# Known issues

- `PhaseMatrixQuickSyn/blacs_workers.py`: the worker's `update_reference_out`, `update_blanking` and `update_lock_recovery` do nothing, and `transition_to_buffered` writes `OUTP:STAT 1` without the `\r` every other command ends with and ignores the shot's gate.
- `FlyCapture2Camera/blacs_workers.py`: `_send_format7_config` skips Format7 settings that fail validation without saying so.
- `PulseBlaster/labscript_devices.py`, `PulseBlaster_No_DDS/labscript_devices.py`: each delay reaches SpinAPI as float nanoseconds (`delaydouble`), which for about 9% of step lengths sits ~1e-12 cycles below a whole core cycle; if SpinAPI truncates, every repetition of such a looped step runs one cycle short, compounding over a ramp (about 39 µs over 2,905 steps). Unverified: settle it from SpinAPI's source or by timing a long looped ramp.
- `PrawnBlaster/blacs_workers.py`: `wait_for_trigger` polls with no deadline while the board reports run status 1, so a board stuck there hangs `transition_to_buffered`.
- `PrawnBlaster/blacs_workers.py`, `PrawnDO/blacs_workers.py`: `abort` counts only run status 5 as aborted, so if the firmware leaves a board that never ran at status 0, `abort_transition_to_buffered` fails after `end_of_shot_timeout`. Unverified: settle it from the firmware.
- `LightCrafterDMD/blacs_workers.py`: `receive` retries a "System Busy" reply every 5 s with no limit, so a DMD that stays busy hangs every transition and abort.
- `PrawnDO/labscript_devices.py` generate_code: `np.asarray(output.timeseries, dtype=np.uint16)` fails on a function instruction, so `repeat_pulse_sequence` (and any future digital ramp) on a PrawnDO output does not compile; use `output.raw_output`.
- `RFBlaster/blacs_workers.py`: `http_request` calls `requests.get` and `requests.post` with no timeout, so an RFBlaster that stops answering hangs its worker.
- `CiceroOpalKellyXEM3001/labscript_devices.py`: `trigger_debounce_clock_ticks` is checked only against 65535, so a negative value compiles, though the error message says 0 to 65535.
- `PhaseMatrixQuickSyn/labscript_devices.py`: `generate_code` raises UnboundLocalError for a QuickSyn with no DDS connected; with two connected, it uses only the last.
- `LightCrafterDMD/labscript_devices.py`: `generate_code` raises IndexError for a DMD with no ImageSet, and `ImageSet.set_image` raises struct.error, not LabscriptError, for raw bytes that start with BM but are under 30 bytes long.
- `LightCrafterDMD/blacs_workers.py`: `transition_to_buffered` leaves `table_data` unbound when the shot has no IMAGE_TABLE, and `program_manual` uses only the last region and leaves `data` unbound when given none. Read, not run.
- `AlazarTechBoard/labscript_devices.py`: `generate_code` calls `init_device_group` inside its loop over acquisitions, so a board with two or more acquisitions does not compile (ValueError, name already exists).
- `AlazarTechBoard/blacs_workers.py`: the worker keeps `sys.exc_info()` and later raises that tuple, a TypeError, and an unknown `chA_input_range` or `chB_input_range` is printed and then used unbound. Read, not run.
