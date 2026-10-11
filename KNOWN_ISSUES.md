# Known issues

- `PulseBlaster.py`: a fixed `pulse_width` that is already a whole number of half clock resolutions is rounded up by one more (`int(q) + 1`, not `ceil`), so `pulse_width=1e-6` gives 1.0133 µs and lowers `clock_limit` to match.
- `PhaseMatrixQuickSyn.py`: the worker's `update_reference_out`, `update_blanking` and `update_lock_recovery` do nothing, and `transition_to_buffered` writes `OUTP:STAT 1` without the `\r` every other command ends with and ignores the shot's gate.
- `FlyCapture2Camera/blacs_workers.py`: `_send_format7_config` skips Format7 settings that fail validation without saying so.
