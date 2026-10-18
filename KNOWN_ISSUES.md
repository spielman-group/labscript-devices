# Known issues

- `PhaseMatrixQuickSyn.py`: the worker's `update_reference_out`, `update_blanking` and `update_lock_recovery` do nothing, and `transition_to_buffered` writes `OUTP:STAT 1` without the `\r` every other command ends with and ignores the shot's gate.
- `FlyCapture2Camera/blacs_workers.py`: `_send_format7_config` skips Format7 settings that fail validation without saying so.
- `PulseBlaster.py`, `PulseBlaster_No_DDS.py`: each delay reaches SpinAPI as float nanoseconds (`delaydouble`), which for about 9% of step lengths sits ~1e-12 cycles below a whole core cycle; if SpinAPI truncates, every repetition of such a looped step runs one cycle short, compounding over a ramp (about 39 µs over 2,905 steps). Unverified: settle it from SpinAPI's source or by timing a long looped ramp.
