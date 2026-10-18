QuickSyn FSW-0010 Synthesizer
=============================

A labscript device that controlls the NI Quicksyn FSW-0010 Microwave Synthesizer
(formerly PhaseMatrix).

Usage
~~~~~

The QuickSyn is not clocked by a pseudoclock, so it takes no parent device, only `name` and `com_port`.
Its one output is a `QuickSynDDS` on `'dds 0'`, which has frequency control only, from 0.5 to 10 GHz; BLACS sets the frequency at the start of each shot.
`enable()` and `disable()` take no time. The gate they set is written to the shot file, but BLACS does not apply it.

.. code-block:: python

	from labscript import *

	from labscript_devices.PhaseMatrixQuickSyn import PhaseMatrixQuickSyn, QuickSynDDS

	PhaseMatrixQuickSyn(name='quicksyn', com_port='COM1')
	QuickSynDDS(name='microwaves', parent_device=quicksyn, connection='dds 0')

	start()
	microwaves.setfreq(6.8e9)
	stop(1)

Detailed Documentation
~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: labscript_devices.PhaseMatrixQuickSyn
	:ignore-module-all:
	:members:
	:undoc-members:
	:show-inheritance:
	:member-order: bysource
	:private-members:

.. automodule:: labscript_devices.PhaseMatrixQuickSyn.labscript_devices
	:members:
	:undoc-members:
	:show-inheritance:
	:member-order: bysource
	:private-members:

.. automodule:: labscript_devices.PhaseMatrixQuickSyn.blacs_tabs
	:members:
	:undoc-members:
	:show-inheritance:
	:member-order: bysource
	:private-members:

.. automodule:: labscript_devices.PhaseMatrixQuickSyn.blacs_workers
	:members:
	:undoc-members:
	:show-inheritance:
	:member-order: bysource
	:private-members:
