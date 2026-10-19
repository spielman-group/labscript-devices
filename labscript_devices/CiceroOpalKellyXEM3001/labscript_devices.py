#####################################################################
#                                                                   #
# /labscript_devices/CiceroOpalKellyXEM3001/labscript_devices.py    #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

from labscript import Device, PseudoclockDevice, Pseudoclock, ClockLine, LabscriptError, set_passed_properties, compiler, WaitMonitor, DigitalOut, internal_wait_monitor_outputs

import numpy as np


#
# The labscript device class
#
class CiceroOpalKellyXEM3001(PseudoclockDevice):
    # note: most parameters set in __init__ as they depend on reference clock frequency
    description = 'CiceroOpalKellyXEM3001'
    trigger_edge_type = 'rising' 
    allowed_children = [Pseudoclock]
    # Its own pseudoclock, and the internal one its wait monitor hangs from.
    max_pseudoclocks = 2
    
    # Determined by confirming that an instruction table that is 2049 long
    # does not output the last instruction
    max_instructions = 2048
    
    @set_passed_properties(property_names = {
        "connection_table_properties": ["reference_clock", "clock_frequency", "trigger_debounce_clock_ticks"],
        "device_properties": ["trigger_delay", "wait_delay"]}
        )    
    def __init__(self, name, trigger_device=None, trigger_connection=None, serial='', reference_clock='internal', clock_frequency=100e6, use_wait_monitor=True, trigger_debounce_clock_ticks=10, **kwargs):
        # set device properties based on clock frequency
        self.clock_limit = clock_frequency/2
        self.clock_resolution = 1/clock_frequency
        # We'll set this to be 2x the debounce count
        self.trigger_minimum_duration = 2*trigger_debounce_clock_ticks/clock_frequency
        # Todo: confirm this.
        #       It should only be 5 clock cycles + the debounce_clock_ticks
        #       as I think it takes 3 clock cycles to propagate to the state
        #       machine of the FPGA code (due to the three uses of the non-blocking <= verilog operator
        #       in the debounce code) and then another 2 cycles before the output goes high
        #       (one to move out of the wait for retrigger code and then one because the update of the
        #        output state is non-blocking)\
        #
        self.trigger_delay = (5+trigger_debounce_clock_ticks)/clock_frequency
        # Todo: confirm this
        #       I believe it is 1 clock cycle
        self.wait_delay = self.clock_resolution
        
        PseudoclockDevice.__init__(self, name, trigger_device, trigger_connection, **kwargs)
        self.BLACS_connection = serial
        
        if trigger_debounce_clock_ticks >= 2**16:
            raise LabscriptError('The %s %s trigger_debounce_clock_ticks parameter must be between 0 and 65535'%(self.description, self.name))
        
        # create Pseudoclock and clockline
        self._pseudoclock = Pseudoclock('%s_pseudoclock'%name, self, 'clock', max_clock_lines=1) # possibly a better connection name than 'clock'?
        # Create the internal direct output clock_line
        self._clock_line = ClockLine('%s_clock_line'%name, self.pseudoclock, 'Clock Out')
        
        # Create internal devices for connecting to a wait monitor
        self.__wait_monitor_intermediate_device = internal_wait_monitor_outputs(self)
        
        # Only the master pseudoclock's board times the waits, as on the PrawnBlaster
        if use_wait_monitor and self.is_master_pseudoclock:
            WaitMonitor('%s__wait_monitor'%name, self.internal_wait_monitor_outputs, 'internal', self.internal_wait_monitor_outputs, 'internal', self.internal_wait_monitor_outputs, 'internal')
        
    @property
    def internal_wait_monitor_outputs(self):
        return self.__wait_monitor_intermediate_device
    
    @property
    def pseudoclock(self):
        return self._pseudoclock
    
    # Note, not to be confused with Device.parent_clock_line which returns the parent ClockLine
    # This one gives the automatically created ClockLine object
    @property
    def clockline(self):
        return self._clock_line
    
    
    def generate_code(self, hdf5_file):
        PseudoclockDevice.generate_code(self, hdf5_file)
        group = self.init_device_group(hdf5_file)   
        
        # compress clock instructions with the same period: This will
        # halve the number of instructions roughly, since the PineBlaster
        # does not have a 'slow clock':
        reduced_instructions = []
        current_wait_index = 0
        wait_table = sorted(compiler.wait_table)
        
        if not self.is_master_pseudoclock:
            reduced_instructions.append({'on': 0, 'off': ((self.trigger_edge_type=='rising') << 1) + 1, 'reps': 0})
                
        for instruction in self.pseudoclock.clock:
            if instruction == 'WAIT':
                # The following period and reps indicates a wait instruction
                wait_timeout = compiler.wait_table[wait_table[current_wait_index]][1]
                current_wait_index += 1
                
                # The actual wait instruction.
                # on_counts correspond to teh number of reference clock cycles
                # to wait for external trigger before auto-resuming. 
                # It overcounts by 1 here because the logic on the FPGA is different for the first reference clock cycle 
                # (you cannot resume until the after second reference clock cycle), so we subtract 1 off the on counts
                # so that it times-out after the correct number of samples
                reduced_instructions.append({'on': self.quantise_to_pseudoclock(wait_timeout, ticks=True)-1, 'off': ((self.trigger_edge_type=='rising') << 1) + 1, 'reps': 0})
                continue
            reps = instruction['reps']
            # period is in quantised units:
            periods = self.quantise_to_pseudoclock(instruction['step'], ticks=True)
            # Get the "high" half of the clock period
            on_period = int(periods/2)
            # Use the remainder to calculate the "off period" (allows slightly assymetric clock signals so to minimise timing errors)
            off_period = periods-on_period
            
            if reduced_instructions and reduced_instructions[-1]['on'] == on_period and reduced_instructions[-1]['off'] == off_period:
                reduced_instructions[-1]['reps'] += reps
            else:
                reduced_instructions.append({'on': on_period, 'off': off_period, 'reps': reps})
        
        if len(reduced_instructions) > self.max_instructions:
            raise LabscriptError("%s %s has too many instructions. It has %d and can only support %d"%(self.description, self.name, len(reduced_instructions), self.max_instructions))
            
        # Store these instructions to the h5 file:
        dtypes = [('on_period',np.int64),('off_period',np.int64),('reps',np.int64)]
        pulse_program = np.zeros(len(reduced_instructions),dtype=dtypes)
        for i, instruction in enumerate(reduced_instructions):
            pulse_program[i]['on_period'] = instruction['on']
            pulse_program[i]['off_period'] = instruction['off']
            pulse_program[i]['reps'] = instruction['reps']
        group.create_dataset('PULSE_PROGRAM', compression = compiler.compression, data=pulse_program)
