#####################################################################
#                                                                   #
# /labscript_devices/PhaseMatrixQuickSyn/blacs_workers.py           #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from blacs.tab_base_classes import Worker


class PhaseMatrixQuickSynWorker(Worker):
    def init(self):
        global serial; import serial
        global h5py; import labscript_utils.h5_lock, h5py
        global time; import time

        baud_rate = 115200
        port = self.address
        self.connection = serial.Serial(port, baudrate=baud_rate, timeout=0.1)
        # Discard any input waiting on the port.
        self.connection.readlines()

        # Switch to the external reference if the synthesiser is on the internal one.
        self.connection.write(b'ROSC:SOUR?\r')
        response = self.connection.readline().decode('utf8')
        if response == 'INT\n':
            self.connection.write(b'ROSC:SOUR EXT\r')

    def check_remote_values(self):
        results = {'dds 0': {}}
        line = ''
        count = 0

        self.connection.write(b'FREQ?\r')
        line = self.connection.readline().decode('utf8')

        if line == '':
            # Nothing within the 0.1 s timeout; read once more.
            line = self.connection.readline().decode('utf8')
            if line == '':
                raise Exception(
                    'The QuickSyn did not answer FREQ?. '
                    'Check that it is powered and that com_port is its serial port.'
                )

        # Convert mHz to Hz:
        results['dds 0']['freq'] = float(line)/1000

        # Wait a little while first, it doesn't like being asked things too quickly!
        time.sleep(0.05)
        self.connection.write(b'OUTP:STAT?\r')
        line = self.connection.readline().decode('utf8')
        if line == '':
            raise Exception(
                'The QuickSyn did not answer OUTP:STAT?. '
                'Check that it is powered and that com_port is its serial port.'
            )
        time.sleep(0.05)

        # The gate is high unless the output state is OFF.
        results['dds 0']['gate'] = 0 if line == 'OFF\n' else 1

        return results

    def check_status(self):
        results = {}
        line = ''
        self.connection.write(b'STAT?\r')
        line = self.connection.readline().decode('utf8')
        if line == '':
            raise Exception(
                'The QuickSyn did not answer STAT?. '
                'Check that it is powered and that com_port is its serial port.'
            )
        time.sleep(0.05)

        # The binary digits of the hex status word, without the '0b' header,
        # padded with zeros to 8 bits so that each bit below can be counted from the end.
        status = bin(int(line,16))[2:]
        while len(status)<8:
            status = '0'+status
        # Bit 0 is 1 for an external ref, 0 for no external ref
        results['ref'] = int(status[-1])
        # Bit 1 is high for rf unlocked, low for rf locked. It is reversed, so that
        # freqlock is 1 when locked.
        results['freqlock'] = int(not int(status[-2]))
        # Bit 2 is high for ref unlocked, low for ref locked. It is reversed likewise.
        results['reflock'] = int(not int(status[-3]))
        # Bit 3 is whether the output is on, which is not read here, as
        # check_remote_values reports it.

        # Bit 4 goes high for a voltage error, which raises an exception to get the
        # user's attention.
        if int(status[-5]):
            self.logger.critical('The QuickSyn reports a voltage error.')
            raise Exception('The QuickSyn reports a voltage error.')
        # Bit 5 is whether the internal reference is being output
        results['ref_output'] = int(status[-6])
        # Bit 6 is whether blanking is on (i.e. turning off output while it changes frequency)
        results['blanking'] = int(status[-7])
        # Bit 7 is whether lock recovery is on
        results['lock_recovery'] = int(status[-8])

        # DIAG:MEAS? 21 is the temperature.
        self.connection.write(b'DIAG:MEAS? 21\r')
        results['temperature'] = float(self.connection.readline().decode('utf8'))

        if results['temperature'] > 50.0:
            raise Exception(
                f"The QuickSyn's temperature is {results['temperature']}, above the limit of 50."
            )

        return results

    def program_manual(self,front_panel_values):
        freq = front_panel_values['dds 0']['freq']
        # The QuickSyn takes millihertz:
        freq*=1e3
        command = 'FREQ %i\r'%freq
        self.connection.write(command.encode('utf8'))

        # Sleep here, since the phasematrix gets grumpy
        time.sleep(0.05)

        gate = front_panel_values['dds 0']['gate']
        command = 'OUTP:STAT %i\r'%gate
        self.connection.write(command.encode('utf8'))

        return self.check_remote_values()

    def update_reference_out(self,value):
        pass

    def update_blanking(self,value):
        pass

    def update_lock_recovery(self,value):
        pass

    def transition_to_buffered(self,device_name,h5_file,front_panel_values,fresh):
        # Store the initial values in case we have to abort and restore them:
        self.initial_values = front_panel_values
        self.final_values = {}
        with h5py.File(h5_file, 'r') as hdf5_file:
            group = hdf5_file['/devices/'+device_name]
            # STATIC_DATA has the frequency, in mHz, and the gate, from generate_code.
            if 'STATIC_DATA' in group:
                data = group['STATIC_DATA'][:][0]

        self.connection.write(b'FREQ %i\r'%(data['freq0']))
        time.sleep(0.05)
        self.connection.write(b'OUTP:STAT 1')

        # BLACS shows these in the front panel when the shot ends.
        final_values = {'dds 0':{}}

        # mHz to Hz
        final_values['dds 0']['freq'] = data['freq0']/1e3
        final_values['dds 0']['gate'] = 1

        return final_values

    def abort_transition_to_buffered(self):
        return self.abort()

    def abort_buffered(self):
        return self.abort()

    def transition_to_manual(self):
        # The device keeps the shot's final value; nothing to do.
        return True

    def abort(self):
        # Reset to the value from before the shot.
        self.program_manual(self.initial_values)
        return True

    def shutdown(self):
        self.connection.close()
