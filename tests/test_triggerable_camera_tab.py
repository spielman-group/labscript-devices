"""Camera tab controls and the settings BLACS restores and archives."""
import unittest
from pathlib import Path

import numpy as np
import pyqtgraph as pg

import labscript_utils.h5_lock  # must precede h5py, as the tab itself does
import h5py

from qtutils.qt import QtWidgets
from qtutils import UiLoader

from blacs import BLACS_DIR
from blacs.front_panel_settings import FrontPanelSettings

from labscript_devices.common.triggerable_camera.blacs_tabs import TriggerableCameraTab
from labscript_devices.common.triggerable_camera import blacs_tabs


ATTRIBUTES = 'AcquisitionAttributes::Bitspp: 8\nCameraAttributes::Gain: 1.0\n'


def a_qapplication():
    """One QApplication for the whole process, as Qt requires."""
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication(['test'])


class AnAttributesDialog:
    """The dialog the tab loads from its .ui file, reduced to what is read."""

    def __init__(self, text):
        self.plainTextEdit = QtWidgets.QPlainTextEdit()
        self.plainTextEdit.setPlainText(text)


class CameraTabTests(unittest.TestCase):
    def setUp(self):
        self.qapplication = a_qapplication()
        # __init__ builds a whole BLACS tab against a camera; on_copy_clicked
        # reads only the dialog, so give it one and nothing else:
        self.tab = TriggerableCameraTab.__new__(TriggerableCameraTab)
        self.tab.attributes_dialog = AnAttributesDialog(ATTRIBUTES)
        self.qapplication.clipboard().clear()

    def test_copy_puts_the_attributes_on_the_clipboard(self):
        self.tab.on_copy_clicked(None)

        self.assertEqual(self.qapplication.clipboard().text(), ATTRIBUTES)

    def test_camera_preferences_restore_but_are_not_archived_with_a_shot(self):
        tab = self.tab
        tab._ui = UiLoader().load(str(Path(BLACS_DIR) / 'tab_frame.ui'))
        tab.ui = UiLoader().load(str(Path(blacs_tabs.__file__).with_name('blacs_tab.ui')))
        tab.attributes_dialog.comboBox = QtWidgets.QComboBox()
        tab.attributes_dialog.comboBox.addItems(['simple', 'advanced'])
        tab.attributes_dialog.comboBox.setCurrentText('advanced')
        tab.acquiring = False
        tab.ui.doubleSpinBox_maxrate.setValue(7)
        tab.ui.pushButtonAutoLevels.setChecked(True)
        tab.image = pg.ImageView()
        for widget in (tab._ui, tab.ui, tab.image, tab.attributes_dialog.comboBox):
            self.addCleanup(widget.close)
        tab.image.setImage(np.zeros((12, 16), dtype=np.uint16))
        tab.image.getView().setRange(xRange=(2, 8), yRange=(3, 9), padding=0)
        tab.image.setLevels(10, 200)
        preferences = tab.get_save_data()
        saved = tab.get_all_save_data()

        tab.ui.pushButtonAutoLevels.setChecked(False)
        tab.image.setLevels(0, 1)
        tab.restore_save_data(saved)
        self.assertEqual(tab.get_save_data(), preferences)

        tab.settings = {'front_panel_settings': {}}
        front_panel = FrontPanelSettings.__new__(FrontPanelSettings)
        front_panel.tablist = {'camera': tab}
        self.assertEqual(front_panel.get_shot_data()['camera']['saved_data'], {})


if __name__ == '__main__':
    unittest.main()
