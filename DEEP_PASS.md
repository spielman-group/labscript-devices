# labscript-devices deep pass

The code-health campaign's record for the `CodeHealth` branch: what it changes
for a lab, what must merge with it, the decisions it follows, and what it
leaves open. It is deleted in the last commit before `CodeHealth` merges into
`Development`.

## Merging

`CodeHealth` needs the other repos' `CodeHealth` at or after labscript
`b273fbf`, labscript-utils `84dde2b`, blacs `6a2c5a2` and runviewer `edcc0a7`.

Every lab recompiles its connection table once after the merge.

## What a lab sees

### Old forms that still work, with a FutureWarning

Each warns at the script's line and is marked `# LEGACY … DEPRECATED CODE, WILL
BE REMOVED.` in the code. Reading a file written before a change warns once,
through labscript-utils' `warn_legacy_file`.

- Keywords: PineBlaster's `usbport` is `com_port`; RFBlaster's `ip_address` and
  LightCrafterDMD's `server` are `host`; Cicero's `serial` is `serial_number`.
- A PulseBlaster subclass's or workerarg's `core_clock_freq`, in MHz, for
  `clock_frequency`, in Hz.
- A NovaTech DDS connected as `'channel n'`: every DDS connects as `'dds n'`.
- A PulseBlaster DDS amplitude calibration in `'Vpp'`: every amplitude is
  `'Arb'`, 0 to 1.
- `test_device`, which is `TestDevice`.
- `PineBlaster.clock_type` and `PhaseMatrixQuickSyn.generation`, wherever read.
- The pre-NI_DAQmx import paths `NI_PCI_6733`, `NI_PCIe_6363` and
  `NI_USB_6343`, which give the NI_DAQmx class.
- `labscript_devices.TekScope.TekScope`, the driver module, which is
  `labscript_devices.TekScope.driver`.
- A camera serial number given as an unprefixed string, which is decimal; IMAQdx,
  which read it as hex, warns.
- Old files: PrawnDO's `pulse_program` dataset, now `PULSE_PROGRAM`; a
  connection table without NovaTech's or PulseBlaster's newer properties, with
  NovaTech's phase mode `'default'`, or from NI_DAQmx's old model
  specification; a front panel saved with NovaTech's old output names or
  RFBlaster's `%`; a shot file without labscript's saved trigger times, in
  runviewer.

### Changes with no old form

- **Connection tables:** the internal pseudoclock, clockline and wait-monitor
  devices of Cicero, PineBlaster, RFBlaster, DummyPseudoclock, PrawnBlaster and
  PrawnDO have new classes; the classes they replaced cannot be imported.
- **Class names:** the tabs, workers and parsers carry their role after the
  device's name (`NI_DAQmxTab`, `PulseBlaster_No_DDSTab`), so lab code that
  imports an old name, or names one in a worker-class string, fails.
- **PulseBlaster:** PulseBlaster_No_DDS and its models, and their parsers, no
  longer subclass PulseBlaster's; `convert_to_pb_inst` takes only the digital
  outputs; each board's flag count is the connection table's `n_flags`.
- **Cameras:** `set_attributes(attributes)`, so a call by `attr_dict=` or
  `attributes_dict=` fails; `configure_acquisition(continuous=True,
  buffer_count=None)`; the interface classes are `<Device>Interface`;
  Spinnaker's `set_attribute(name, value)`, with `set_stream_attribute`.
- **Cicero:** `use_wait_monitor` defaults to True on a master, so a script that
  makes its own WaitMonitor on one fails and needs `use_wait_monitor=False`; a
  secondary asked for one raises.
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
- **NI_DAQmx:** every task is cleared on every path, and analog input keeps the
  samples after its last full chunk.
- **AndorSolis:** an EM gain without `cooldown` warns, not refused; cooling
  starts without waiting; the temperature is printed every shot.
- **TekScope:** `acquire_mode`, `stop_after` and `channels` keywords; `int16`
  traces read correctly.
- **runviewer:** it shows ESRPro500 shots, and draws every trace on script time,
  in which a wait takes no time: a trace moves earlier by its master's
  `wait_delay` for each wait before it, a secondary PineBlaster starts 350 ns
  after its trigger, and a secondary PulseBlaster at its trigger.
- **Compiles that failed:** an AlazarTechBoard with two acquisitions, and PrawnDO
  ramps and `repeat_pulse_sequence`, compile.

## Decisions in force (Ian)

- A public interface that changes keeps its old form working, with a
  FutureWarning at the user's line and the LEGACY comment; an internal one
  changes outright. A public name is kept, used or not, unless Ian says
  otherwise.
- Each device is a package. Its `__init__` imports the labscript-side names,
  which make up `__all__`, and gives the BLACS- and runviewer-side names
  lazily, so a compile never imports BLACS (`tests/test_device_packages.py`).
- blacs keeps only the generic `Worker` and `DeviceTab`. `PseudoclockWorker`,
  `PseudoclockTab`, `GuilessTab` and `GuilessWorker` live here.
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

## Open

For Ian:

- AndorSolis's `shutdown` closes no shutter and calls no `CoolerOFF` before
  `ShutDown`, as micro-manager's Andor adapter does.
- PulseBlaster's base still knows of DDS outputs in two places: its parser's
  `num_dds` loop and `'dds'` prefix test, and its tab's empty "DDS Outputs"
  palette.
- runviewer under a DummyIntermediateDevice trigger (`KNOWN_ISSUES.md`): a
  parser for DummyIntermediateDevice would supply the trigger's trace.
- NI_DAQmx releases no task before BLACS terminates a worker, on a restart or
  a tab's close; Ian deferred it, as only failed and aborted runs leaked.

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
- IMAQdxCamera: a camera given an unprefixed serial.
