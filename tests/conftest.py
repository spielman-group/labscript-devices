"""Keep test runs off the screen: set before Qt and labscript_utils.excepthook import."""
import os

os.environ.setdefault('LABSCRIPT_DISABLE_GRAPHICAL_EXCEPTHOOK', '1')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
