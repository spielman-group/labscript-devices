#####################################################################
#                                                                   #
# /labscript_devices/PulseBlaster/runviewer_parsers.py              #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

import numpy as np
import labscript_utils.h5_lock, h5py

from .labscript_devices import PulseBlasterBase


class PulseBlasterBaseParser:
    """Runviewer's traces of a PulseBlaster board's program. A board's class sets
    ``num_flags``, and ``num_dds`` if it has DDS outputs."""
    num_dds = 0

    def __init__(self, path, device):
        self.path = path
        self.name = device.name
        self.device = device
        
        # We create a lookup table for strings to be used later as dictionary keys.
        # This saves having to evaluate '%d'%i many many times, and makes the _add_pulse_program_row_to_traces method
        # significantly more efficient
        self.dds_strings = {}
        for i in range(self.num_dds):
            self.dds_strings[i] = {}
            self.dds_strings[i]['ddsfreq'] = 'dds %d_freq'%i
            self.dds_strings[i]['ddsamp'] = 'dds %d_amp'%i
            self.dds_strings[i]['ddsphase'] = 'dds %d_phase'%i
            self.dds_strings[i]['freq'] = 'freq%d'%i
            self.dds_strings[i]['amp'] = 'amp%d'%i
            self.dds_strings[i]['phase'] = 'phase%d'%i
            self.dds_strings[i]['dds_en'] = 'dds_en%d'%i
            
        self.flag_strings = {}
        self.flag_powers = {}
        
        for i in range(self.num_flags):
            self.flag_strings[i] = 'flag %d'%i
            self.flag_powers[i] = 2**i
        
            
        
    def _duration(self, row):
        # A LONG_DELAY runs its length as many times as its data says
        repeats = row['inst_data'] if row['inst'] == 7 else 1
        return repeats * row['length'] * 1.0e-9

    def get_traces(self, add_trace, clock=None):
        if clock is None:
            # we're the master pseudoclock, software triggered. So we don't have to worry about trigger delays, etc
            pass
            
        # get the pulse program
        with h5py.File(self.path, 'r') as f:
            pulse_program = f['devices/%s/PULSE_PROGRAM'%self.name][:]
            dds = {}
            for i in range(self.num_dds):
                dds[i] = {}
                for reg in ['FREQ', 'AMP', 'PHASE']:
                    dds[i][reg] = f['devices/%s/DDS%d/%s_REGS'%(self.name, i, reg)][:]
        
        times = []
        traces = {}
        for i in range(self.num_flags):
            traces['flag %d'%i] = []
        for i in range(self.num_dds):
            for sub_chnl in ['freq', 'amp', 'phase']:
                traces['dds %d_%s'%(i,sub_chnl)] = []   
        
        # now build the traces
        t = 0. if clock is None else PulseBlasterBase.trigger_delay # Offset by the initial trigger from the parent's clock
        i = 0
        while i < len(pulse_program):
            # ignore the first 2 instructions, they are dummy instructions for BLACS
            if i < 2:
                i += 1
                continue
            
            row = pulse_program[i]
            
            if row['inst'] == 2: # Loop
                loops = int(row['inst_data'])
                
                buffer = {}
                j = i
                while loops > 0:
                    looping = True
                    while looping:
                        row = pulse_program[j]
                        # buffer the index of traces used for this instruction
                        # Cuts the runtime down by ~60%
                        if j not in buffer:
                            times.append(t)
                            self._add_pulse_program_row_to_traces(traces, row, dds)
                            buffer[j] = len(times)-1
                        else:                            
                            times.append(t)
                            self._add_pulse_program_row_from_buffer(traces, buffer[j])
                            
                        t+= self._duration(row)
                        
                        if row['inst'] == 3: # END_LOOP
                            looping = False
                            j = int(row['inst_data']) if loops > 1 else j
                        else:
                            j+=1
                    loops -= 1
                    
                i = j
                    
            else: # Continue
                if row['inst'] == 8: #WAIT
                    print('Wait at %.9f'%t)
                    pass
                times.append(t)
                self._add_pulse_program_row_to_traces(traces,row,dds)
                t+= self._duration(row)
            
                if row['inst'] == 8 and clock is not None: #WAIT
                    t+= PulseBlasterBase.trigger_delay
                    
            
            i += 1            
                
        print('Stop time: %.9f'%t)
        # now put together the traces
        to_return = {}
        times = np.array(times, dtype=np.float64)
        for name, data in traces.items():
            to_return[name] = (times, np.array(data))
            
        
        clocklines_and_triggers = {}
        for pseudoclock_name, pseudoclock in self.device.child_list.items():
            for clock_line_name, clock_line in pseudoclock.child_list.items():
                if clock_line.parent_port == 'internal':
                    parent_device_name = '%s.direct_outputs'%self.name
                    for internal_device_name, internal_device in clock_line.child_list.items():
                        for channel_name, channel in internal_device.child_list.items():
                            # A DDS of any class, by its 'dds n' connection
                            if channel.parent_port.split()[0] == 'dds':
                                for subchnl_name, subchnl in channel.child_list.items():
                                    connection = '%s_%s'%(channel.parent_port, subchnl.parent_port)
                                    if connection in to_return:
                                        add_trace(subchnl.name, to_return[connection], parent_device_name, connection)
                            else:
                                # A flag that triggers devices, a Trigger of any class, clocks them
                                if channel.child_list:
                                    clocklines_and_triggers[channel_name] = to_return[channel.parent_port]
                                add_trace(channel_name, to_return[channel.parent_port], parent_device_name, channel.parent_port)
                else:
                    clocklines_and_triggers[clock_line_name] = to_return[clock_line.parent_port]
                    add_trace(clock_line_name, to_return[clock_line.parent_port], self.name, clock_line.parent_port)
            
        return clocklines_and_triggers
    
    def _add_pulse_program_row_from_buffer(self, traces, index):
        for i in range(self.num_flags):
            traces[self.flag_strings[i]].append(traces[self.flag_strings[i]][index])
            
        for i in range(self.num_dds):
            current_strings = self.dds_strings[i]
            traces[current_strings['ddsfreq']].append(traces[current_strings['ddsfreq']][index])
            traces[current_strings['ddsphase']].append(traces[current_strings['ddsphase']][index])
            traces[current_strings['ddsamp']].append(traces[current_strings['ddsamp']][index])
            
    def _add_pulse_program_row_to_traces(self, traces, row, dds, flags = None):
        # add flags
        if flags is None:
            flags = np.binary_repr(row['flags'],self.num_flags)[::-1]
        for i in range(self.num_flags):
            traces[self.flag_strings[i]].append(int(flags[i]))
        
       
        # note that we are looking up keys for the traces dictionary and row array in self.dds_strings
        # Doing this reduces the runtime (of the below block) by 25%
        for i in range(self.num_dds):
            # Note: This is done to reduce runtime (about 10%)
            current_strings = self.dds_strings[i]
            current_dds = dds[i]
            
            traces[current_strings['ddsfreq']].append(current_dds['FREQ'][row[current_strings['freq']]])
            traces[current_strings['ddsphase']].append(current_dds['PHASE'][row[current_strings['phase']]])
            # Note: Using the inline if statement reduces the runtime (of this for loop) by 50%
            amp = current_dds['AMP'][row[current_strings['amp']]] if row[current_strings['dds_en']] else 0
            traces[current_strings['ddsamp']].append(amp)


class PulseBlasterParser(PulseBlasterBaseParser):
    num_dds = 2
    num_flags = 12
