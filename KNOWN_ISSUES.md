# Known issues

- `PhaseMatrixQuickSyn/blacs_workers.py`: the worker's `update_reference_out`, `update_blanking` and `update_lock_recovery` do nothing, and `transition_to_buffered` writes `OUTP:STAT 1` without the `\r` every other command ends with and ignores the shot's gate.
- `FlyCapture2Camera/blacs_workers.py`: `_send_format7_config` skips Format7 settings that fail validation without saying so.
- `PulseBlaster/labscript_devices.py`, `PulseBlaster_No_DDS/labscript_devices.py`: each delay reaches SpinAPI as float nanoseconds (`delaydouble`), which for about 9% of step lengths sits ~1e-12 cycles below a whole core cycle; if SpinAPI truncates, every repetition of such a looped step runs one cycle short, compounding over a ramp (about 39 µs over 2,905 steps). Unverified: settle it from SpinAPI's source or by timing a long looped ramp.
- `RFBlaster/blacs_workers.py`: `http_request` retries, and restarts kloned, only on urllib's and the built-in errors, but `requests` raises its own (`requests.exceptions.ConnectionError`, `Timeout`, `HTTPError`), so a failed request raises at once, without a retry.
- `CiceroOpalKellyXEM3001/labscript_devices.py`: `trigger_debounce_clock_ticks` is checked only against 65535, so a negative value compiles, though the error message says 0 to 65535.
- `PhaseMatrixQuickSyn/labscript_devices.py`: `generate_code` raises UnboundLocalError for a QuickSyn with no DDS connected; with two connected, it uses only the last.
- `LightCrafterDMD/labscript_devices.py`: `generate_code` raises IndexError for a DMD with no ImageSet, and `ImageSet.set_image` raises struct.error, not LabscriptError, for raw bytes that start with BM but are under 30 bytes long.
- `LightCrafterDMD/blacs_workers.py`: `transition_to_buffered` leaves `table_data` unbound when the shot has no IMAGE_TABLE, and `program_manual` uses only the last region and leaves `data` unbound when given none. Read, not run.
- `AlazarTechBoard/blacs_workers.py`: `find_nearest_internal_clock` makes a 0-d array of the `dict_keys` it is given, so `transition_to_buffered` with the default `INTERNAL_CLOCK` raises TypeError (as upstream).
