#####################################################################
#                                                                   #
# /labscript_devices/NovaTechDDS9M/blacs_workers.py                 #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

import time

from blacs.tab_base_classes import Worker

from .labscript_devices import bauds


class NovaTechDDS9MWorker(Worker):
    def init(self):
        global serial; import serial
        global socket; import socket
        global h5py; import labscript_utils.h5_lock, h5py
        self.smart_cache = {'STATIC_DATA': None, 'TABLE_DATA': ''}

        if self.default_baud_rate is not None:
            initial_baud_rate = self.default_baud_rate
        else:
            initial_baud_rate = self.baud_rate

        self.connection = serial.Serial(
            self.com_port, baudrate=initial_baud_rate, timeout=0.1
        )

        # Check if the novatech will talk to us on this baud rate:
        if not self.check_connection():
            # Nope. Try all baud rates, from slowest to fastest:
            for rate in sorted(bauds):
                self.connection.baudrate = rate
                if self.check_connection():
                    break
            else:
                msg = (
                    "The NovaTech did not respond at any baud rate. "
                    "Check that it is powered and connected to com_port."
                )
                raise RuntimeError(msg)

        # If the baud rate we are using to initially talk to the device is not the one
        # we want to use to program it, switch now to the desired baud rate:
        if self.connection.baudrate != self.baud_rate:
            self.connection.write(b'%s\r\n' % bauds[self.baud_rate])
            # ensure command finishes before switching rates in pyserial:
            time.sleep(0.1)
            self.connection.baudrate = self.baud_rate
            if not self.check_connection():
                msg = (
                    f"The NovaTech did not respond after switching to {self.baud_rate} "
                    f"baud with {bauds[self.baud_rate]!r}."
                )
                raise RuntimeError(msg)

        phase_mode_commands = {
            'aligned': b'm a',
            'continuous': b'm n',
        }

        self.phase_mode_command = phase_mode_commands[self.phase_mode]

        self.connection.write(b'e d\r\n')
        response = self.connection.readline()
        if response == b'e d\r\n':
            # if echo was enabled, then the command to disable it echos back at us!
            response = self.connection.readline()
        if response != b"OK\r\n":
            msg = f'The NovaTech did not answer OK to "e d", received {response!r}.'
            raise Exception(msg)

        self.connection.write(b'I a\r\n')
        if self.connection.readline() != b"OK\r\n":
            raise Exception('The NovaTech did not answer OK to "I a".')

        # Ensure we are in single-tone mode:
        self.connection.write(b'm 0\r\n')
        if self.connection.readline() != b"OK\r\n":
            raise Exception('The NovaTech did not answer OK to "m 0".')

        self.connection.write(b'%s\r\n'%self.phase_mode_command)
        if self.connection.readline() != b"OK\r\n":
            raise Exception(f'The NovaTech did not answer OK to "{self.phase_mode_command.decode("utf8")}".')

    def check_connection(self):
        """Return whether the NovaTech answers an empty command with OK."""
        # check twice since false positive possible on first check. use readlines in
        # case echo is on
        self.connection.write(b'\r\n')
        self.connection.readlines()
        self.connection.write(b'\r\n')
        try:
            return self.connection.readlines()[-1] == b'OK\r\n'
        except IndexError:
            # empty response, probably not connected
            return False

    def check_remote_values(self):
        # Get the currently output values:
        self.connection.write(b'QUE\r\n')
        try:
            response = [self.connection.readline() for i in range(5)]
        except socket.timeout:
            raise Exception('Failed to execute command "QUE". Cannot connect to device.')
        results = {}
        for i, line in enumerate(response[:4]):
            results['dds %d'%i] = {}
            freq, phase, amp, ignore, ignore, ignore, ignore = line.split()
            # Convert hex multiple of 0.1 Hz to Hz:
            results['dds %d'%i]['freq'] = float(int(freq,16))/10.0
            # Convert hex out of 1023 to a fraction of full amplitude:
            results['dds %d'%i]['amp'] = int(amp,16)/1023.0
            # Convert hex fraction of 16384 to degrees:
            results['dds %d'%i]['phase'] = int(phase,16)*360/16384.0
        return results

    def program_manual(self,front_panel_values):
        for i in range(4):
            for subchnl in ['freq','amp','phase']:
                self.program_static(i,subchnl,front_panel_values['dds %d'%i][subchnl])
        return self.check_remote_values()

    def program_static(self,channel,type,value):
        if type == 'freq':
            command = b'F%d %.7f\r\n'%(channel,value/10.0**6)
        elif type == 'amp':
            command = b'V%d %u\r\n'%(channel,int(value*1023+0.5))
        elif type == 'phase':
            command = b'P%d %u\r\n'%(channel,value*16384/360)
        else:
            raise TypeError(f"Unknown sub-channel {type!r}: use 'freq', 'amp' or 'phase'.")
        self.connection.write(command)
        if self.connection.readline() != b"OK\r\n":
            raise Exception(f'The NovaTech did not answer OK to "{command.decode("utf8").strip()}".')
        # Now that a static update has been done, we'd better invalidate the saved STATIC_DATA:
        self.smart_cache['STATIC_DATA'] = None

    def transition_to_buffered(self,device_name,h5_file,front_panel_values,fresh):
        # "Double clutch": switching to table mode and back, before going into it for real,
        # empirically resolves an off-by-one error in table mode in some circumstances,
        # presumably by zeroing the memory pointer, though it should be zero already.
        self.connection.write(b'm t\r\n')
        self.connection.readline()
        self.connection.write(b'm 0\r\n')
        if self.connection.readline() != b"OK\r\n":
            raise Exception('The NovaTech did not answer OK to "m 0".')

        # Store the initial values in case we have to abort and restore them:
        self.initial_values = front_panel_values
        # Store the final values for use in transition_to_manual:
        self.final_values = {}
        static_data = None
        table_data = None
        with h5py.File(h5_file, 'r') as hdf5_file:
            group = hdf5_file['/devices/'+device_name]
            if 'STATIC_DATA' in group:
                static_data = group['STATIC_DATA'][:][0]
            if 'TABLE_DATA' in group:
                table_data = group['TABLE_DATA'][:]

        if static_data is not None:
            data = static_data
            if fresh or data != self.smart_cache['STATIC_DATA']:
                self.logger.debug('Static data has changed, reprogramming.')
                self.smart_cache['STATIC_DATA'] = data
                self.connection.write(b'F2 %.7f\r\n'%(data['freq2']/10.0**7))
                self.connection.readline()
                self.connection.write(b'V2 %u\r\n'%(data['amp2']))
                self.connection.readline()
                self.connection.write(b'P2 %u\r\n'%(data['phase2']))
                self.connection.readline()
                self.connection.write(b'F3 %.7f\r\n'%(data['freq3']/10.0**7))
                self.connection.readline()
                self.connection.write(b'V3 %u\r\n'%data['amp3'])
                self.connection.readline()
                self.connection.write(b'P3 %u\r\n'%data['phase3'])
                self.connection.readline()

                # Save these values into final_values so the GUI can
                # be updated at the end of the run to reflect them:
                self.final_values['dds 2'] = {}
                self.final_values['dds 3'] = {}
                self.final_values['dds 2']['freq'] = data['freq2']/10.0
                self.final_values['dds 3']['freq'] = data['freq3']/10.0
                self.final_values['dds 2']['amp'] = data['amp2']/1023.0
                self.final_values['dds 3']['amp'] = data['amp3']/1023.0
                self.final_values['dds 2']['phase'] = data['phase2']*360/16384.0
                self.final_values['dds 3']['phase'] = data['phase3']*360/16384.0

        # Now program the buffered outputs:
        if table_data is not None:
            data = table_data
            for i, line in enumerate(data):
                st = time.time()
                oldtable = self.smart_cache['TABLE_DATA']
                for ddsno in range(2):
                    if fresh or i >= len(oldtable) or (line['freq%d'%ddsno],line['phase%d'%ddsno],line['amp%d'%ddsno]) != (oldtable[i]['freq%d'%ddsno],oldtable[i]['phase%d'%ddsno],oldtable[i]['amp%d'%ddsno]):
                        self.connection.write(b't%d %04x %08x,%04x,%04x,ff\r\n'%(ddsno, i,line['freq%d'%ddsno],line['phase%d'%ddsno],line['amp%d'%ddsno]))
                        self.connection.readline()
                et = time.time()
                tt=et-st
                self.logger.debug('Time spent on line %s: %s'%(i,tt))
            # Store the table for future smart programming comparisons:
            try:
                self.smart_cache['TABLE_DATA'][:len(data)] = data
                self.logger.debug('Stored new table as subset of old table')
            except: # new table is longer than old table
                self.smart_cache['TABLE_DATA'] = data
                self.logger.debug('New table is longer than old table and has replaced it.')

            # Get the final values of table mode so that the GUI can
            # reflect them after the run:
            self.final_values['dds 0'] = {}
            self.final_values['dds 1'] = {}
            self.final_values['dds 0']['freq'] = data[-1]['freq0']/10.0
            self.final_values['dds 1']['freq'] = data[-1]['freq1']/10.0
            self.final_values['dds 0']['amp'] = data[-1]['amp0']/1023.0
            self.final_values['dds 1']['amp'] = data[-1]['amp1']/1023.0
            self.final_values['dds 0']['phase'] = data[-1]['phase0']*360/16384.0
            self.final_values['dds 1']['phase'] = data[-1]['phase1']*360/16384.0

            # Transition to table mode:
            self.connection.write(b'm t\r\n')
            self.connection.readline()
            if self.update_mode == 'synchronous':
                # Transition to hardware synchronous updates:
                self.connection.write(b'I e\r\n')
                self.connection.readline()
                # We are now waiting for a rising edge to trigger the output
                # of the second table pair (first of the experiment)
            elif self.update_mode == 'asynchronous':
                # Output will now be updated on falling edges.
                pass
            else:
                raise ValueError(
                    f"update_mode is {self.update_mode!r}, not 'synchronous' or 'asynchronous'."
                )

        return self.final_values

    def abort_transition_to_buffered(self):
        return self.abort()

    def abort_buffered(self):
        return self.abort()

    def transition_to_manual(self):
        return self._return_to_manual(abort=False)

    def abort(self):
        return self._return_to_manual(abort=True)

    def _return_to_manual(self, abort):
        self.connection.write(b'm 0\r\n')
        if self.connection.readline() != b"OK\r\n":
            raise Exception('The NovaTech did not answer OK to "m 0".')
        self.connection.write(b'I a\r\n')
        if self.connection.readline() != b"OK\r\n":
            raise Exception('The NovaTech did not answer OK to "I a".')
        if abort:
            # On an abort, reset DDSs 2 and 3 to their initial values (0 and 1 already
            # are) and invalidate the smart programming cache for them.
            values = self.initial_values
            DDSs = [2,3]
            self.smart_cache['STATIC_DATA'] = None
        else:
            # Otherwise set DDSs 0 and 1 to their final values (2 and 3 already are).
            values = self.final_values
            DDSs = [0,1]

        for ddsnumber in DDSs:
            channel_values = values['dds %d'%ddsnumber]
            for subchnl in ['freq','amp','phase']:
                self.program_static(ddsnumber,subchnl,channel_values[subchnl])

        return True

    def shutdown(self):
        # return to the default baud rate
        if self.default_baud_rate is not None:
            self.connection.write(b'%s\r\n' % bauds[self.default_baud_rate])
            time.sleep(0.1)
            self.connection.readlines()

        self.connection.close()
