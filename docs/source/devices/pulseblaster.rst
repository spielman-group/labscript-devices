Pulseblaster
============

This labscript device controls the Spincore PulseblaserDDS-II-300-AWG.
The Pulseblaster is a programmable pulse generator that is the typical timing backbone of an experiment (ie it generates the pseudoclock timing pulses that control execution of other devices in the experiment).
The code every Pulseblaster board shares is in `PulseBlasterBase`, and this device adds its DDS outputs to it with `DDSPulseBlasterMixin`; its BLACS tab, worker and runviewer parser are built the same way.
The boards without DDS subclass `PulseBlasterBase` alone, each with its own hard-coded values.
Most importantly, the `clock_frequency`, in Hz, must be manually set to match that of the Pulseblaster being used in order for the timing of the programmed pulses to be correct (in the `labscript_device` and the `BLACS_worker`).

This particular version of Pulseblaster has a 75 MHz core clock frequency and also has DDS synthesizer outputs.

Installation
~~~~~~~~~~~~

Use of the Pulseblaster requires driver installation available from the manufacturer `here <https://www.spincore.com/support/>`_.
The corresponding python wrapper, `spinapi <https://github.com/chrisjbillington/spinapi/>`_ is available via pip.

.. code-block:: bash

	pip install -U spinapi

Usage
~~~~~

`board_number` is the SpinCore board index, which BLACS passes to `pb_select_board`.
The PulseBlaster has 12 flags, `'flag 0'` to `'flag 11'`, and two DDS outputs, `'dds 0'` and `'dds 1'`.
Each flag is either a clock line, a `ClockLine` on `pb.pseudoclock`, or a `DigitalOut` on `pb.direct_outputs`.
DDS outputs, `DDS` or `PulseBlasterDDS`, also go on `pb.direct_outputs`; their gate is internal to the PulseBlaster, so they take no `digital_gate`.
Outputs on `pb.direct_outputs` cannot ramp.

.. code-block:: python

	from labscript import *

	from labscript_devices.PulseBlaster.labscript_devices import PulseBlaster, PulseBlasterDDS

	PulseBlaster(name='pb',board_number=0,programming_scheme='pb_start/BRANCH')

	ClockLine(name='pb_clockline_fast', pseudoclock=pb.pseudoclock,connection='flag 0')
	ClockLine(name='pb_clockline_slow', pseudoclock=pb.pseudoclock,connection='flag 1')

	DigitalOut(name='pb_0',parent_device=pb.direct_outputs,connection='flag 2')

	PulseBlasterDDS(name='pb_dds_0',parent_device=pb.direct_outputs,connection='dds 0')

	start()

	stop(1)

Detailed Documentation
~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: labscript_devices.PulseBlaster.labscript_devices
   :members:
   :undoc-members:
   :show-inheritance:
   :private-members:

.. automodule:: labscript_devices.PulseBlaster.blacs_tabs
   :members:
   :undoc-members:
   :show-inheritance:
   :private-members:

.. automodule:: labscript_devices.PulseBlaster.blacs_workers
   :members:
   :undoc-members:
   :show-inheritance:
   :private-members:

.. automodule:: labscript_devices.PulseBlaster.runviewer_parsers
   :members:
   :undoc-members:
   :show-inheritance:
   :private-members:
