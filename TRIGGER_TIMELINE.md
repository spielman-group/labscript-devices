# A triggered device's timeline in runviewer: design (for Ian)

Ian: "I am very much in favor of a shared model so all bugs are fixed at once."
So one model says when a pseudoclock device starts and when it resumes after
each wait, and every parser that needs it uses it. This note counts today's
copies and weighs where the model lives and what it reads. Nothing is built.

## 1. The copies today

Six parsers draw a pseudoclock device's own program, so each times its start
and its resumes. A "case" below is one branch or copied constant that exists
only for that timing; the program's own decoding (stop rows, loops) is not
counted.

| Parser | Start | Resume after wait n | Master's wait | Cases |
| --- | --- | --- | --- | --- |
| PrawnBlaster | first edge of `clock` + `trigger_delay` | counts edges: edge n+1 + `trigger_delay` | `+= wait_delay` | 4 |
| PrawnDO | first edge + `trigger_delay` | first edge at or after the shot's nth wait time, less 1 ps (`fd44105`) | `+= wait_delay` | 5 |
| PineBlaster | first edge + `trigger_delay` | counts edges | `+= wait_delay`, a constant copied into the parser | 6 |
| DummyPseudoclock | first edge + `trigger_delay` | counts edges | `+= wait_delay`; three constants copied | 7 |
| CiceroOpalKellyXEM3001 | a secondary's program begins with a wait, so its start is the wait branch | counts edges | `+= wait_delay` | 3 |
| PulseBlaster | `trigger_delay`, the trigger taken to be at 0 | `+= trigger_delay`; `clock` is never read | the WAIT row's 100 ns | 3 |

28 cases carry one rule in three versions (counting edges, searching by time,
ignoring the clock), and the masters draw each wait as lasting its
`wait_delay`. The two clocked parsers, NI_DAQmx and NovaTechDDS9M, put sample i
at edge i of `clock` and need no rule.

What each gets wrong:
- Counting edges (PrawnBlaster, PineBlaster, DummyPseudoclock, Cicero) is
  right on a trigger's trace, and wrong on a clock with other edges. Only a
  PrawnDO is ever given such a clock (section 2).
- PrawnDO: `fd44105` compares the shot's wait times with a master trace that
  has gained `wait_delay` at each wait, so after several waits it takes an
  earlier tick and time runs backward (Codex: waits at 10, 20, 30, 40 µs and a
  shared tick at 39.9 µs). `0c89814`, searching from its own wait time, is
  wrong when its coarser clock rounds that time past the retrigger.
- PulseBlaster: a secondary is drawn as if triggered at 0, so a later
  `set_initial_trigger_time` is not shown. After each wait it runs ahead of
  its master by the master's `wait_delay`.
- Not a parser's: runviewer draws nothing below a device without a parser,
  such as a secondary triggered from a DummyIntermediateDevice, since loading
  that device raises and its children are skipped.
- The masters' `wait_delay` puts every trace after n waits n × `wait_delay`
  after its script time, so traces and runviewer's markers, at script times,
  part. It is why `fd44105` fails.

## 2. What runviewer passes, and what the shot file holds

runviewer (Development) has no wait logic. A parser returns `{name: trace}` for
the clock lines and triggers it drives, and runviewer loads each device below
that name with the trace as `clock`:
- a device on a ClockLine gets the clock line's trace: one rising edge per
  tick, for every device on the line;
- a triggered pseudoclock device gets its Trigger's digital trace: one rising
  edge per trigger, the start and one after each wait;
- a PrawnDO on `clock_line` gets the clock line's trace, passed through its
  internal intermediate device's parser. It has edges besides its triggers:
  the trigger's falling change and any other device's ticks.

The shot file holds:
- `/waits`: each wait's label, script time and timeout, and the wait
  monitor's devices;
- `/data/waits`, once the shot has run with a wait monitor: each wait's
  measured duration and whether it timed out;
- every pseudoclock device's `is_master_pseudoclock` and `stop_time`; and
  `trigger_delay` and `wait_delay` from PrawnBlaster, PrawnDO and Cicero only;
- the connection table, which says what triggers each secondary.

labscript knows, and does not save: each pseudoclock's trigger times (its
start and each retrigger, as its trigger device rounds them), the initial
trigger time, `compiler.trigger_duration` and `compiler.wait_delay`.

## 3. The model

One function, `start_and_resume_times(clock, wait_times)`: the times a device
starts and resumes after each wait, on runviewer's time axis. It is pure, so it
can be tested without a shot file. A parser adds its `trigger_delay` (none for
a master) and draws its program from each. It keeps only its decoding.

The axis has to be the script's time, with waits of no length. Then the nth
retrigger is the first edge of `clock` at or after the nth wait time in
`/waits`, and that holds for a trigger's trace and for a clock line alike.
Masters stop adding `wait_delay`. A wait of measured length, from
`/data/waits`, would be a later change in this one place.

Where it lives and what it reads:

| Option | Reads | Repos | Size | Cases left |
| --- | --- | --- | --- | --- |
| A. A function in `labscript_devices/runviewer_parsing.py`, beside `rising_edge_times` | `clock`'s edges and the sorted wait times | labscript-devices; labscript-utils too for the shared reader below | about 20 lines; the six parsers lose their copies, net about −25 | 2: a master (no `clock`) and a secondary. Plus one tolerance, 1 ps, for the drawn ticks' float error |
| B. runviewer passes the wait times, or the trigger times, to `get_traces` | the new argument | runviewer, which is validated and has an owner, and labscript-devices | about 10 lines in runviewer and the parsers; parsers that do not take the argument need a fallback | A's 2, and the fallback. `/waits` is already in the file each parser opens, so B gives nothing A lacks |
| C. labscript saves each pseudoclock's trigger times, before it offsets them | the saved times; no edges | labscript and labscript-devices | about 4 lines in labscript and about 20 here | 2: saved times, or a fallback for older shot files that is A |

A has the fewest cases, and is the recommendation. C would read the trigger
times without edges or a tolerance, since labscript alone knows the exact
retrigger times; it is a later step, with A as its fallback.

The wait times come from `/waits`, which five places in three repos read
raw: blacs's progress bar and shot execution, PulseBlaster's worker,
NI_DAQmx's tab, and PrawnDO's parser. The librarian advises one reader,
`get_wait_times(h5_file)`, in `labscript_utils.shot_utils` beside
`get_shot_globals`, with lyse's readers of the measured waits beside it later.
That adds labscript-utils and about 10 lines. Without it, the parsers read
`/waits` themselves, one line each, and A touches labscript-devices alone.

What the drawn traces change, with A, which Ian should weigh first, as it is
visible in every shot with a wait:
- after each wait, every trace moves earlier by its master's `wait_delay`
  (40 ns on a PrawnBlaster, 2.5 µs on a PineBlaster or DummyPseudoclock, one
  clock period on a Cicero, 100 ns on a PulseBlaster), and lines up with its
  script time;
- a PrawnDO resumes on its retrigger, as intended;
- a PulseBlaster secondary starts at its trigger and resumes on each
  retrigger.

`0c89814` and `fd44105` stay as they are until Ian decides.
The librarian reviewed this note: no suite abstraction covers it, the model's
home is right, B would put pseudoclock wait semantics in runviewer, and C is
the right repo at a higher cost.
