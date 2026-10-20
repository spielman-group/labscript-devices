#####################################################################
#                                                                   #
# /labscript_devices/LightCrafterDMD/blacs_tabs.py                  #
#                                                                   #
# Copyright 2017, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from blacs.device_base_class import DeviceTab


class LightCrafterDMDTab(DeviceTab):
    # For now, assume only the DLP 0.3 WVGA is supported, fix the image dimensions:
    width = 608
    height = 684
    
    def initialise_GUI(self):
        # find the connection table object for this device
        self.connection_object = self.connection_table.find_by_name(self.device_name)
        
        # Get the region properties from teh connection table and build the dictionary to produce the IMAGE object outputs
        image_properties = {}
        for child_name, child in self.connection_object.child_list.items():
            wx = self.width
            wy = self.height
            image_properties[child.parent_port] = {'width' : wx, 'height' : wy}
            
            
        # Create the outputs and widgets and place the widgets in the UI
        self.create_image_outputs(image_properties)
        _,_,_,image_widgets = self.auto_create_widgets()
        self.auto_place_widgets(("DMD Image", image_widgets))
        
        self.supports_remote_value_check(False)        
        self.supports_smart_programming(True) 
        
    def initialise_workers(self):
        self.server = self.BLACS_connection
        self.create_worker("main_worker",'labscript_devices.LightCrafterDMD.blacs_workers.LightCrafterDMDWorker',{'server':self.server, 'slm_properties':{'width':self.width, 'height':self.height}})
        self.primary_worker = "main_worker"
