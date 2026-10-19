#####################################################################
#                                                                   #
# /labscript_devices/PineBlaster/labscript_devices.py               #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

from labscript import PseudoclockDevice, Pseudoclock, ClockLine, compiler, LabscriptError, set_passed_properties, renamed_keyword

import numpy as np



class PineBlaster(PseudoclockDevice):
    description = 'PineBlaster'
    clock_limit = 10e6
    clock_resolution = 25e-9
    clock_type = 'fast clock'
    # Measured by Phil Starkey on 2015/9/24
    trigger_delay = 350e-9
    # Todo: find out what this actually is:
    wait_delay = 2.5e-6
    allowed_children = [Pseudoclock]
    max_pseudoclocks = 1
    
    max_instructions = 15000
    
    @set_passed_properties(property_names = {
        "connection_table_properties": ["com_port"]}
        )    
    def __init__(self, name, trigger_device=None, trigger_connection=None, com_port='COM1', **kwargs):
        # LEGACY USBPORT KEYWORD COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
        self.com_port = com_port = renamed_keyword(kwargs, 'usbport', 'com_port', com_port, 'PineBlaster', stacklevel=4)
        PseudoclockDevice.__init__(self, name, trigger_device, trigger_connection, **kwargs)
        self.BLACS_connection = com_port
        
        # create Pseudoclock and clockline
        self._pseudoclock = Pseudoclock('%s_pseudoclock'%name, self, 'clock', max_clock_lines=1) # possibly a better connection name than 'clock'?
        # Create the internal direct output clock_line
        self._clock_line = ClockLine('%s_clock_line'%name, self.pseudoclock, 'internal')
    
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
        for instruction in self.pseudoclock.clock:
            if instruction == 'WAIT':
                # The following period and reps indicates a wait instruction
                reduced_instructions.append({'period': 0, 'reps': 1})
                continue
            reps = instruction['reps']
            # period is in quantised units:
            period = self.quantise_to_pseudoclock(instruction['step'], ticks=True)
            if reduced_instructions and reduced_instructions[-1]['period'] == period:
                reduced_instructions[-1]['reps'] += reps
            else:
                reduced_instructions.append({'period': period, 'reps': reps})
        # The following period and reps indicates a stop instruction:
        reduced_instructions.append({'period': 0, 'reps': 0})
        if len(reduced_instructions) > self.max_instructions:
            raise LabscriptError("%s %s has too many instructions. It has %d and can only support %d"%(self.description, self.name, len(reduced_instructions), self.max_instructions))
        # Store these instructions to the h5 file:
        dtypes = [('period',int),('reps',int)]
        pulse_program = np.zeros(len(reduced_instructions),dtype=dtypes)
        for i, instruction in enumerate(reduced_instructions):
            pulse_program[i]['period'] = instruction['period']
            pulse_program[i]['reps'] = instruction['reps']
        group.create_dataset('PULSE_PROGRAM', compression = compiler.compression, data=pulse_program)
