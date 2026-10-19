#####################################################################
#                                                                   #
# /labscript_devices/PhaseMatrixQuickSyn/labscript_devices.py       #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import numpy as np

from labscript import Device, StaticDDS, StaticAnalogQuantity, StaticDigitalOut, compiler, LabscriptError, set_passed_properties
import labscript_utils.properties

class QuickSynDDS(StaticDDS):
    """A StaticDDS that supports only frequency control, with no phase or amplitude control."""
    description = 'PhaseMatrix QuickSyn DDS'
    allowed_children = [StaticAnalogQuantity,StaticDigitalOut]
    generation = 2
    
    @set_passed_properties()    
    def __init__(self, name, parent_device, connection, freq_limits = None, freq_conv_class = None,freq_conv_params = {}, **kwargs):
        Device.__init__(self,name,parent_device,connection, **kwargs)
        self.frequency = StaticAnalogQuantity(self.name+'_freq',self,'freq',freq_limits,freq_conv_class,freq_conv_params)
        self.frequency.default_value = 0.5e9
        self.gate = StaticDigitalOut(self.name+'_gate',self,'gate')
            
    def setamp(self,value,units=None):
        raise LabscriptError('QuickSyn does not support amplitude control')
        
    def setphase(self,value,units=None):
        raise LabscriptError('QuickSyn does not support phase control')
            
    def enable(self):       
        """overridden from StaticDDS so as not to provide time resolution -
        output can be enabled or disabled only at the start of the shot"""
        self.gate.go_high()
                            
    def disable(self):
        """overridden from StaticDDS so as not to provide time resolution -
        output can be enabled or disabled only at the start of the shot"""
        self.gate.go_low()


class PhaseMatrixQuickSyn(Device):
    description = 'QuickSyn Frequency Synthesiser'
    allowed_children = [QuickSynDDS]
    generation = 0

    @set_passed_properties()
    def __init__(self, name,com_port, **kwargs):
        Device.__init__(self, name, None, None, **kwargs)
        self.BLACS_connection = com_port
        
    def quantise_freq(self, data, device):
        """Return a DDS's frequencies, `data`, in the device's mHz, with the
        scale."""
        return device.quantise_channel('frequency', 1000, values=data, limits=(0.5e9, 10e9), dtype=np.uint64)

    def generate_code(self, hdf5_file):
        for output in self.child_devices:
            try:
                prefix, channel = output.connection.split()
                channel = int(channel)
            except:
                raise LabscriptError('%s %s has invalid connection string: \'%s\'. '%(output.description,output.name,str(output.connection)) + 
                                     'Format must be \'dds 0\'.')
            if channel != 0:
                raise LabscriptError('%s %s has invalid connection string: \'%s\'. '%(output.description,output.name,str(output.connection)) + 
                                     'Format must be \'dds 0\'.')
            dds = output
        # Call these functions to finalise stuff:
        ignore = dds.frequency.get_change_times()
        dds.frequency.make_timeseries([])
        dds.frequency.expand_timeseries()
        
        ignore = dds.gate.get_change_times()
        dds.gate.make_timeseries([])
        dds.gate.expand_timeseries()
        
        dds.frequency.raw_output, dds.frequency.scale_factor = self.quantise_freq(dds.frequency.raw_output, dds)
        static_dtypes = [('freq0', np.uint64)] + \
                        [('gate0', np.uint16)]
        static_table = np.zeros(1, dtype=static_dtypes)
        static_table['freq0'].fill(1)
        static_table['freq0'] = dds.frequency.raw_output[0]
        static_table['gate0'] = dds.gate.raw_output[0]
        grp = self.init_device_group(hdf5_file)
        grp.create_dataset('STATIC_DATA',compression=compiler.compression,data=static_table) 
        self.set_property('frequency_scale_factor', 1000, location='device_properties')
