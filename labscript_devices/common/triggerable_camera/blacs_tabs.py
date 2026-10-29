#####################################################################
#                                                                   #
# /labscript_devices/common/triggerable_camera/blacs_tabs.py        #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import os
import json
import threading
from time import perf_counter
import ast

import labscript_utils.h5_lock
import h5py

import numpy as np

from qtutils import UiLoader, inmain_decorator
import qtutils.icons
from qtutils.qt import QtWidgets, QtCore
import pyqtgraph as pg

from blacs.tab_base_classes import define_state, MODE_MANUAL
from blacs.device_base_class import DeviceTab

import labscript_utils.properties
from labscript_utils.ls_zprocess import ZMQServer


def exp_av(av_old, data_new, dt, tau):
    """Update the average `av_old`, of timescale `tau`, with `data_new` after `dt`."""
    if dt > tau:
        return data_new
    k = dt / tau
    return k * data_new + (1 - k) * av_old


class ImageReceiver(ZMQServer):
    """Receive images from the worker, reply 'ok', and show them with the frame rate."""

    def __init__(self, image_view, label_fps, autolevels_button):
        ZMQServer.__init__(self, port=None, dtype='multipart')
        self.image_view = image_view
        self.label_fps = label_fps
        self.last_frame_time = None
        self.frame_rate = None
        self.image = None
        self.bg_image = None
        self.autolevels_button = autolevels_button
        # Set when no received image is waiting to be displayed:
        self.displayed = threading.Event()
        self.displayed.set()

    def handler(self, data):
        # In the server thread, which never waits for the main thread, so a tab restart
        # cannot deadlock with an arriving image. The reply waits only for the previous
        # image's display, so at most one image is waiting.
        while not self.displayed.wait(timeout=0.1):
            if self.stopping:
                return [b'ok']
        self.displayed.clear()
        md = json.loads(data[0])
        image = np.frombuffer(memoryview(data[1]), dtype=md['dtype'])
        image = image.reshape(md['shape'])
        if len(image.shape) == 3 and image.shape[0] == 1:
            # transition_to_manual sends a shot's images as one 3D stack; show a single
            # image as 2D.
            image = image.reshape(image.shape[1:])
        self.display(image)
        return [b'ok']

    @inmain_decorator(wait_for_return=False)
    def display(self, image):
        try:
            this_frame_time = perf_counter()
            if self.last_frame_time is not None:
                dt = this_frame_time - self.last_frame_time
                if self.frame_rate is not None:
                    # Exponential moving average of the frame rate over 1 second:
                    self.frame_rate = exp_av(self.frame_rate, 1 / dt, dt, 1.0)
                else:
                    self.frame_rate = 1 / dt
            self.last_frame_time = this_frame_time
            self.image = image
            self.update_image()
            if self.frame_rate is not None:
                self.label_fps.setText(f"{self.frame_rate:.01f} fps")

            # qtutils CallEvents, which call this method in the main thread, cannot be
            # given low enough priority for paint events to run before the next call, so
            # they back up. Sending posted events here prevents it (issue #36).
            QtWidgets.QApplication.instance().sendPostedEvents()
        finally:
            self.displayed.set()

    @inmain_decorator(wait_for_return=True)
    def update_image(self):
        if self.image is None:
            return
        image = self.image
        bg_image = self.bg_image
        if bg_image is not None and image.shape[-bg_image.ndim:] == bg_image.shape:
            # Subtract the background from the image, or from each image of a stack, if
            # the shapes match:
            image = image.astype(float) - bg_image.astype(float)
        autolevels = self.autolevels_button.isChecked()
        if self.image_view.image is None:
            # First time setting an image. Do autoscaling etc:
            self.image_view.setImage(image.swapaxes(-1, -2))
        else:
            # Keep zoom and pan, and the levels unless they are scaled automatically.
            self.image_view.setImage(
                image.swapaxes(-1, -2),
                autoRange=False,
                autoLevels=autolevels,
                autoHistogramRange=autolevels,
            )

    @inmain_decorator(wait_for_return=True)
    def set_bg_image(self):
        """Use the latest image as the background; False if there is none yet."""
        if self.image is None:
            return False
        self.bg_image = self.image
        self.update_image()
        return True

    @inmain_decorator()
    def clear_bg_image(self):
        self.bg_image = None
        self.update_image()


class TriggerableCameraTab(DeviceTab):
    # A subclass that only replaces the worker class overrides this.
    worker_class = (
        'labscript_devices.common.triggerable_camera.blacs_workers'
        '.TriggerableCameraWorker'
    )
    # A subclass overrides this to False to set the camera attributes every shot, even
    # when they are unchanged.
    use_smart_programming = True

    def initialise_GUI(self):
        layout = self.get_tab_layout()
        ui_filepath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'blacs_tab.ui'
        )
        attributes_ui_filepath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'attributes_dialog.ui'
        )
        self.ui = UiLoader().load(ui_filepath)
        self.ui.pushButton_continuous.clicked.connect(self.on_continuous_clicked)
        self.ui.pushButton_stop.clicked.connect(self.on_stop_clicked)
        self.ui.pushButton_snap.clicked.connect(self.on_snap_clicked)
        self.ui.pushButton_attributes.clicked.connect(self.on_attributes_clicked)
        self.ui.toolButton_nomax.clicked.connect(self.on_reset_rate_clicked)
        self.ui.pushButton_set_bg.clicked.connect(self.on_set_bg_clicked)
        self.ui.pushButton_clear_bg.clicked.connect(self.on_clear_bg_clicked)

        self.attributes_dialog = UiLoader().load(attributes_ui_filepath)
        self.attributes_dialog.setParent(self.ui.parent())
        self.attributes_dialog.setWindowFlags(QtCore.Qt.WindowType.Tool)
        self.attributes_dialog.setWindowTitle(f"{self.device_name} attributes")
        self.attributes_dialog.pushButton_copy.clicked.connect(self.on_copy_clicked)
        self.attributes_dialog.comboBox.currentIndexChanged.connect(
            self.on_attr_visibility_level_changed
        )
        self.ui.doubleSpinBox_maxrate.valueChanged.connect(self.on_max_rate_changed)

        layout.addWidget(self.ui)
        self.image = pg.ImageView()
        self.image.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.ui.horizontalLayout.addWidget(self.image)
        self.ui.pushButton_stop.hide()
        self.ui.pushButton_clear_bg.hide()
        self.ui.doubleSpinBox_maxrate.hide()
        self.ui.toolButton_nomax.hide()
        self.ui.label_fps.hide()

        # Ensure the GUI reserves space for these widgets even if they are hidden.
        # This prevents the GUI jumping around when buttons are clicked:
        for widget in [
            self.ui.pushButton_stop,
            self.ui.doubleSpinBox_maxrate,
            self.ui.toolButton_nomax,
        ]:
            size_policy = widget.sizePolicy()
            size_policy.setRetainSizeWhenHidden(True)
            widget.setSizePolicy(size_policy)

        self.image_receiver = ImageReceiver(
            self.image, self.ui.label_fps, self.ui.pushButtonAutoLevels
        )
        self.acquiring = False

        self.supports_smart_programming(self.use_smart_programming)

    def get_save_data(self):
        save_data = {
            'attribute_visibility': self.attributes_dialog.comboBox.currentText(),
            'acquiring': self.acquiring,
            'max_rate': self.ui.doubleSpinBox_maxrate.value(),
            'colormap': repr(self.image.ui.histogram.gradient.saveState()),
            'autolevels': self.ui.pushButtonAutoLevels.isChecked(),
        }
        # The view of the image shown, if any: its shape and dtype, ranges and levels.
        # BLACS saves these with repr() and restores them with eval(), so numpy scalars
        # become Python floats.
        image = self.image.image
        if image is not None:
            save_data['image_shape'] = repr(image.shape)
            save_data['image_dtype'] = str(image.dtype)
            view_box = self.image.getImageItem().getViewBox()
            targetRange_x, targetRange_y = view_box.targetRange()
            save_data['targetRange_x'] = [float(x) for x in targetRange_x]
            save_data['targetRange_y'] = [float(y) for y in targetRange_y]
            autoRange_x, autoRange_y = view_box.autoRangeEnabled()
            save_data['autoRange_x'] = autoRange_x
            save_data['autoRange_y'] = autoRange_y
            color_scale_min, color_scale_max = self.image.getLevels()
            save_data['color_scale_min'] = float(color_scale_min)
            save_data['color_scale_max'] = float(color_scale_max)
        return save_data

    def restore_save_data(self, data):
        self.attributes_dialog.comboBox.setCurrentText(
            data.get('attribute_visibility', 'simple')
        )
        self.ui.doubleSpinBox_maxrate.setValue(data.get('max_rate', 0))
        if data.get('acquiring', False):
            # Begin acquisition
            self.on_continuous_clicked(None)
        if 'colormap' in data:
            self.image.ui.histogram.gradient.restoreState(
                ast.literal_eval(data['colormap'])
            )
        self.ui.pushButtonAutoLevels.setChecked(data.get('autolevels', False))
        if 'image_shape' in data and 'image_dtype' in data:
            # A blank image of the saved shape and dtype, so that the first real image
            # does not reset the view restored here.
            image_shape = ast.literal_eval(data['image_shape'])
            image_dtype = np.dtype(data['image_dtype'])
            self.image.setImage(np.zeros(image_shape, dtype=image_dtype))
            view_box = self.image.getImageItem().getViewBox()
            if 'targetRange_x' in data and 'targetRange_y' in data:
                view_box.setRange(
                    xRange=data['targetRange_x'],
                    yRange=data['targetRange_y'],
                    padding=0,
                )
            if 'autoRange_x' in data and 'autoRange_y' in data:
                view_box.enableAutoRange(x=data['autoRange_x'], y=data['autoRange_y'])
            if 'color_scale_min' in data and 'color_scale_max' in data:
                self.image.setLevels(data['color_scale_min'], data['color_scale_max'])

    def initialise_workers(self):
        table = self.settings['connection_table']
        connection_table_properties = table.find_by_name(self.device_name).properties
        # The device properties can vary from shot to shot; at startup the values in
        # the connection table are set, for manual mode acquisition.
        with h5py.File(table.filepath, 'r') as f:
            device_properties = labscript_utils.properties.get(
                f, self.device_name, "device_properties"
            )
        worker_initialisation_kwargs = {
            'serial_number': connection_table_properties['serial_number'],
            'orientation': connection_table_properties['orientation'],
            'camera_attributes': device_properties['camera_attributes'],
            'manual_mode_camera_attributes': connection_table_properties[
                'manual_mode_camera_attributes'
            ],
            'image_receiver_port': self.image_receiver.port,
        }
        self.create_worker(
            'main_worker', self.worker_class, worker_initialisation_kwargs
        )
        self.primary_worker = "main_worker"

    @define_state(MODE_MANUAL, queue_state_indefinitely=True, delete_stale_states=True)
    def update_attributes(self):
        attributes_text = yield (
            self.queue_work(
                self.primary_worker,
                'get_attributes_as_text',
                self.attributes_dialog.comboBox.currentText(),
            )
        )
        self.attributes_dialog.plainTextEdit.setPlainText(attributes_text)

    def on_attributes_clicked(self, button):
        self.attributes_dialog.show()
        self.on_attr_visibility_level_changed(None)

    def on_attr_visibility_level_changed(self, value):
        self.attributes_dialog.plainTextEdit.setPlainText("Reading attributes...")
        self.update_attributes()

    def on_continuous_clicked(self, button):
        self.ui.pushButton_snap.setEnabled(False)
        self.ui.pushButton_attributes.setEnabled(False)
        self.ui.pushButton_continuous.hide()
        self.ui.pushButton_stop.show()
        self.ui.doubleSpinBox_maxrate.show()
        self.ui.toolButton_nomax.show()
        self.ui.label_fps.show()
        self.ui.label_fps.setText('? fps')
        self.acquiring = True
        max_fps = self.ui.doubleSpinBox_maxrate.value()
        dt = 1 / max_fps if max_fps else 0
        self.start_continuous(dt)

    def on_stop_clicked(self, button):
        self.ui.pushButton_snap.setEnabled(True)
        self.ui.pushButton_attributes.setEnabled(True)
        self.ui.pushButton_continuous.show()
        self.ui.doubleSpinBox_maxrate.hide()
        self.ui.toolButton_nomax.hide()
        self.ui.pushButton_stop.hide()
        self.ui.label_fps.hide()
        self.acquiring = False
        self.stop_continuous()

    def on_set_bg_clicked(self, button=None):
        if not self.image_receiver.set_bg_image():
            return
        self.ui.pushButton_set_bg.hide()
        self.ui.pushButton_clear_bg.show()

    def on_clear_bg_clicked(self, button=None):
        self.image_receiver.clear_bg_image()
        self.ui.pushButton_set_bg.show()
        self.ui.pushButton_clear_bg.hide()

    def on_copy_clicked(self, button):
        text = self.attributes_dialog.plainTextEdit.toPlainText()
        clipboard = QtWidgets.QApplication.instance().clipboard()
        clipboard.setText(text)

    def on_reset_rate_clicked(self):
        self.ui.doubleSpinBox_maxrate.setValue(0)

    def on_max_rate_changed(self, max_fps):
        if self.acquiring:
            self.stop_continuous()
            dt = 1 / max_fps if max_fps else 0
            self.start_continuous(dt)

    @define_state(MODE_MANUAL, queue_state_indefinitely=True, delete_stale_states=True)
    def on_snap_clicked(self, button=None):
        yield (self.queue_work(self.primary_worker, 'snap'))

    @define_state(MODE_MANUAL, queue_state_indefinitely=True, delete_stale_states=True)
    def start_continuous(self, dt):
        yield (self.queue_work(self.primary_worker, 'start_continuous', dt))

    @define_state(MODE_MANUAL, queue_state_indefinitely=True, delete_stale_states=True)
    def stop_continuous(self):
        yield (self.queue_work(self.primary_worker, 'stop_continuous'))

    def restart(self, *args, **kwargs):
        # The receiving server must be stopped on a restart, or it is not cleaned up.
        self.image_receiver.shutdown()
        return DeviceTab.restart(self, *args, **kwargs)
