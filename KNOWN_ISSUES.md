# Known issues

- `PhaseMatrixQuickSyn/blacs_workers.py`: the worker's `update_reference_out`, `update_blanking` and `update_lock_recovery` do nothing, and `transition_to_buffered` writes `OUTP:STAT 1` without the `\r` every other command ends with and ignores the shot's gate.
- `FlyCapture2Camera/blacs_workers.py`: `_send_format7_config` skips Format7 settings that fail validation without saying so.
- `PulseBlaster.py`, `PulseBlaster_No_DDS.py`: each delay reaches SpinAPI as float nanoseconds (`delaydouble`), which for about 9% of step lengths sits ~1e-12 cycles below a whole core cycle; if SpinAPI truncates, every repetition of such a looped step runs one cycle short, compounding over a ramp (about 39 µs over 2,905 steps). Unverified: settle it from SpinAPI's source or by timing a long looped ramp.
- `PrawnBlaster/blacs_workers.py`: `wait_for_trigger` polls with no deadline while the board reports run status 1, so a board stuck there hangs `transition_to_buffered`.
- `PrawnBlaster/blacs_workers.py`, `PrawnDO/blacs_workers.py`: `abort_buffered` counts only run status 5 as aborted, so if the firmware leaves a board that never ran at status 0, `abort_transition_to_buffered` fails after `end_of_shot_timeout`. Unverified: settle it from the firmware.
- `NI_DAQmx/blacs_workers.py`: the wait monitor thread waits for the start pulse with no timeout, and `transition_to_manual` joins it with none, so a shot whose start pulse never reaches the counter hangs the transition.
- `LightCrafterDMD.py`: `receive` retries a "System Busy" reply every 5 s with no limit, so a DMD that stays busy hangs every transition and abort.
- `PrawnDO/labscript_devices.py` generate_code: `np.asarray(output.timeseries, dtype=np.uint16)` fails on a function instruction, so `repeat_pulse_sequence` (and any future digital ramp) on a PrawnDO output does not compile; use `output.raw_output`.
