# labscript-devices deep pass

The code-health campaign's record for the `CodeHealth` branch: what it changes
for a lab, what must merge with it, the decisions it follows, and what it
leaves open. It is deleted in the last commit before `CodeHealth` merges into
`Development`.

## Merging

`CodeHealth` needs the other repos' `CodeHealth` at or after labscript
`b273fbf`, labscript-utils `84dde2b`, blacs `6a2c5a2` and runviewer `edcc0a7`.

It needs Python 3.13, qtutils 4.4.3, zprocess 3.0.1 and filelock 3.12, and no
longer PyNIVision.

Every lab recompiles its connection table once after the merge.

## What a lab sees

### Old forms that still work, with a FutureWarning

Each warns at the script's line and is marked `# LEGACY … DEPRECATED CODE, WILL
BE REMOVED.` in the code. Reading a file written before a change warns once,
through labscript_profile's `warn_legacy_file`.

Kept because upstream's own form keeps them, or Ian said so:

- A name imported from the package of a device that was once a single module,
  such as `labscript_devices.PulseBlaster`, as upstream gives it.
- The pre-NI_DAQmx import paths `NI_PCI_6733`, `NI_PCIe_6363` and
  `NI_USB_6343`, which give the NI_DAQmx class: upstream's, and Ian's step 2.4
  row 1.
- A PulseBlaster subclass's or workerarg's `core_clock_freq`, in MHz, for
  `clock_frequency`, in Hz: Ian (`c0c0003`).
- A camera serial number given as an unprefixed string, which is decimal;
  IMAQdx, which read it as hex, as upstream reads every camera's, warns: Ian
  (C-LD3).
- Old shot files and connection tables: PrawnDO's `pulse_program` dataset, now
  `PULSE_PROGRAM`; a connection table without NovaTech's or PulseBlaster's
  newer properties, or from NI_DAQmx's old model specification; a shot file
  without labscript's saved trigger times, in runviewer: Ian (C-LD4).
  NovaTech's phase mode `'default'` is upstream's.

### Changes with no old form

- **New devices,** from upstream: NarwhalPulseGenerator, AD9959DDSSweeper,
  Windfreak's SynthHD and SynthHD Pro, ThorlabsTSICamera and GenICamCamera,
  with `labscript_devices.common.usbserial` for FTDI serial adaptors.
- **Connection tables:** the internal pseudoclock, clockline and wait-monitor
  devices of Cicero, PineBlaster, RFBlaster, DummyPseudoclock, PrawnBlaster and
  PrawnDO have new classes; the classes they replaced cannot be imported.
- **Class names:** the tabs, workers and parsers carry their role after the
  device's name (`NI_DAQmxTab`, `PulseBlaster_No_DDSTab`), so lab code that
  imports an old name, or names one in a worker-class string, fails.
- **PulseBlaster:** PulseBlaster_No_DDS and its models, and their parsers, no
  longer subclass PulseBlaster's; `convert_to_pb_inst` takes only the digital
  outputs; each board's flag count is the connection table's `n_flags`. The
  base parser and tab know only flags, and `DDSPulseBlasterParserMixin` draws
  the DDS outputs.
- **Cameras:** `set_attributes(attributes)`, so a call by `attr_dict=` or
  `attributes_dict=` fails; `configure_acquisition(continuous=True,
  buffer_count=None)`; the interface classes are `<Device>Interface`, subclasses
  of `CameraInterface`, in `labscript_devices.common.triggerable_camera` with
  the rest of the camera base; Spinnaker's `set_attribute(name, value)`, with
  `set_stream_attribute`. `mock=True` drives upstream's `MockCamera`, and every
  shot's images carry `mock_data`. A worker shut down mid-shot aborts the shot
  before closing the camera, and one whose init failed still closes it. An
  abort disarms a camera armed for a shot whose acquisition thread never ran,
  and joins one interrupted after it started; stopping continuous acquisition
  is not held up by a tab that never replies.
- **Moved modules:** `labscript_devices.atsapi` is
  `labscript_devices.AlazarTechBoard.atsapi`, as upstream's is.
- **Refused old forms**, each with a message naming the new one (Ian, C-LD1 and
  C-LD2): a NovaTech DDS connected as `'channel n'`, which connects as
  `'dds n'`, in a compile or an old shot in runviewer; a PulseBlaster DDS
  amplitude calibration in `'Vpp'`, whose base unit is `'Arb'`, 0 to 1;
  `test_device`, which is `TestDevice`; the old keywords: PineBlaster's
  `usbport` is `com_port`; RFBlaster's `ip_address` and LightCrafterDMD's
  `server` are `host`; Cicero's `serial` is `serial_number`.
- **Front panels** saved under NovaTech's `'channel n'` names, or with
  RFBlaster's amplitudes in `%`, are not converted, and those values are not
  restored (Ian, C-LD4).
- **Cicero:** `use_wait_monitor` defaults to True on a master, so a script that
  makes its own WaitMonitor on one fails and needs `use_wait_monitor=False`; a
  secondary asked for one raises. Its firmware `.bit` files go in the
  `CiceroOpalKellyXEM3001` package folder, as upstream's, not `labscript_devices/`.
- **Refused when compiled or connected**, where they compiled or failed later:
  a DDS on a PulseBlaster without DDS; a `digital_gate` on a PulseBlasterDDS; an
  RFBlaster without `trigger_device`, or with a value outside the board's range;
  NI_DAQmx's `static_AO=False` or `static_DO=False` on a board that cannot
  buffer them; an AlazarTechBoard without channel A, or on its external clock
  at rate 0; a FunctionRunner lambda; a camera serial with letters and no
  `0x`; a LightCrafterDMD without an ImageSet, or with short bitmap bytes; a
  PhaseMatrixQuickSyn without exactly one DDS; a negative Cicero debounce.
  An out-of-range DDS value raises labscript's error, naming the value and the
  limits.
- **Deadlines:** PrawnBlaster's arming, NI_DAQmx's wait-monitor stop and wait
  durations, LightCrafterDMD's commands and RFBlaster's requests raise
  "<device> did not <what> within <seconds> s." where they hung. RFBlaster
  does not retry.
- **Aborts:** every worker aborts through `abort()`. A FunctionRunner whose own
  start function raised runs its stop functions.
- **NI_DAQmx:** every task is cleared on every path. Analog input keeps the
  samples after its last full chunk, raises a buffer overflow at the end of a
  shot rather than losing the shot's end, and discards an aborted shot's.
- **AndorSolis:** an EM gain without `cooldown` warns, not refused; cooling
  starts without waiting; the temperature is printed every shot. The
  `em_gain_mode` attribute, 0 by default, is set before the gain range is read.
  A camera without a keep-clean cycle or crop mode can be set up, and only an
  iXon Ultra crops anywhere. Shutting down closes the shutter and stops the
  cooler before `ShutDown`, as micro-manager's Andor adapter does. An abort
  leaves the camera disarmed, so it shuts down after a shot that never began. A single acquisition's image is saved 2D, without
  a leading axis of one.
- **Cameras' tab:** a frame arriving during a tab restart no longer deadlocks
  BLACS. The tab has Auto Levels and a background subtracted from the
  displayed image, and keeps its view across a restart of BLACS.
- **IMAQdxCamera:** NI-IMAQdx is called through ctypes, not pynivision; boolean
  attributes are saved as booleans.
- **DummyCamera:** its images are marked `mock_data`, not `NOT_REAL_DATA`, so
  lyse's column is `(<orientation>, 'mock_data')`.
- **TekScope:** `acquire_mode`, `stop_after` and `channels` keywords; `int16`
  traces read correctly.
- **More refusals:** two analog outputs in one bank of an NI PCIe-6738 or
  PXIe-6738 above 400 kS/s (pass `max_AO_sample_rate=400e3`); a PrawnBlaster
  wait timeout, period or repeat count, or a PrawnDO interval, beyond the
  firmware's 32 bits, which wrapped silently.
- **PulseBlaster:** the direct outputs use their board's own `clock_limit`; the
  ESR-PRO-500 has 24 flags. **PhaseMatrixQuickSyn** ends its `OUTP:STAT`
  command with `\r`.
- **runviewer:** it shows ESRPro500 shots, and draws every trace on script time,
  in which a wait takes no time: a trace moves earlier by its master's
  `wait_delay` for each wait before it, a secondary PineBlaster starts 350 ns
  after its trigger, and a secondary PulseBlaster at its trigger. It draws a
  DummyIntermediateDevice's outputs, which give a trigger's trace to the
  devices below, and an NI_DAQmx output whose connection has a PFI suffix.
- **Compiles that failed:** an AlazarTechBoard with two acquisitions, and PrawnDO
  ramps and `repeat_pulse_sequence`, compile.

## Decisions in force (Ian)

- No old form is kept unless Ian says so or upstream keeps it. One that is
  kept warns at the user's line, through upstream's `deprecated_names` for an
  import path, and carries the LEGACY comment. A name or path that only the
  fork's branches had changes outright: the merge into Development replaces it.
- Each device is a package with upstream's `__init__`: one that was once a
  single module gives its old names through `deprecated_names`, and the rest
  are empty. A compile never imports BLACS (`tests/test_device_packages.py`).
- blacs keeps only the generic `Worker` and `DeviceTab`. `PseudoclockWorker`,
  `PseudoclockTab`, `GuilessTab` and `GuilessWorker` live here, in
  `labscript_devices.common`, with the other code shared by devices.
- What a tab and worker need to know of a device is a connection-table
  property, which BLACS passes to the worker, as NI_DAQmx's channel counts are.
  A worker's default is a class attribute, which a workerarg overrides.
- Every DAQmx task is cleared on every path, by `DAQmxTaskOwner.release_tasks`.
- A board that confirms its abort or end of shot after the deadline counts as
  done.
- PulseBlaster's transition abort leaves the board programmed, as blacs
  reprograms it.
- runviewer draws on script time: a secondary starts `trigger_delay` after the
  trigger times labscript saves (`PseudoclockParser`).
- lyse tooling inside FunctionRunner's functions is not supported.
- An upstream fix is ported by hand onto `CodeHealth`, crediting its upstream
  commit. `master` is never merged in, and `DummyCamera` never merged inward.
- Where upstream's form differs and fits, the fork takes upstream's. An owner
  rules a change only "not possible", for code that has drifted too far or an
  earlier decision of Ian's; any other choice is Ian's.

## Upstream

`CodeHealth` has upstream's `master` to `63648fd`: each of its commits is in,
ported by hand or cherry-picked with `-x`, or left by a decision in
`issues/upstream_adoption_review.md`. Where the fork keeps its own form:

- The docs link Qt names to the PyQt6 inventory, the suite's binding.
- `FunctionRunner.add_function`'s docstring documents the fork's refusals and
  runmanager's `set_values`, without upstream's `lyse.Run` example.
- The camera list names no `Camera` or `PythonCamera`, which the fork lacks.
- IMAQdx reads an unprefixed string serial number as decimal, and warns.
- The Python classifiers start at 3.13, the suite's floor.

Left by decision: AndorSolis's `SetupAcquisitionFast` and acquisition-start
semaphores (#144, of which only the camera-compatibility parts were taken),
the legacy `Camera` device (#168) and upstream's `DummyCamera` (#176; the
fork has its own).

## Open

For Ian:

- NI_DAQmx releases no task before BLACS terminates a worker, on a restart or
  a tab's close; deferred until blacs's quit-message design.
- A camera class that does not subclass `CameraInterface`, which upstream's
  form supports, runs only under `IMAQdxCameraWorker`, which warns, and
  configures it positionally. Taking upstream's worker-level
  `get_attributes_as_dict` would make that route unneeded.
- The camera base's interface differs from upstream's:
  `configure_acquisition(continuous, buffer_count=None)`, not `bufferCount=5`;
  `set_attributes(attributes)`, not `attr_dict`; `get_attributes_as_dict` on the
  camera, not the worker; `transition_to_buffered`'s `h5_file`, not
  `h5_filepath`; `restore_save_data(data)`; a camera's `__init__` need not call
  `super().__init__()`.

Lab checks, on `Development`:

- NI_DAQmx: a shot with its start pulse unplugged fails rather than hangs; the
  chunked counter reads record every wait; analog input keeps every sample
  after its last full chunk, a late callback's too, with no buffer error;
  stopping an acquisition during a callback does not hang; after a failed stop
  the next shot runs without a driver reset; a restarted tab's tasks are
  released by the driver.
- PulseBlaster: whether the labs' Windows `spinapi64.dll` rounds float-ns
  delays (`KNOWN_ISSUES.md`); a tab started from a connection table without
  `n_flags`.
- PrawnBlaster: a one-pseudoclock program that fills its table.
- TekScope: an `int16` shot, its points and time axis; `channels` naming a
  hidden channel.
- SpinnakerCamera: one that fails to open leaves PySpin usable; the saved
  attributes at each visibility level.
- AndorSolis: EMCCD gain with cooldown, the temperature printed at set-up; an
  abort during a series; a preamp gain such as 2.4.
- IMAQdxCamera: a camera given an unprefixed serial; a shot and continuous
  acquisition through the ctypes module.
- Cameras' tab: a restart during continuous acquisition; Auto Levels and the
  background buttons.
- AndorSolis: an older camera without a keep-clean cycle or crop mode, and an
  iXon Ultra cropping.
- PulseBlaster: the status icons on a high-DPI screen.
- NI_DAQmx: analog input whose read callback falls behind by more than the
  buffer raises the overflow at the end of the shot, and the next shot runs.
- The new devices: none has run on hardware here; a lab with one runs a shot.
- AndorSolis: quitting BLACS closes the shutter and stops the cooler.
- Cameras: a shot whose acquisition times out with `exception_on_failed_shot`
  False is followed by a shot that acquires every image.
