# labscript-devices deep pass

A planning document for the code-health campaign in labscript-devices
(`issues/code_health_campaign.md` in the meta repo): the test contract, then the
deep pass's candidates for Ian's review, one section per step. It is deleted
when the pass is done. Nothing is removed until Ian has reviewed each entry.

## Commits

Each stage's commits on `CodeHealth`, for review:

- The contract, step 1, the end-of-shot wait and the decided items:
  `0895d6c..` the commit that records this line. Paired with labscript's
  `73af05d` (is_master_pseudoclock, stop_time and the pseudoclock stop order),
  which must merge with `4534238`.
- Codex's three findings on the first stage, the bounded abort waits Ian asked
  for before its re-check, and the re-check's finding: `4ff99a8..02b4a52`, and the
  commit that records this line.
  - **Outcome:** Codex's re-check found two points. Fixed in 02b4a52: an error
    from PrawnDO's abort after a timeout, such as a `SerialException`, is logged
    and the `TimeoutError` raised, where it used to replace it. Left as is (Ian):
    a board that confirms its abort or end of shot after the deadline counts as
    done, since the hardware did finish and each poll is bounded by the serial
    read timeout.
- Step 2.2's table and Ian's decisions, the two bugs fixed on his word
  (`719fe26`, `d0c300e`), and step 2.2.1's Phase A: `02b4a52..` the commit that
  records this line. Phase A alone is `93cdc48..` the same commit.
- Codex's findings on Phase A, and Ian's decisions on them: `4a74e3e..` the commit
  that records this line.
  - The ValueError for a device with no runviewer parser needs labscript-utils'
    lookup to treat a `None` registration as none, so it is left to that owner.
  - **Outcome:** each package gives its old module's own names, and the device
    classes it imported, as the same objects. Its labscript-side names make up
    `__all__`. The incidental imports are dropped, by Ian's decision. The names
    are listed under step 2.2.1.
  - The package check skips only AlazarTechBoard's missing library.
- Step 2.2.1's Phase B: `25c2f22..` the commit that records this line, coupled
  with labscript `2e47a79`, `608013c`, `f9d64b9`, `1d5ea89`, `58c5445` and `1988218`.
- Codex's findings on Phase B, its re-check's finding, and Ian's decision on
  that: `e0243fa..` the commit that records this line, coupled with labscript
  `0b14960`, `ab2ffae` and `bbcbad9`.
- The suite vocabulary (Ian): `d5eae95..` the commit that records this line.
  blacs did its own two items, `b68d188` and `27e20bb`; nothing here waits on
  them.
- The device differences (Ian), and the review's findings on them: `e791c8d..`
  the commit that records this line, coupled with labscript `6e5af94` and
  `fe63433` (`renamed_keyword` and its `stacklevel`) and `ac21df6` (its
  example and tests use the new names).
- Codex's findings on the device differences, and Ian's decision on the third:
  `b3a1880..` the commit that records this line.
- The legacy-file round: `12c9632..1bd2216`, coupled with labscript-utils
  `019113b` (`warn_legacy_file`).
- Codex's findings on it: `c005e01..` the commit that records this line, coupled
  with blacs `83fa555` (`front_panel_settings_file`).
- Step 2.3's table: the commit that records this line, a table only.
- Step 2.3's build (Ian: "go ahead with step 2.3"): `8c40fbf..` the commit
  that records this line.
- Codex's findings on step 2.3 (Ian: "yes send the fixes to
  labscript-devices"): `a407b55..ff741e4`.
- Ian's decisions on that round ("Fix the fragile name issue and do not have
  RFBlaster retry"): the commit that records this line.
  - **Outcome:** RFBlaster does not retry. A request that times out raises the
    Deadline's TimeoutError at once, and requests' other errors do too, since
    the request loop's retry catches none of them.
  - The PulseBlaster and NI_DAQmx parsers know a trigger by its connection and
    by the devices it clocks, not by the class name `Trigger`, so runviewer
    shows the devices under a Trigger subclass.
- Step 2.4's table: `2443b93`, a table only.
- Step 2.4's build (Ian: "approve as proposed; for the old NI paths, do not
  remove them, and instead add the depriciation warnings there too"):
  `36a7a77..` `5400b1d`.
- Step 2.5's table: `8028a2c`, a table only.
- Step 2.5's build (Ian: "What is lightcrafter unused view? I approve all else";
  then "delete the LightCrafter view and verify the PrawnDO bug now"):
  `cd4713f..` `30c7658`.
- PrawnDO's parser drift (Ian: "fix the PrawnDO parser drift now"): the commit
  that records this line. After each wait a secondary PrawnDO is drawn from its
  master's resume tick, so its traces in shots with waits move by the master's
  `wait_delay`, 40 ns a wait behind a PrawnBlaster; every other trace is
  unchanged.
  - Coupled with labscript `06820ed`, where `quantise_channel` rounds a phase
    before it wraps it. RFBlaster's phase (row 2 of step 2.5) and
    NovaTechDDS9M's rely on it.
- Step 2.6's build, the style pass (Ian: "go ahead with the remaining
  packages"; then "fix the two PrawnBlaster bugs before the final
  validation"): `83b11ce..` `c2d217d`.
- Codex's findings on step 2.6: `fd44105..` `828ab6c`.
- Runviewer's model of a triggered device (Ian: "agree with all three
  recommendations", "whichever is the cleanest should be accepted", "yes, drop
  the reader", then "yes, bring C forward now"): `1fea8d6..` the commit that
  records this line. Coupled with labscript `4d88c40..99b4f59`, which saves
  the trigger times the model reads, in time order. Codex's re-check at
  `6506f94` is clean, and step 2.6 is closed.
- The whole pass's open findings, steps 1 to 2.6, triaged for Ian, in place
  of step 2.6's triage: the commit that records this line, a table only.
- Its 35 simple rows (Ian: "have all of the simple no-brainers fixed and
  checked off"): `0e17cfe..` `a3ee208`.
- Codex's findings on them, its re-check's, Fable's review, and every NI task
  released (Ian): `75df455..` the commit that records this line.

## The test contract

Marks:

- **keep**: protects a real behaviour, and fails when that behaviour breaks.
- **rename**: keep, under a name that states the behaviour.
- **trim**: keep, but drop its assertions on message text (rule 13).
- **cut**: protects nothing on the list; the category is given.

"Step 2.1" marks a test that guards behaviour no one asked for; the entry of
the same number in step 1 below holds the evidence. Each duplicate cut was
checked by breaking the behaviour in a scratch copy of `HEAD` (0895d6c) and
running the suite: "M1" and so on name those runs.

- M1: `grab_multiple` ignores an abort. Failed: the two abort tests, and nothing else.
- M2: `Dummy_Camera.identifying_attributes` emptied. Failed: the three marker tests.
- M3: the image function loses its keyword arguments. Failed: eleven tests,
  "the frames of one absorption image agree" among them.

### Totals

- Test files: 4, plus `conftest.py`, which holds no tests.
- Tests: 41 at the start. Step 1 removed three with their behaviours (entries 2,
  4 and 7), and the contract, applied as Ian approved it, cut seven more: 31 remain.
- Marks, of the 38 left after step 1: keep 27, rename 1, trim 3, cut 7.

### The vendor-camera guard

The four `ContractTests` check how the vendor camera classes are written
(which methods each defines, what it inherits), not what they do, which rule
13 cuts. But they are the only check that runs on the vendor classes, whose
SDKs are absent here, so Ian kept the first as a guard: without it, a refactor
that dropped, say, `Pylon_Camera.snap` would pass the suite.

### tests/test_camera_interface.py

- `ContractTests.test_every_camera_writes_the_members_only_it_can`: each of the six cameras defines `set_attributes`, `snap`, `grab`, `configure_acquisition`, `stop_acquisition` and `close`. **keep**, as the guard above.
- `ContractTests.test_every_camera_in_the_tree_inherits_the_base`: each camera subclasses `TriggerableCameraInterface`. **cut** (structure).
- `ContractTests.test_every_camera_can_read_its_attributes_as_a_dict`: each camera defines `get_attributes_as_dict` or the two readers it composes from. **cut** (structure).
- `ContractTests.test_an_unwritten_member_names_the_camera_and_the_member`: an interface stub's error names the class and method. **cut** (message text). Step 2.1, entry 6.
- `GrabMultipleTests.test_a_clean_acquisition_collects_every_frame_in_order`: frames come back in grab order. **keep**.
- `GrabMultipleTests.test_a_camera_still_waiting_for_a_trigger_is_asked_again`: an error the camera calls transient is retried (IMAQdx, Pylon, FlyCapture2). **keep**.
- `GrabMultipleTests.test_a_camera_that_does_not_retry_lets_the_failure_out`: with nothing declared transient, the first error ends the acquisition (Spinnaker, Dummy). **keep**.
- `GrabMultipleTests.test_a_real_fault_ends_the_acquisition`: an error other than the declared transient one ends it. **keep**.
- `GrabMultipleTests.test_a_shot_told_not_to_fail_gives_up_the_frame_and_carries_on`: a skippable error with `exception_on_failed_shot=False` drops that frame (IMAQdx). **keep**.
- `GrabMultipleTests.test_a_shot_told_to_fail_fails_on_the_same_error`: the same error with `exception_on_failed_shot=True` ends it. **keep**.
- `GrabMultipleTests.test_an_abort_stops_between_frames_and_clears_the_flag`: an abort stops the acquisition and clears itself for the next shot. **keep**.

### tests/test_compile_device_tables.py

- `NI_DAQmxTests.test_a_shot_asking_a_daqmx_board_for_an_acquisition_compiles`: an NI_DAQmx shot with an analog input compiles under numpy 2. **keep**.
- `NI_DAQmxTests.test_the_acquisitions_table_stores_its_strings_as_bytes` (was `..._is_written_as_earlier_versions_wrote_it`): the acquisitions table's strings are fixed-length bytes, as readers expect. **rename** → `test_the_acquisitions_table_stores_its_strings_as_bytes`.

### tests/test_triggerable_camera_tab.py

- `CopyAttributesTests.test_copy_puts_the_attributes_on_the_clipboard`: the attributes dialog's Copy button copies its text. **keep**.

### tests/test_dummy_camera.py

- `AbsorptionImageTests.test_one_image_is_compiled_for_each_exposure`: one uint16 image per exposure, at the sensor's size. **keep**.
- `AbsorptionImageTests.test_the_images_are_stored_in_the_order_the_triggers_arrive`: images are stored in time order, not `expose()` order. **keep**.
- `AbsorptionImageTests.test_the_images_follow_a_global_the_function_uses`: a shot global changes the image. **keep**.
- `AbsorptionImageTests.test_the_frames_of_one_absorption_image_agree_with_each_other`: **cut** (duplicate): M3 failed it together with ten others, and its optical-density check repeats the lyse test's.
- `CoordinateGridTests.test_the_grid_is_the_object_plane_in_micrometres`: the grid is pixels scaled by `pixel_size/magnification`. **keep**.
- `DefaultImageTests.test_an_exposure_with_no_function_gets_a_blank_frame`: an exposure with no function stores zeros. **keep**.
- `RejectedFunctionTests.test_a_function_returning_a_nan_stops_the_compile` (was `..._says_so`): a non-finite image stops the compile. **trim**. Step 2.1, entry 1.
- `SensorSizeTests.test_a_camera_never_told_its_size_stops_before_the_shot_file_is_written` (was `..._says_so_before_it_compiles`): a camera without `Width` and `Height` stops before the shot file is written to. **trim**.
- `SavedImageTests.test_the_images_are_saved_where_a_real_camera_saves_them`: frames land in `images/<camera>/<name>/<frametype>`, uint16, with the save path's attributes. **keep**.
- `SavedImageTests.test_each_frame_is_saved_under_the_exposure_that_asked_for_it`: each saved frame is the compiled one for its exposure. **keep**.
- `SavedImageTests.test_the_saved_images_are_marked_as_not_real_data`: the saved group carries `NOT_REAL_DATA`. **keep**.
- `SavedImageTests.test_the_datasets_declare_themselves_to_be_images`: saved frames carry `CLASS=IMAGE`, as every camera's do. **keep**.
- `SavedImageTests.test_an_analysis_script_reads_them_as_it_reads_any_camera_s`: lyse's `get_images` reads them back. **keep**.
- `SaturationTests.test_a_pixel_saturates_at_the_depth_pixelformat_gives`: counts clip to the `PixelFormat` depth. **keep**. Step 2.1, entry 3.
- `WrongShapeTests.test_a_function_returning_the_wrong_shape_stops_the_compile` (was `..._says_which_exposure`): an image of the wrong shape stops the compile. **trim**. Step 2.1, entry 8.
- `UnsavedAttributeTests.test_the_marker_survives_a_camera_that_saves_no_attributes`: `NOT_REAL_DATA` is saved even when no attributes are. **keep**. Step 2.1, entry 5.
- `OldStyleCameraTests.test_a_camera_without_the_interface_still_runs_a_shot`: a lab's plain camera under an `IMAQdxCameraWorker` subclass still saves its images and attributes. **keep**.
- `PlaybackTests.test_the_camera_returns_the_compiled_frames_one_per_grab`: **keep**.
- `PlaybackTests.test_a_second_shot_starts_again_at_the_first_frame`: **keep**.
- `PlaybackTests.test_manual_mode_after_a_shot_does_not_grab_the_shot_again`: **keep**.
- `PlaybackTests.test_aborting_stops_the_acquisition`: **cut** (duplicate): M1 failed only it and the `GrabMultipleTests` abort test.
- `PlaybackTests.test_with_no_shot_loaded_it_returns_a_blank_frame`: Snap in manual mode returns zeros. **keep**.
- `PlaybackTests.test_a_camera_never_told_its_size_says_so`: **cut** (unreachable): a `DummyCamera` without `Width` and `Height` cannot compile its connection table, so no worker is ever started without them.
- `PlaybackTests.test_the_camera_declares_that_its_images_are_not_real_data`: **cut** (duplicate): M2 failed it with the two saved-marker tests.

## Step 1: behaviour no one asked for

What the fork changed: `git diff master CodeHealth` (two-dot) at 0895d6c, 58
commits and, in `labscript_devices/`, 57 files, +1799 −2335. Requests were read
from each commit, from this session's record of Ian's instructions, and from
the meta repo's `CODEX.md` and `issues/`. Users considered: labs' connection
tables and sequences, labs' own camera classes and workers, BLACS and lyse.

Not candidates, because Ian asked for them: the TriggerableCamera extraction and
its interface base class, DummyCamera (images from a function of the shot,
evaluated at compile time; µm grid; blank frame for no function or Snap;
`NOT_REAL_DATA` as a class attribute; uint16), the removal of `mock`, the
override guard and the old-style camera fallback, every mapping-round fix, and
the campaign edits. The numpy 2 and PyQt6 commits are compatibility.

Every candidate is inside DummyCamera or the camera base, chosen by an agent or
a review while building what Ian asked for.

| # | Behaviour | From | Reachable by a user? | Without it | Lines | Ian |
|---|---|---|---|---|---|---|
| 1 | A non-finite image stops the compile | b64d579 (review) | yes: a function can return NaN | NaN is cast to uint16, undefined, and stored as if read | ~6 | keep |
| 2 | A function passed where `trigger_duration` goes stops the compile | b64d579 (review) | yes: `expose(t, name, frametype, f)` | the compile still stops, with `TypeError: '>' not supported between instances of 'function' and 'int'` (checked) | ~8 | removed |
| 3 | Counts clip to the `PixelFormat` bit depth, not uint16's | a6df924 | yes, by setting `PixelFormat` | clip at 0..65535 | ~15 | keep |
| 4 | More grabs than compiled frames raises ValueError | a6df924 | no: one trigger per exposure, and the worker asks for that many | an IndexError, never reached | ~6 + test | removed |
| 5 | `NOT_REAL_DATA` is saved even with `saved_attribute_visibility_level=None` | b64d579 (review) | yes | the marker can be switched off | ~3 | keep |
| 6 | Each interface member is a stub raising NotImplementedError that names the class | 208afcf | when a lab writes a camera | an AttributeError naming the member | ~30 | keep |
| 7 | A worker with no `interface_class` raises NotImplementedError naming it | b64d579 (review) | when a lab writes a worker | TypeError: 'NoneType' object is not callable | ~5 + test | removed |
| 8 | An image of the wrong shape stops the compile, naming the exposure | a6df924 | yes | one wrong-shaped image compiles and is stored at the wrong size, silently (checked); several of differing shapes hit numpy's inhomogeneous-shape error | ~8 | keep |
| 9 | The coordinate grid is centred on the sensor | a6df924 | yes | the grid starts at 0 at a corner | ~2 | keep |
| 10 | The sensor size is checked when the camera is created, before the shot file is written | b64d579 (review) | yes | the shot file is left half-written | ~3 | keep |

## Step 2.2: duplication

Sources: `issues/seen_while_mapping.md` and the librarian's map, at `CodeHealth`
`2e8de3b`. Every class named below is public and keeps its name. A class
recorded in connection tables also keeps its class, since BLACS compares class
names, and a change would make every lab using the device recompile its
connection table once.

| # | Copies | Should it exist? | Where the one copy lives | Lines | Users each change touches | Ian |
|---|---|---|---|---|---|---|
| 1 | The "one clockline only" pseudoclock in Cicero, DummyPseudoclock, PineBlaster, RFBlaster and PrawnBlaster | Yes: these boards have one clock output | Done in `e806548`: labscript's `Pseudoclock.max_clock_lines`. Each subclass is now two lines, and it names the pseudoclock's class in connection tables | 0 | none | open: verify `e806548` |
| 2 | PrawnDO's pseudoclock and clockline still rewrite `add_device` to allow one child of one type | Yes | The same labscript checks: `max_clock_lines = 1`, and `allowed_children` on both. The clockline then limits its child's type but not the count; only PrawnDO itself creates that child | −14 | PrawnDO compiles; a misconnection error becomes labscript's own wording | agree |
| 3 | The wait-monitor dummy pseudoclock, clockline and intermediate device, in Cicero (34 lines) and PrawnBlaster (55) | Yes: labscript's `WaitMonitor` must hang from an intermediate device on a clockline, and these boards time their own waits | One set of three classes, about 15 lines, with `allowed_children` and `max_clock_lines` doing the checks. Cicero's and PrawnBlaster's six names stay as empty subclasses, so imports and connection tables are unchanged. Where: a labscript-devices module, since only these two devices use it (recommended); or labscript core beside `WaitMonitor`, as the librarian suggests, which needs labscript's owner | about −60 | Cicero and PrawnBlaster compiles with an internal wait monitor | open: question below |
| 4 | The rising-edge times of a parent clock, a six-line copy in seven runviewer parsers: Cicero, DummyPseudoclock, NI_DAQmx, NovaTechDDS9M, PineBlaster, PrawnBlaster, PrawnDO | Yes | One function, `(times, values) -> edge times`, about 8 lines, in a small new module `labscript_devices/runviewer_parsing.py` (librarian: runviewer has no such helper, and no parser imports runviewer); each parser calls it | about −35 | runviewer, for those seven devices | agree |
| 5 | DummyPseudoclock's `generate_code` (32 lines) and parser (45) copy PineBlaster's, pulse-program format included | Yes: labscript's tests and labs' test setups use the dummy | DummyPseudoclock's package, whose imports are light. `PineBlaster` and its `PineBlasterParser` subclass the dummy's classes, keeping their names, their own `__init__`, `max_instructions` and the parser's `trigger_delay`. Not the reverse: `PineBlaster.py` imports BLACS at module level, so the dummy would pull BLACS into every compile | about −75 | PineBlaster compiles and runviewer; no change to the dummy | open: step 2.2.1 |
| 6 | PulseBlaster_No_DDS's worker and tab copy PulseBlaster's: 7 worker methods (60 lines) and 6 tab methods (79) are identical | Yes | PulseBlaster's classes. `PulseblasterNoDDSWorker` and `Pulseblaster_No_DDS_Tab` subclass them and keep only what differs for a board without DDS: `init`, `program_manual`, `transition_to_buffered` and `initialise_GUI` | −139 | BLACS, for every DDS-free PulseBlaster: No_DDS, ESRPro200, ESRPro500, USB, SP2 | agree |
| 7 | Each PulseBlaster model's tab has a four-line `__init__` that only sets `device_worker_class` | Yes | A class attribute: `Pulseblaster_No_DDS_Tab.__init__` already uses one if set | −12 | the four model tabs | the most common pattern, everywhere |
| 8 | The PulseBlaster parsers. SP2's restates `num_dds = 0` and `num_flags = 24`, which `PulseBlaster_No_DDS_Parser` already sets | Yes | `PulseBlaster_No_DDS_Parser`; SP2's subclasses it, as USB's does | −2 | runviewer, SP2 | agree |
| 9 | ESRPro500 has no parser, so runviewer cannot show its shots (`get_runviewer_parser('PulseBlasterESRPro500')` raises ValueError; checked). A gap, not a copy; upstream has it too | Yes | A three-line `PulseblasterESRPro500Parser(PulseBlaster_No_DDS_Parser)`, with `num_flags = 21`, as ESRPro200's | +4 | runviewer, ESRPro500 | agree |
| 10 | Device groups made by hand (`hdf5_file['devices'].create_group(self.name)` and the like) in Cicero, PineBlaster, RFBlaster, PulseBlaster and PhaseMatrixQuickSyn | Yes | labscript's `Device.init_device_group`, which does exactly that | 0 (five one-line swaps) | those five devices' compiles; the shot file is unchanged | agree |

Ian's decisions, in his words: "1. Verify that work is done at a high level of
quality. 2. agree 3. why do old names stay as empty subclasses? 4. agree (but
see note below) 5. why does pineblaster import blacs. This is not a desired
dependency is it? Anyway the better question is 'why does pineblaster inherit
from dummy'. This point requres more discussion about the class structure
overall. We may defer this to a 2.2.1 since part of our goal here is to reshape
the class pattern to be most logical (like with our camera work). 6. agree. 7.
follow the standard most common in devices. We should adhere to a single
pattern globally. 8. agree. 9 agree 10. agree."

And overall: "We should attempting to build the most logical possible overall
class structure. Mostly as a tree, but sometimes with mixins as needed. Most
everything that does not support a specific type of hardware belongs in the
base classes provided by labscript core."

Approved, to build after Ian's review of the class structure: 2, 4, 6, 8, 9 and
10, and 7 in the pattern most common across devices, applied everywhere. Open:
1, 3, and 5, which moves to a step 2.2.1 on the class structure.

Answers to the two questions:

- 3: the empty subclasses keep two things. Cicero's three dummy classes are
  public names a lab's code could import. And every device's class is recorded
  in the connection table, which BLACS compares class by class, so a dummy that
  changed class would make each lab using Cicero or a PrawnBlaster with an
  internal wait monitor recompile its BLACS connection table once. PrawnBlaster's
  names are private. Without the subclasses, the cost is that one recompile.
- 5: `PineBlaster.py` was an old single-file device: its labscript class, BLACS
  tab and worker shared one module, which imported BLACS at module level, so
  compiling a PineBlaster shot imported BLACS. The package layout
  (`labscript_devices.py`, `blacs_tabs.py`, `blacs_workers.py`) keeps compiles
  free of BLACS; step 2.2.1's Phase A moves every single-file device to it.
 is upstream's name for the parser in each old
single-file device (Cicero, NovaTech, PineBlaster), and each is a different
parser. `TekScope` names both the instrument driver and the labscript device, in
two modules. The "return coerced values" TODO repeated in three
`program_manual`s goes to step 5.

Deferred (Ian): near-duplicates left for now, not rejected. Step 5 carries each
to the docs' "Possible improvements", so they outlive this file.

- DDS value quantisers (scale, add 0.5, cast): 10 lines across NovaTechDDS9M
  (frequency, phase, amplitude), PhaseMatrixQuickSyn (frequency) and RFBlaster
  (inline, with its trigger times), each with its own bounds and scale. A shared
  helper would save about 5 lines.
- Steps converted to hardware ticks, `round(step / clock_resolution)`: one line
  in each of five `generate_code`s (DummyPseudoclock, PineBlaster, Cicero,
  PrawnBlaster, PrawnDO). It is a unit conversion, not labscript's
  `quantise_to_pseudoclock`, which rounds times in seconds.
- Front-panel bit packing, about 20 lines: NI_DAQmx's worker packs and unpacks
  port values and its parser unpacks them, and PrawnDO's worker has
  `_dict_to_int` and `_int_to_dict`. `labscript.utils.bitfield` packs arrays per
  bit and does not cover packing one dict.
- Cicero's and PineBlaster's tab status monitors share six lines; Cicero's adds
  its own branches.
- Short camera methods, open on their merits. `TriggerableCameraInterface`
  could supply three defaults, saving about 15 lines:
  - `set_attributes` composed from `set_attribute`: IMAQdx's and Spinnaker's are
    that three-line loop.
  - `snap` as configure for one frame, `grab`, `stop_acquisition`:
    FlyCapture2's is exactly that, and Spinnaker's is, if its
    `stop_acquisition` can stand in for the bare `EndAcquisition` it calls.
  - Attributes held in a dict, for AndorSolis's and DummyCamera's two-line
    `set_attributes`, `set_attribute` and `get_attribute`.

  The vendor-camera guard test would change with them: `snap` leaves its list
  (a default `snap` needs only members the list already holds), and
  `set_attributes` becomes "`set_attributes` or `set_attribute`".

## Step 2.2.1: class structure

The plan is the class-structure page in the meta repo,
`issues/campaign_progress/class_structure.html` (`3379f7b`). Ian approved it:
"move forward with the work. I strongly suggest having each movement of a
single-file based device into a directory performed by seperate independent
subagents sequentally, perhaps as the first task. This is a big code change
that leads to no/little behavior change. So it is very easily testable."

Decided:

- Build cards 1, 2, 6, 7, 8, 9 and 10. Drop D1 and D2.
- Cards 3, 4 and 5, by Ian's rule that blacs keeps only the generic `Worker`
  and `DeviceTab`. `PseudoclockWorker` stays in labscript-devices, and
  `PseudoclockTab` joins it there. `GuilessTab` and `GuilessWorker` move to a
  shared labscript-devices module, and card 6's helper also lives in
  labscript-devices.
- Private class names go in the same round as the packages, so labs recompile
  their connection tables once.
- The approved step 2.2 items fold in: 2, 4, 6, 8, 9 and 10, and 7's single
  pattern.

Phase A comes first and alone: each single-file device becomes a package, one
Sonnet subagent per device, run one after another. Each conversion must show no
change in behaviour:

- identical shot files for its test shots, and for any connection table that
  uses the device, before and after;
- the same BLACS tab and runviewer parser looked up by class name;
- the labscript class imported with nothing from blacs in `sys.modules`;
- the suite passing.

There is one commit per device. Phase B, the class moves and core additions,
starts only after Codex reviews Phase A.

Phase A, as built: all 15 single-file devices are packages: DummyIntermediateDevice,
PineBlaster, RFBlaster, CiceroOpalKellyXEM3001, NovaTechDDS9M, PhaseMatrixQuickSyn,
LightCrafterDMD, AlazarTechBoard, PulseBlaster, PulseBlaster_No_DDS, the four
PulseBlaster models and test_device.

- **History:** each is two commits, a pure rename into the package, so that
  `git log --follow` tracks the file, then the split.
- **Old import paths:** each package's `__init__` imports its compile-side names
  for real. It re-exports the BLACS- and runviewer-side ones through
  `lazy_attributes`, new in `labscript_devices/__init__.py`.
- **The test:** `tests/test_device_packages.py` imports every device package as
  a compile does, and fails if one brings in BLACS. It skips, by name,
  AlazarTechBoard, whose compile loads the vendor's library.
- **Resource files:** QuickSyn's `.ui` moved into its package, and
  `pulseblaster.ui` into PulseBlaster's in Phase B. Cicero's worker still finds
  its firmware in `labscript_devices/`.
- **What was checked:** per device, identical shot files for its test shots and
  any workspace script using it, the RbChip lab's three sequences included.
  Also the same BLACS tab and runviewer parser by class name, and the same
  parser traces.
- **What changed:** the one difference anyone can see is `get_runviewer_parser`
  for a device with no parser. It raised ValueError and now raises
  AttributeError, from labscript-utils' handling of `runviewer_parser=None`.
  runviewer catches both.

### Phase B, as built

On `CodeHealth` after Phase A (`25c2f22`), in this order:

- **Card 9, device groups** (`5a32ccc`): five devices make their shot-file
  group with labscript's `init_device_group`.
- **Step 2.2 item 9** (`1681a27`): ESRPro500 gets a runviewer parser.
- **Card 4** (`5534444`, `3ca384e`): `pseudoclock_worker.py` becomes
  `pseudoclock.py`, and `PseudoclockTab` there holds the status monitor that
  Cicero's and PineBlaster's tabs shared.
- **Card 6** (`fd22d15`): `rising_edge_times`, in
  `labscript_devices/runviewer_parsing.py`, for seven parsers.
- **Card 7, with step 2.2 items 6, 7 and 8** (`cb4eac6`..`f6682a2`, `c406a1d`).
  PulseBlaster is a DDS mixin on a flags-only `PulseBlasterBase`, on all four
  sides. The tabs name their worker by `worker_class`, and a lab's tab that sets
  `device_worker_class` is still honoured.
- **Card 5** (`54d04dd`): `GuilessTab` and a generic `GuilessWorker` in
  `labscript_devices/guiless.py`. AlazarTechBoard's are now
  `AlazarTechBoardTab` and `AlazarTechBoardWorker`; its old names keep their old
  meaning.
- **Cards 2 and 1, device side** (`cd51918`, `313f78c`). The one-clockline
  pseudoclock subclasses and the wait-monitor dummies go, for labscript's
  `max_clock_lines` argument and `internal_wait_monitor_outputs`.
- **Step 2.2 item 2** (`10ca3ab`): PrawnDO's private pseudoclock and clockline
  classes go.
- **Card 9, ticks and DDS values** (`f6849e6`, `4134c99`). Steps become ticks
  with `quantise_to_pseudoclock(ticks=True)`; NovaTech, QuickSyn and RFBlaster
  quantise their DDS values with labscript's `quantise_channel`.
- **The reviews' fixes** (`f9c09d9`, `a1afd1f`, `b58f9ed`, `b291d89` and the
  commit that records this line).
- **Card 10** (`82c42cc`): `TriggerableCameraInterface` composes
  `set_attributes` and `snap`, and `DictAttributesMixin` holds dict attributes.
  Card 10 and its fixes stay on `CodeHealth`: upstream PR #148's `DummyCamera`
  branch takes only true bug fixes in the PR's own camera code (Ian).

Merge coupling: this range must merge with labscript `2e47a79`, `608013c`,
`f9d64b9`, `1d5ea89`, `58c5445`, `1988218`, `0b14960`, `ab2ffae` and `bbcbad9`.

Intended differences:

- **Connection tables:** the internal pseudoclock, clockline and wait-monitor
  devices of Cicero, PineBlaster, RFBlaster, DummyPseudoclock, PrawnBlaster and
  PrawnDO have new classes, so labs recompile their connection table once.
- **Removed names:** the classes those devices dropped can no longer be imported.
  No script in the workspace imports them.
- **isinstance:** PulseBlaster_No_DDS and its models are no longer
  subclasses of PulseBlaster.
- **runviewer:** it shows ESRPro500 shots.
- **PineBlaster's tab monitor:** it stops after an abort, and a worker failure
  aborts the shot, as Cicero's did.
- **DDS errors:** an out-of-range value raises labscript's error, which names
  the value and the limits.
- **RFBlaster:** a value negative after scaling rounds to nearest, not towards
  zero.
- **BLACS:** finds `AlazarTechBoardTab` for an AlazarTechBoard.
- **PulseBlaster code:**
  - `convert_to_pb_inst` takes only the digital outputs, so a lab subclass that
    calls it with five arguments fails.
  - The DDS board's tab, like the others, now honours a `device_worker_class` a
    lab's tab sets.
- **Parsers:** No_DDS's and SP2's parsers are no longer subclasses of
  `PulseBlasterParser`.
- **Error wording:** misconnections to the internal wait-monitor chain (Cicero,
  PrawnBlaster) and to PrawnDO's internals raise labscript's own messages.
- **Cameras:** every camera's `set_attributes` names its dict `attributes`, as
  the interface does (Ian), so a call by the old `attr_dict=` or
  `attributes_dict=` keyword fails. Nothing in the workspace calls it by keyword.

Kept for labs' own subclasses, after the review:
- **DDS quantisers:** NovaTech's and QuickSyn's `quantise_*` methods are still
  the hooks `generate_code` calls, now made with `quantise_channel`. Each
  quantises the data it is given, so a subclass can transform it first.
- **DDS worker:** it takes 12 flags when a tab doesn't pass `num_DO`.

Card 9's bit packing is left, by Ian's decision. Every other shot compiles to an
identical file.

### The names each package gives (Ian)

Each package gives the names its old single-file module defined, and the
device classes it imported from another device package, such as
`PulseBlaster_No_DDS`'s `PulseBlaster`. The labscript-side ones are imported for
real and make up `__all__`, so a star import never loads BLACS; the rest load
when asked for by name. The names an old module only imported from elsewhere
are dropped (Ian: "agree with decisions 1 and 2"). That covers labscript,
labscript_utils, numpy, h5py, PIL, tqdm, the standard library, BLACS, Qt and
qtutils, and labscript_devices' helpers. The package docs pages pass
`:ignore-module-all:`, so the classes are documented once, under
`.labscript_devices`.


Phase B then dropped the internal pseudoclock and wait-monitor classes, which no
script imports, and added the PulseBlaster bases and mixins, AlazarTechBoard's
tab and worker, and ESRPro500's parser; the lists below are as they stand.

- `AlazarTechBoard`: `__all__` AlazarTechBoard; by name AlazarTechBoardTab, GuilessTab, tqdm_kwargs, atsRanges, atsSampleRates, atsExternalClockAdvice, find_nearest_internal_clock, find_clock_and_r, ats9462_clock, AlazarTechBoardWorker, GuilessWorker (new: AlazarTechBoardTab, AlazarTechBoardWorker); dropped ctypes, np, signal, sys, time, tqdm, ats, Device, AnalogIn, compiler, LabscriptError, set_passed_properties, labscript_utils, h5py, BLACS_tab, Worker, define_state, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab, os, copy.
- `CiceroOpalKellyXEM3001`: `__all__` CiceroOpalKellyXEM3001; by name CiceroOpalKellyXEM3001Tab, int_to_bytes, bits_to_int, add_instruction_to_bytearray, CiceroOpalKellyXEM3001Worker, CiceroOpalKellyXEM3001Parser; dropped Device, PseudoclockDevice, Pseudoclock, ClockLine, LabscriptError, set_passed_properties, compiler, IntermediateDevice, WaitMonitor, DigitalOut, runviewer_parser, BLACS_tab, BLACS_worker, labscript_device, np, labscript_utils, h5py, ensure_str, CiceroOpalKellyXEM3001Pseudoclock, CiceroOpalKellyXEM3001DummyPseudoclock, CiceroOpalKellyXEM3001DummyClockLine, CiceroOpalKellyXEM3001DummyIntermediateDevice, define_state, Tab, PseudoclockWorker, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab.
- `DummyIntermediateDevice`: `__all__` DummyIntermediateDevice; by name DummyIntermediateDeviceTab, DummyIntermediateDeviceWorker; dropped labscript_device, BLACS_tab, BLACS_worker, IntermediateDevice, DigitalOut, AnalogOut, compiler, np, DeviceTab, Worker.
- `LightCrafterDMD`: `__all__` arr_to_bmp, WIDTH, HEIGHT, BLANK_BMP, ImageSet, LightCrafterDMD; by name LightCrafterDMDTab, LightCrafterDMDWorker; dropped base64, os, struct, time, PIL, BytesIO, labscript_utils, h5py, labscript_device, BLACS_tab, BLACS_worker, runviewer_parser, Device, IntermediateDevice, LabscriptError, Output, compiler, np, Worker, define_state, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab, Signal.
- `NovaTechDDS9M`: `__all__` bauds, NovaTechDDS9M; by name NovaTechDDS9MTab, NovaTechDDS9MWorker, NovaTechDDS9MParser; dropped runviewer_parser, BLACS_tab, IntermediateDevice, DDS, StaticDDS, Device, compiler, LabscriptError, set_passed_properties, NovaTechDDS9mFreqConversion, NovaTechDDS9mAmpConversion, np, labscript_utils, h5py, time, Worker, define_state, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab.
- `PhaseMatrixQuickSyn`: `__all__` QuickSynDDS, PhaseMatrixQuickSyn; by name PhaseMatrixQuickSynTab, PhaseMatrixQuickSynWorker; dropped np, BLACS_tab, runviewer_parser, Device, StaticDDS, StaticAnalogQuantity, StaticDigitalOut, compiler, LabscriptError, set_passed_properties, labscript_utils, Worker, define_state, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab, UiLoader, os.
- `PineBlaster`: `__all__` PineBlaster; by name PineBlasterTab, PineBlasterWorker, PineBlasterParser; dropped PseudoclockDevice, Pseudoclock, ClockLine, compiler, LabscriptError, set_passed_properties, runviewer_parser, BLACS_tab, np, labscript_utils, h5py, PineBlasterPseudoclock, define_state, PseudoclockWorker, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab.
- `PulseBlaster`: `__all__` PulseBlasterDDS, PulseBlasterBase, DDSPulseBlasterMixin, PulseBlaster, PulseBlasterDirectOutputs; by name PulseBlasterBaseTab, DDSPulseBlasterTabMixin, PulseBlasterTab, PulseBlasterBaseWorker, DDSPulseBlasterWorkerMixin, PulseBlasterWorker, profiles, profile, start_profile, stop_profile, PulseBlasterBaseParser, PulseBlasterParser (new: PulseBlasterBase, DDSPulseBlasterMixin, PulseBlasterBaseTab, DDSPulseBlasterTabMixin, PulseBlasterBaseWorker, DDSPulseBlasterWorkerMixin, PulseBlasterBaseParser); dropped BLACS_tab, runviewer_parser, dedent, Device, PseudoclockDevice, Pseudoclock, ClockLine, IntermediateDevice, DigitalQuantity, DigitalOut, DDS, DDSQuantity, LabscriptError, set_passed_properties, compiler, np, labscript_utils, h5py, time, define_state, PseudoclockWorker, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab, UiLoader, qtutils, os, QtCore, QtGui.
- `PulseBlaster_No_DDS`: `__all__` PulseBlaster, PulseBlaster_No_DDS; by name PulseBlaster_No_DDSTab, PulseBlaster_No_DDSWorker, PulseBlaster_No_DDSParser, PulseBlasterParser; dropped BLACS_tab, runviewer_parser, PseudoclockDevice, compiler, LabscriptError, np, define_state, PseudoclockWorker, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab, UiLoader, qtutils, os, QtCore, QtGui, QtWidgets.
- `PulseBlasterESRPro200`: `__all__` PulseBlaster_No_DDS, PulseBlasterESRPro200; by name PulseBlaster_No_DDSTab, PulseBlasterESRPro200Tab, PulseBlaster_No_DDSWorker, PulseBlasterESRPro200Worker, PulseBlaster_No_DDSParser, PulseBlasterESRPro200Parser; dropped BLACS_tab, runviewer_parser.
- `PulseBlasterESRPro500`: `__all__` PulseBlaster_No_DDS, PulseBlasterESRPro500; by name PulseBlaster_No_DDSTab, PulseBlasterESRPro500Tab, PulseBlaster_No_DDSWorker, PulseBlasterESRPro500Worker, PulseBlasterESRPro500Parser (new: PulseBlasterESRPro500Parser); dropped BLACS_tab, runviewer_parser.
- `PulseBlasterUSB`: `__all__` PulseBlaster_No_DDS, PulseBlasterUSB; by name PulseBlaster_No_DDSTab, PulseBlasterUSBTab, PulseBlaster_No_DDSWorker, PulseBlasterUSBWorker, PulseBlaster_No_DDSParser, PulseBlasterUSBParser; dropped BLACS_tab, runviewer_parser.
- `PulseBlaster_SP2_24_100_32k`: `__all__` PulseBlaster_No_DDS, PulseBlaster_SP2_24_100_32k; by name PulseBlaster_No_DDSTab, PulseBlaster_SP2_24_100_32kTab, PulseBlaster_No_DDSWorker, PulseBlaster_SP2_24_100_32kWorker, PulseBlaster_SP2_24_100_32kParser, PulseBlasterParser; dropped BLACS_tab, runviewer_parser.
- `RFBlaster`: `__all__` RFBlaster, RFBlasterDirectOutputs; by name RFBlasterTab, MultiPartForm, RFBlasterWorker; dropped os, PseudoclockDevice, Pseudoclock, ClockLine, IntermediateDevice, DDS, compiler, startupinfo, LabscriptError, set_passed_properties, np, BLACS_tab, runviewer_parser, setup_logging, RFBlasterPseudoclock, define_state, PseudoclockWorker, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab.
- `test_device`: `__all__` test_device; by name test_deviceTab, test_deviceWorker, test_deviceParser; dropped BLACS_tab, runviewer_parser, Device, LabscriptError, set_passed_properties.

## The suite vocabulary (Ian)

Ian approved the ten rules of the librarian's survey (meta
`issues/suite_vocabulary_survey.md`, `50428a2`); they are labscript-style's
`IDIOMS.md` §5. On `CodeHealth`:

- **attributes** (`d5eae95`, `b36d00d`): every camera's
  `set_attributes(self, attributes)`, and FlyCapture2's `set_attribute(name, value)`.
- **properties** (`a4a775b`, `75367b4`): each worker reads its shot-file
  properties as `device_properties` (AlazarTechBoard's `atsparam`, TekScope's
  `scope_params`, the dummy's `props`, TriggerableCamera's `properties`), and
  `labscript_utils.properties`' helpers are called by module.
- **Docs** (`7fb8c18`): `camera_attributes` and `manual_mode_camera_attributes`
  in the FlyCapture2, Pylon and Spinnaker examples.
- **Worker methods** (`650eae5`, `1df437e`, `3c502ff`): blacs' parameter names
  on all 21 `transition_to_buffered` and 20 `program_manual`. `shot_finished` is
  the end-of-shot query: Cicero's and PineBlaster's `status_monitor` and the
  dummy's `check_if_done` go. The dummy's abort clears its shot without the
  transition, which now waits for the dummy's own `shot_finished`, so an abort
  still does not wait. It gains `abort_transition_to_buffered`, and TekScope
  gains `shutdown`.
- **Class names** (`e724bd8`, `b36d00d`): 32 tabs, workers and parsers. The
  role is glued onto every device's name, underscores or not: `NI_DAQmxTab`,
  `PulseBlaster_No_DDSTab`, `test_deviceTab`.
- **GUI save data** (`f074ad5`): `restore_save_data(data)`. The two-key dicts
  are blacs': one key each in `27e20bb`, and its demo worker's names in
  `b68d188`.

Choices made within the rules:
- NI_DAQmx's output worker is its `NI_DAQmxWorker`; the acquisition and
  wait-monitor workers keep their role in the name.
- `check_status` stays: in PulseBlaster, PrawnBlaster, PrawnDO and QuickSyn it
  returns the device's status for the front panel, not whether the shot is
  over, and it has one name already.

What breaks: a lab's code that imports an old tab, worker or parser name, or
names an old worker in a `device_worker_class` string; and a
`set_attributes(attr_dict=...)` call. Nothing in the workspace does.

Checks: every test shot and the RbChip sequences compile identical to
`d5eae95`; BLACS and runviewer find every registered device's tab and parser
as before; every dotted class path resolves and every worker method a tab
queues exists; the PulseBlaster workers drive the fake spinapi identically;
labscript-devices, blacs and labscript suites pass.

### Other differences, for Ian (not built)

| Concept | Variants | Proposed | Public | Size |
| --- | --- | --- | --- | --- |
| Serial or instrument address kwarg | `com_port` ×5; `usbport` PineBlaster; `addr` TekScope; `ip_address` RFBlaster; `server`, `port` LightCrafterDMD; `server` AlazarTechBoard | `com_port` for serial ports; one name for network hosts | yes, kwargs and saved properties | ~6 devices |
| Board identity kwarg | `board_number` PulseBlaster; `serial_number` cameras; `serial` Cicero; `MAX_name` NI_DAQmx | `serial_number` where it is a serial number | yes | ~3 |
| Core clock frequency | `clock_frequency` in Hz, Cicero, PrawnBlaster, PrawnDO; `core_clock_freq` in MHz, a PulseBlaster class attribute | `clock_frequency` in Hz | partly | ~6 |
| `use_wait_monitor` default | False on Cicero, True on PrawnBlaster | one default | yes, behaviour | 2 |
| Core `Device` keywords | 9 labscript classes take no `**kwargs`, so no `gui`, `worker`, `start_order` | take and pass `**kwargs` | additive | 9 |
| Tab's end-of-shot polling | `status_monitor` with three signatures; PulseBlaster's and PrawnBlaster's tabs reimplement `start_run` and `status_monitor`, and PulseBlaster's tab repeats its worker's `shot_finished` test | inherit `PseudoclockTab` | no | ~3 tabs |
| Abort | `transition_to_manual(abort=False)` ×6 against an `abort()` helper ×9 | one `abort()` | no | ~6 |
| Where a tab creates its worker | `initialise_GUI` ×8, `initialise_workers` ×12 | `initialise_workers` (rule 10) | no | 8 |
| Parsers' shot-file read-backs | `device_props`, `props`, `conn_props` in PrawnBlaster, PrawnDO and NI_DAQmx parsers | `device_properties`, `connection_table_properties` | no | 3 |
| The shot file kept for `transition_to_manual` | `self.h5file` ×4, `self.h5_filepath` TriggerableCamera | `self.h5_file` | no | ~6 |
| Camera interface classes | `<Vendor>_Camera` ×5, `AndorCamera`; drivers inside `blacs_workers.py` | `<Device>Camera` | no | 6 |
| Camera `set_attribute` | Spinnaker's takes a third argument, `stream_map=False` | `(name, value)` | no | 1 |
| Camera interface keywords | `bufferCount`, `waitForNextBuffer` camelCase; `grab` and `configure_acquisition` defaults differ | snake_case, one default | no | 6 cameras |
| `register_classes` call | three forms; PrawnDO's `BLACS_tab=''` where the registry expects `None` | one form, `None` | no | 31 files |
| Package `__init__` | `lazy_attributes` ×15, `deprecated_import_alias` ×2 (DummyPseudoclock, PrawnBlaster), header only ×5, empty ×7 | `lazy_attributes` everywhere | the empty ones export nothing | ~14 |
| DDS channel names and units | connection `'channel n'` NovaTech, `'dds n'` others; amplitude `'Arb'`, `'Vpp'`, `'%'` | one prefix and unit | yes, connection strings | 4 devices |
| Pulse-program datasets | `PULSE_PROGRAM` ×5 against `pulse_program` PrawnDO; column names differ per board | one case | shot-file format | 2 |
| `test_device` | a lower-case labscript class | CamelCase | test-only, but stored in connection tables | 1 |
| NI_DAQmx `self.AI_timebease_rate` | a misspelt, unused attribute (labscript_devices.py:267) | remove | no | 1 line |

## The device differences (Ian)

Ian decided the 19 differences (meta
`issues/campaign_progress/device_differences.html`): the public ones change,
leaving the old forms working with a `FutureWarning`, which points at the
script's line, and a `# LEGACY … WILL BE REMOVED` comment; the internal ones
change outright.

Public:
1. A serial port is `com_port` and a network host `host` (`c994b7a`):
   PineBlaster's `usbport`, RFBlaster's `ip_address` and LightCrafterDMD's
   `server`. AlazarTechBoard's `server`, a PCI board's BLACS name, and
   TekScope's `addr`, a VISA address, are neither and stay.
2. Cicero's `serial` is `serial_number` (`4331d7a`).
3. PulseBlaster's `core_clock_freq`, in MHz, is `clock_frequency`, in Hz
   (`dfff799`); a lab's subclass that sets `core_clock_freq` still works.
4. Cicero's `use_wait_monitor` defaults to True, and only a master pseudoclock
   makes one, as on the PrawnBlaster (`5f042ef`). A default cannot be
   deprecated: a script that made its own WaitMonitor on a Cicero master now
   fails with "Cannot instantiate a second WaitMonitor", and needs
   `use_wait_monitor=False`.
5. AlazarTechBoard, Cicero, PineBlaster, RFBlaster, PrawnBlaster,
   LightCrafterDMD and its ImageSet, PhaseMatrixQuickSyn and QuickSynDDS take
   the core `Device` keywords and pass them on (`04539ff`).
6. Every DDS connects as `'dds n'`, and every amplitude is `'Arb'`, 0 to 1, the
   unit labscript-utils' NovaTech and AOM conversions use (`20140dc`,
   `e167a83`, `ba1282a`). NovaTech's `'channel n'` still connects, and its tab
   renames the outputs of a front panel saved under the old names. RFBlaster's
   worker converts to the board's %, and its tab converts a front panel saved in
   %, converting only the fields saved (`98956f4`); both tabs do so at
   startup and when a front panel is loaded (`e167a83`). A PulseBlaster
   amplitude calibration written for `'Vpp'`, the old name of the same 0 to 1,
   still loads, with a FutureWarning at compile, at the script's line
   (`cc627dd`), and in BLACS (`ba1282a`). An RFBlaster calibration
   written for `'%'` is refused by BLACS, which logs why; none is in the
   workspace.
7. PrawnDO's dataset is `PULSE_PROGRAM`, as on the other pseudoclocks
   (`01a5da5`); its worker and parser still read `pulse_program`, warning once
   for each such file that it may not be readable in future (`4eca405`,
   `510428c`, `1bd2216`, Ian), through labscript-utils' `warn_legacy_file`.
   Every other read of a legacy file warns the same way (`ab52f2f`, `10a1596`,
   `f742f10`, `f580eb5`): NovaTech's `'channel n'` connections; a connection
   table without NovaTech's or PulseBlaster's newer properties, or with
   NovaTech's phase_mode `'default'`; NI_DAQmx's old model specification; a
   `'Vpp'` calibration; the test device's old class name; and a front panel
   with NovaTech's old names or RFBlaster's `%`.
8. The test device's class is `TestDevice`; `test_device` still works
   (`7d278ce`). Its package keeps its name.

Internal:
9. PulseBlaster's and PrawnBlaster's tabs inherit `PseudoclockTab`'s
   `start_run` and `status_monitor`, which ask the worker `shot_finished`, and
   they and QuickSyn's refresh their widgets in `update_status` (`f37de4f`,
   `0a5e705`). PulseBlaster's
   reprogramming after a STOP shot is its `shot_over`. PrawnBlaster's
   `shot_finished` takes its tab's test, reading each wait as it ends; a
   run-status of 5 during a shot now raises, where the tab ended the shot.
10. Every worker aborts through `abort()`, which `abort_buffered` and
    `abort_transition_to_buffered` call; where its transition and abort share
    their work, both call `_return_to_manual(abort)` (`ecc96af`, `7185596`).
    PulseBlaster's and FunctionRunner's transition aborts still do less, as
    before: neither stops the board nor runs the stop functions.
11. Every tab creates its workers in `initialise_workers` (`5adaed5`). Cicero's
    tab reflashes its FPGA once its worker exists.
12. Parsers read back `device_properties` and `connection_table_properties`
    (`d597d1d`).
13. Workers keep the shot's file as `self.h5_file` (`7a0d8bf`).
14. The camera interfaces are `<Device>Interface`, as their base
    `TriggerableCameraInterface` is (`477de21`): `<Device>Camera` would name
    DummyCamera's interface `DummyCamera`, its labscript class.
15. Spinnaker's `get_attribute(name)` and `set_attribute(name, value)`; its
    stream node map has `set_stream_attribute` (`8f9389f`).
16. Every camera's `configure_acquisition(continuous=True, buffer_count=None)`,
    `None` leaving each its own number of buffers, and `grab()` (`330ee3d`). The
    worker passes the count positionally, so a camera on IMAQdxCameraWorker's
    deprecated route, written with upstream's `bufferCount`, still works
    (`c37313b`).
17. Every `register_classes.py` in the documented form; PrawnDO's intermediate
    device has `BLACS_tab=None` (`cfda0bc`).
18. Every package has the `lazy_attributes` `__init__` (`ac54e75`); NI_DAQmx's
    also exports its models.
19. NI_DAQmx's misspelt, unused `self.AI_timebease_rate` goes (`ec8e054`).

Intended differences in shot files, against `e791c8d`: NovaTech's DDSs connect
as `'dds n'` (the RbChip sequences' 8 NovaTech DDSs too, their only
difference); PineBlaster saves `com_port`; PrawnDO writes `PULSE_PROGRAM`; a
Cicero master gets its wait monitor; the test device's error names
`TestDevice`. Labs recompile their connection table once.

Checks: every other test shot compiles identical, and every old public form
compiles with its `FutureWarning`; BLACS and runviewer find every device, and
`TestDevice`; old and new shot files give the same runviewer traces; the
PulseBlaster, NovaTech, RFBlaster, QuickSyn, Spinnaker and PrawnDO workers do
the same on fake hardware; labscript-devices, blacs and labscript suites pass.

Seen, not changed:
- PulseBlaster's and FunctionRunner's transition aborts, above: whether they
  should stop the board and run the stop functions is Ian's call.
- labscript's example puts labscript-utils' `example3`, based on `'Vpp'`, on a
  PulseBlaster DDS amplitude, so its compile and BLACS now warn; labscript-utils
  has no `'Arb'`-based example to use instead.
- PulseBlaster's parsers take `get_traces(add_trace, parent=None)`, where
  §5 names it `clock`; runviewer passes it positionally.
- TekScope's driver module `TekScope.py` shadows the package's `TekScope`
  class in a process that has imported it.
- The test device's `DoSomething` keyword is CamelCase.

## Step 2.3: root causes

Sources: `KNOWN_ISSUES.md`, the "seen, not changed" lists above, and the 25
guards added since the fork, each traced to its cause. Ranked by Ian's rule,
"can a reasonable sequence in his labs reach this?": his labs run PulseBlaster
masters, NovaTech DDSs and NI cards (and spielman-devices' Arduinos, not this
repo's). Ian decided rows 5, 6, 17's second part and 19, as marked ("agree with
your views on 5, 6, 17b and 19"), and confirmed the groups ("agree with fix now,
verify first and defer groups. But remember we are only planning"): fix now 1,
2, 4, 7, 8, 10, 11, 12, 14, 15, 16 and 17's first part; verify first 3 and 9;
defer 13, 18, 20 and 21. "Built" below says how each went.

| Rank | Device, file:line | What goes wrong | Who reaches it | Cause | Fix at the cause, size | Now or defer |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | PulseBlaster `runviewer_parsers.py:206` | runviewer raises KeyError on any shot with a PulseBlasterDDS | any PulseBlaster lab using a PulseBlasterDDS | children are matched by the class name `'DDS'` | match a DDS by its sub-channels, 1 line | now |
| 2 | PulseBlaster `runviewer_parsers.py:169` | runviewer's time axis falls short after any instruction longer than about 43 s | a PulseBlaster sequence with a long hold or load | a LONG_DELAY's repeat count (`inst_data`) is ignored, as if a CONTINUE | multiply its length by the count, 2 lines; and name the argument `clock`, per §5 | now |
| 3 | PulseBlaster `labscript_devices.py:455` | a looped step may run one core cycle short each time, about 39 µs over a 2,905-step ramp | every PulseBlaster ramp, if SpinAPI truncates | delays reach SpinAPI as float ns, about 9% just under a whole cycle | pass a delay SpinAPI turns into the intended whole cycle, about 3 lines | verify first: SpinAPI's source, or time a long looped ramp |
| 4 | NI_DAQmx `blacs_workers.py:788, 863` | a lost start pulse hangs the transition to manual, and BLACS with it | an NI lab with waits, on a miswired or failed shot | the wait monitor reads edges with no timeout, and is joined with none | bound the read by the shot's length and the join, raising, about 8 lines | now, then hardware validation on Development |
| 5 | FunctionRunner `blacs_workers.py:111` | a transition aborted after its start functions ran never runs the stop functions | a FunctionRunner lab whose other device fails its transition | `abort_transition_to_buffered` returns True, though the transition already ran code | call `abort()`, 1 line | Ian: it runs the stop functions after a failed transition |
| 6 | PulseBlaster `blacs_workers.py:267` | a transition abort leaves the board programmed, and a secondary on BRANCH armed, until BLACS reprograms it | any PulseBlaster lab whose other device fails its transition | the transition abort is a stub; blacs' `program_device` afterwards covers it | none | Ian: left as it is, with a one-line comment that blacs reprograms the device afterwards |
| 7 | `docs/source/devices/pulseblaster_no_dds.rst:61-64` | the example makes a PulseBlaster with DDS and calls `Clockline`, which does not exist | anyone copying the docs for a no-DDS board | a stale example | `PulseBlaster_No_DDS`, `ClockLine`, 3 lines | now |
| 8 | PrawnBlaster `blacs_workers.py:469` | a board stuck at run status 1 hangs `transition_to_buffered` | PrawnBlaster secondaries (not in Ian's labs) | the trigger poll has no deadline | `wait_for_end_of_shot` with its own test, 3 lines | now |
| 9 | PrawnBlaster, PrawnDO `abort`, `blacs_workers.py:551, 376` | an abort of a board that never ran may fail after `end_of_shot_timeout` | Prawn users who abort a transition | only run status 5 counts as aborted; whether firmware leaves 0 is unknown | accept 0 too, 1 line each | verify first, from the firmware |
| 10 | PrawnDO `labscript_devices.py:252` | `repeat_pulse_sequence` on a PrawnDO output does not compile | PrawnDO users | `output.timeseries` holds function instructions | read `output.raw_output`, 1 line | now |
| 11 | LightCrafterDMD `blacs_workers.py:101` | a DMD that stays busy hangs every transition and abort | DMD users | "System Busy" is retried every 5 s with no limit | a deadline, raising, 3 lines | now |
| 12 | RFBlaster `blacs_workers.py:143, 145` | an RFBlaster that stops answering hangs its worker | RFBlaster users | `requests` calls have no timeout | `timeout=`, 2 lines | now |
| 13 | RFBlaster `pseudoclock.py:33` (guard) | the transition does not wait for a secondary RFBlaster to end | RFBlaster secondaries | the board has no status readback, so `shot_finished` is the default True | unknown without the board's protocol | defer: hardware |
| 14 | AlazarTechBoard `labscript_devices.py:102`; `blacs_workers.py:303, 314, 420` | two acquisitions do not compile; an acquisition error raises a TypeError; an unknown input range is used unbound | AlazarTech users | `init_device_group` inside the loop; `sys.exc_info()` kept and raised; a print in place of a raise | move it out, re-raise the exception, raise on the range, about 6 lines | now |
| 15 | LightCrafterDMD `labscript_devices.py`, `blacs_workers.py` | no ImageSet gives IndexError; short BM bytes give struct.error; no IMAGE_TABLE leaves a name unbound | DMD users | no empty or short-input checks | LabscriptError for each, about 8 lines | now |
| 16 | PhaseMatrixQuickSyn `labscript_devices.py:65-75` | no DDS gives UnboundLocalError; with two, only the last is used | QuickSyn users | the loop keeps the last output | raise unless exactly one, 3 lines | now |
| 17 | Cicero `labscript_devices.py:62, 74` (guard) | a negative debounce compiles; a wait monitor asked of a secondary is dropped silently | Cicero users (not in Ian's labs) | only the upper bound is checked; `use_wait_monitor and is_master_pseudoclock` | check 0 too; default `None` meaning "if master", raising for an explicit True on a secondary, about 5 lines | now; for the second, Ian: a secondary's wait monitor raises a clear LabscriptError, not dropped |
| 18 | PulseBlaster `labscript_devices.py:482` (guard) | a DDS on a no-DDS board is refused at compile, not at connection | a misconnected PulseBlaster script | every board's direct outputs allow DDS children | per-board `allowed_children`, about 5 lines | defer: it is already an error |
| 19 | DummyCamera `labscript_devices.py:71` (guard) | a failed `generate_code` leaves a shot file that cannot be compiled again | any device's failed compile | labscript writes the shot file in place | labscript's: compile to a temporary file, then move it | Ian: labscript's owner |
| 20 | TekScope `TekScope.py` | the driver module shadows the package's `TekScope` once a worker imports it | a process that imports both | the module has the class's name | rename the module, about 3 lines | defer: no caller hits it |
| 21 | test_device `labscript_devices.py` | its `DoSomething` keyword is CamelCase | none | upstream's test fixture | `do_something`, with a legacy keyword, about 4 lines | defer |
| 22 | PhaseMatrixQuickSyn worker; FlyCapture2 Format7 | QuickSyn's buttons and gate; Format7 skipped silently | their users | upstream | as `KNOWN_ISSUES.md` says | left, by Ian's decision |

The other 21 guards are designed behaviour (deadlines, the camera contract,
legacy paths, DummyCamera's checks), whose causes need no fix.

### Built

- One commit per row, each with a probe that fails before it, and one per
  review finding (rows 4, 5 and 10 each needed a second).
- Row 3: Linux's `libspinapi64.so` (spinapi 3.2.2) rounds to the nearest cycle,
  so nothing changed. The labs' Windows `spinapi64.dll` is unchecked;
  `KNOWN_ISSUES.md` says what settles it.
- Row 9: both firmwares abort only at run status 1 or 2. Fixed.
- Row 4: the wait monitor is stopped a second after the tasks stop. Its error
  was reraised with a wrong call, and a failing monitor now tells NI's
  acquisition worker, which waited for it with no timeout.
- Row 5: blacs calls `abort_transition_to_buffered` only on the tab whose own
  transition failed; the other tabs get `abort_buffered`, which already ran the
  stop functions. So the row's case is a FunctionRunner whose own start
  function raised.
- Row 8: a 5 s deadline in the arming loop. `wait_for_end_of_shot` was not
  used, because its error speaks of the shot's end.
- Row 10: waits are now placed by clock ticks, which also fixes a second wait
  landing one instruction late (as upstream).
- Row 11: the DMD sends no second answer after System Busy (TI's DLPU007,
  2.1.1), so the command is sent again, for up to 30 s.
- Shot files against `a21e313`: 65 test shots identical, 31 failing the same
  way. Intended differences:
  - an AlazarTechBoard with two acquisitions compiles;
  - PrawnDO ramps compile;
  - a PrawnDO shot with two or more waits has a new PULSE_PROGRAM;
  - new LabscriptErrors from LightCrafterDMD, PhaseMatrixQuickSyn and Cicero;
  - LightCrafterDMD's two-ImageSet message is new.
- The earlier rounds' sweeps compared a failed compile's partial shot file as
  if it had compiled. Rerun, gated on exit status, over `e791c8d..a21e313`, they
  missed only NovaTechDDS9M's `err2` message, which now names the renamed
  connection.
- Lab checks, on Development:
  - row 4: an NI shot with waits still records every wait, and one with its
    start pulse unplugged fails rather than hangs;
  - row 3: the Windows DLL.

### Codex's findings

- One `Deadline` (`labscript_devices/deadline.py`, named by the librarian)
  polls until done and gives a library call the time left. It raises "<device>
  did not <what> within <seconds> s.", also when the library's own timeout
  runs out. These use it:
  - PseudoclockWorker's end-of-shot wait;
  - PrawnBlaster's arming;
  - stopping NI's wait-monitor thread (2 s), and the acquisition worker's wait
    for the wait durations (30 s);
  - LightCrafterDMD's command (30 s);
  - RFBlaster's requests.

  PrawnBlaster's and LightCrafterDMD's timeouts used to raise RuntimeError.
- 1: NI reads its counter in chunks of at most 0.2 s, within a wait's timeout,
  and keeps the samples a timed-out chunk returns. A wait's own timeout is not
  a `Deadline`, since when it runs out a resume pulse is sent, not an error.
- 2: a failure anywhere up to writing the wait durations posts `'failed'`.
- 3: LightCrafterDMD gives each socket operation and retry sleep the time left.
- 4: no change, by Ian's decision.
- 5: the PulseBlaster parser knows a DDS by its `dds n` connection.
- The review found four faults, all fixed:
  - `timeout_for` let zprocess's own error through when its timeout ran out a
    moment early;
  - a chunk could lose an edge;
  - one timeout per attempt let a LightCrafterDMD answer take 60 s;
  - RFBlaster retried a timeout and restarted kloned. That behaviour change is
    undone, as Ian then decided.
- Rule 6 forbids timeout machinery around ZMQ calls. Ian's plan gives the
  acquisition worker's wait the deadline, and it passes the time left to
  zprocess's own `Event.wait(timeout=)`.
- Shot files: every test shot is identical to `0c690fb`, or fails the same
  way. No compile code changed after `c894f3e`.
- Lab check, on Development: a shot with waits on NI's chunked counter reads
  records every wait. This also confirms that PyDAQmx takes the array slice a
  partial read continues into.

## Step 2.4: dead code and compatibility leftovers

A table for Ian; nothing is changed until he decides. A name counts as unused
when `git -C <repo> grep -n -w -I` finds only its definition in every one of
the 16 repos: labscript, labscript-utils, labscript-devices, blacs, runmanager,
lyse, runviewer, zprocess, labscript-suite, labscript-optimization,
labscript-agents, spielman-devices, hyde, labscript-digilock, desktop-app and
labscript-c-extensions. Docs and the `.tex` guides are part of each repo's
search, and strings count as uses, since BLACS and runviewer look classes up by
name.

The sweep covered 1,541 definitions with 15,968 searches, and none of them
broke.
- Control: `PseudoclockWorker` was found in all 9 files that use it.
- Control: a scratch module with 7 injected names flagged exactly the 6 unused
  ones.
- The 12 NI_DAQmx model classes that only a computed name loads
  (`models/__init__.py`) were taken out by hand.

The LEGACY paths this pass added, each with its FutureWarning, stay by decision
and are not listed. Experiment scripts and lab code outside these repos can call
any public name, so a public row is kept unless Ian says otherwise.

| # | Item | File:line | Evidence | Public? | Proposal | Size |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `NI_PCI_6733.py`, `NI_PCIe_6363.py`, `NI_USB_6343.py`: the pre-NI_DAQmx import paths | `labscript_devices/NI_*.py:13-18` | no repo imports `labscript_devices.NI_PCIe_6363` and the others; control: the current path is found in labscript's `example.py:30` and `docs/source/devices/ni_daqs.rst:34` | yes: upstream's, for old experiment scripts | keep; on Ian's word they go, and a script that uses an old path breaks | 3 files |
| 2 | NI_DAQmx's model spec without `AI_term_cfg`, read as RSE with a FutureWarning | `NI_DAQmx/labscript_devices.py:234-242` | every bundled model with AI inputs gives `AI_term_cfg` (11 in `capabilities.json`); only a lab's own older model spec reaches it | yes: upstream's | keep; its warning names `get_capabilites.py`, a misspelling, to correct | 1 line |
| 3 | A camera without the interface, under a lab's `IMAQdxCameraWorker` subclass | `IMAQdxCamera/blacs_workers.py:169-195` | no suite worker uses it, spielman-devices included; `OldStyleCameraTests` tests it; `triggerablecamera.rst:19` documents it | yes: upstream's way to add a camera | keep | none |
| 4 | `expose(name, t)` taken in the old argument order | `TriggerableCamera/labscript_devices.py:198-206` | upstream's (IMAQdxCamera) | yes | keep | none |
| 5 | NovaTech's `com_port,baud_rate` connection | `NovaTechDDS9M/blacs_tabs.py:93-99` | not a leftover: the labscript class still writes it (`labscript_devices.py:70, 72`) | n/a | keep | none |
| 6 | AlazarTech SDK constants, 158 unused | `atsapi.py` | definition only | yes: the vendor wrapper | keep | none |
| 7 | `atsapi.enter_pressed`, a keyboard poll from AlazarTech's samples | `atsapi.py:449-462` | definition only | exposed, not documented | remove | −14 |
| 8 | Andor SDK wrappers, 11 unused, and `at_64` | `AndorSolis/andor_sdk/andor_solis.py` | definition only | yes: the SDK wrapper | keep | none |
| 9 | Four "reserved" Andor stubs: `GetAcquiredFloatData`, `GetAllDMAData`, `GetBackground`, `GetCYMGShift` | `andor_solis.py:319, 383, 427, 567` | definition only; each body ends in `pass`; `GetCYMGShift` reads `iXShift` before setting it, a NameError if called | exposed, does nothing | remove | about −30 |
| 10 | `ImageSet.set_array`, `PulseBlasterDDS.hold_phase` and `release_phase`, and TekScope's `save_screenshot`, `set_date_time` and `get_acquire_state` | `LightCrafterDMD/labscript_devices.py:54`, `PulseBlaster/labscript_devices.py:58, 61`, `TekScope/TekScope.py:120, 127, 143` | no caller in the suite | yes: for experiment scripts, in the autodoc pages | keep | none |
| 11 | PulseBlaster parser profiling: `profile` (a decorator that returns its function unchanged), `start_profile`, `stop_profile` and `profiles` | `PulseBlaster/runviewer_parsers.py:22-61`; `@profile` at :224, :235 | `start_profile` and `stop_profile` are called only in commented-out lines (:147-168); re-exported by `PulseBlaster/__init__.py:38` | exposed as upstream's module names, not documented | remove, with its commented calls and its exports | about −50 |
| 12 | `testing/` scripts: FunctionRunner's `test.py`, IMAQdxCamera's `test.py`, NI_DAQmx's `test_NI_DAQmx_labscript.py` and ZaberStageController's `test.py` | `<device>/testing/` | not imported or run in any repo; no docs | internal: not packages | remove | −160 |
| 13 | DummyCamera's `testing/test.py`, the fork's | `DummyCamera/testing/test.py` | `dummycamera.rst:77` points to it as the working example | documented | keep | none |
| 14 | PylonCamera's `testing/ExposureTiming.py` | `PylonCamera/testing/ExposureTiming.py` | `pylon.rst:103-123` documents it as a utility | documented | keep | none |
| 15 | `__main__` demos: TekScope's, and Andor's `if __name__ in '__main__': pass` with 48 commented lines | `TekScope/TekScope.py:153-159`, `andor_utils.py:665-715` | not referenced | internal | remove | −57 |
| 16 | `__main__` tools: `daqmx_utils.py`, `generate_subclasses.py`, `get_capabilities.py`, and the package `__init__.py`'s self-import guard | `NI_DAQmx/daqmx_utils.py:139-150` and the rest | the model tools are documented (`ni_daqs.rst:22-29`); `daqmx_utils.py`'s is a card diagnostic | yes | keep | none |
| 17 | `test_device`, upstream's do-nothing test device | `test_device/` | `testdevice.rst` documents it | yes | keep | none |
| 18 | `models/README.txt` names `generate_classes.py`, which does not exist (as upstream) | `NI_DAQmx/models/README.txt:9` | the file is `generate_subclasses.py` | docs | correct | 1 line |
| 19 | Commented-out code: 59 runs, 58 of them upstream's. The largest are `atsapi.py:591-772` and `:934-974` (vendor DSP wrappers), `andor_utils.py:668-715` (row 15), LightCrafterDMD `blacs_tabs.py:43-50`, and 10 AlazarTech debug prints | across the package | none of it runs | internal | step 5 decides it, with the 36 TODOs; proposal: remove all | about −420 |
| 20 | `spielman_merged/Numpy2Fixes` (`a5ac858`) and `spielman_merged/Qt6Fixes` (`3d3b3db`), local and on origin | branches | no commit outside `Development`; `git cherry` is empty for both | n/a | delete, local and origin | 4 refs |
| 21 | `maintenance/3.0.x` (`080e054`) and `more-ni-daq-models` (`ce82ea8`), on origin | branches | identical to upstream's own; lyse and runviewer deleted their copies | n/a | delete from origin; upstream keeps them | 2 refs |

`DummyCamera`, upstream pull request #148's head, stays. `UpstreamBugFixes`,
`CodeHealth` and the tiers are not decided here. Seen on the way, for step 6:
five comments narrate history ("'S' rather than the 'a' this used to say"), in
AlazarTechBoard, Cicero, NI_DAQmx twice and PrawnBlaster.

### Built

- Rows 7, 9, 11, 12 and 15 removed; rows 2 and 18 corrected, with
  `generate_subclasses.py`'s own banner, which had the same wrong name, and the
  warning's `AI_Term_Cfg` for `AI_term_cfg`. Row 19 goes to step 5. The rest
  are kept.
- Row 1, by Ian's decision: the old paths stay, and each import from one gives
  the NI_DAQmx class itself, with a FutureWarning at the importing line naming
  the NI_DAQmx path.
  - `lazy_attributes` takes `legacy=True` for it. A module `__getattr__` runs in
    the importing frame, so the warning points at that line on every supported
    Python.
  - `__all__` keeps a star import working.
  - `labscript-utils`' `deprecated_import_alias` returned a wrapper function,
    not the class, and warned only at the first call. These modules were its
    last users in the suite.
  - BLACS and runviewer find the three cards in the registry, so they never
    import these modules and never warn.
- Shot files: every test shot is identical to `2443b93`, or fails the same
  way. A shot compiled through an old path is identical to one compiled
  through the new path.
- Branches: the deletions need Ian. Their tips:
  - `spielman_merged/Numpy2Fixes` `a5ac8581d5c790b3f9a590516837c72a3750e11a`,
    local and origin;
  - `spielman_merged/Qt6Fixes` `3d3b3db8b4037ae356164f46811e8c11424bbb17`,
    local and origin;
  - `maintenance/3.0.x` `080e054e266251c15f0bf4cf6a6373ad187a0f83`, origin;
  - `more-ni-daq-models` `ce82ea8ddab511138e378f0b8368232823c1a110`, origin.

## Step 2.5: documents

A table for Ian; nothing is changed until he decides. TODO lines are as of
`5400b1d`. Commented-out runs keep step 2.4's numbers (row 19); 11 of the 59
went with step 2.4's removals, and 48 runs, 305 lines, remain. Each "Possible
improvements" item is worded below the table. That page would be new,
`docs/source/improvements.rst`, in the index, as labscript and labscript-utils
have it.

| # | Item | File:line | Proposal | Reason | Size |
| --- | --- | --- | --- | --- | --- |
| 1 | TODO: PineBlaster's parser `trigger_delay` "find out what this actually is" | `PineBlaster/runviewer_parsers.py:22` | do it: the parser takes the class's measured 350 ns (`labscript_devices.py:26`), not 1 µs | the answer is already in the code; runviewer draws a secondary PineBlaster 650 ns late (an intended trace change) | 2 lines |
| 2 | TODO: RFBlaster "bounds checking" | `RFBlaster/labscript_devices.py:92` | do it: give its three `quantise_channel` calls the limits its BLACS tab uses (350 MHz, amplitude 0 to 1, phase 0 to 360) | an out-of-range value is quantised into int32 without an error | 3 lines |
| 3 | TODOs done already: PulseBlaster's parser trigger-delay offset, PulseBlaster's `n_dds`, QuickSyn's widget update | `PulseBlaster/runviewer_parsers.py:135`, `PulseBlaster/labscript_devices.py:631`, `PhaseMatrixQuickSyn/blacs_tabs.py:67` | delete | the next line, the DDS mixin with `num_dds`, and the code below each do what they ask | −3 |
| 4 | TODOs the code answers: NovaTech's phase precision, RFBlaster's amplitude and phase precision | `NovaTechDDS9M/blacs_tabs.py:41`, `RFBlaster/blacs_tabs.py:50` | delete | each device's quantiser fixes it (NovaTech 45.51 steps a degree, 0.022°) | −2 |
| 5 | TODOs not worth doing: two `shutdown`s, Zaber's smart programming, NovaTech's reprogram-only-changes, PulseBlaster's firmware checks, three Andor SDK notes, NI_DAQmx's AI "broker" (two) | `PulseBlaster/blacs_workers.py:272`, `RFBlaster/blacs_workers.py:207`, `ZaberStageController/blacs_tabs.py:53`, `NovaTechDDS9M/blacs_workers.py:128`, `PulseBlaster/labscript_devices.py:102`, `andor_solis.py:146`, `andor_utils.py:447, 473`, `NI_DAQmx/blacs_workers.py:479, 488` | delete, and reword `:488`'s docstring | the process's exit closes both boards; the rest no one has asked for, or names a server that does not exist | −10 |
| 6 | TODOs saying "untested" | `NovaTechDDS9M/blacs_workers.py:267`, `RFBlaster/blacs_workers.py:115` | delete | hardware validation on Development is where untested code gets tested | −2 |
| 7 | TODO: PrawnDO's `trigger_delay` "gets applied twice on waits" | `PrawnDO/labscript_devices.py:81` | a `KNOWN_ISSUES.md` line, unverified, in place of the TODO | a suspected bug, not an improvement | 1 line |
| 8 | TODOs worth doing but larger, the three `program_manual`s' "return coerced/quantised values" among them | `NI_DAQmx/blacs_workers.py:136`, `PulseBlaster/blacs_workers.py:98, 336`; `PulseBlaster/labscript_devices.py:222, 252`, `AlazarTechBoard/labscript_devices.py:72`; `PineBlaster/labscript_devices.py:27`, `PineBlaster/runviewer_parsers.py:24`, `RFBlaster/labscript_devices.py:24`, `CiceroOpalKellyXEM3001/labscript_devices.py:46, 55`; `andor_utils.py:560`, `AndorSolis/blacs_workers.py:48`; `TekScope/blacs_workers.py:36`; `pseudoclock.py:55, 72` | move to Possible improvements (items a to g) | each is real, and needs more than a small change or a board to measure | −16 lines here |
| 9 | Commented-out debug prints | B2-B4, B6-B11 (AlazarTechBoard), B39-B41, B43 (PulseBlaster parser, Python 2), B47 (RFBlaster, Python 2), B49 (Spinnaker) | delete | debugging left over; the Python 2 ones cannot even run | 15 runs, −16 |
| 10 | Commented-out older forms of live code | B5, B13, B18, B21, B23, B36 with B44 (a slow-clock trace whose read is gone), B45 ("for history"), B50 | delete | each is replaced by the line beside it; git keeps the history | 9 runs, −22 |
| 11 | Commented-out calls the code does without | B1, B12, B14, B16, B19, B24, B28, B29, B34, B46, B48, B51, B52 | delete | none is a behaviour anyone has asked for back; TekScope's `*RST` on abort and LightCrafterDMD's blank image at start are the nearest, and neither is wanted | 13 runs, −16 |
| 12 | Cicero's design notes, with their pseudo-code (B17, B20) | `CiceroOpalKellyXEM3001/blacs_workers.py:196-216, 262-276` | delete | the code below them does what they plan; their one live point, missed close waits, goes to item f | −36 |
| 13 | LightCrafterDMD's alternative view | B26, B27 (`LightCrafterDMD/blacs_tabs.py:38-50`) | delete | the tab places its widgets with `auto_place_widgets` | −10 |
| 14 | AlazarTech wrappers commented out: DSP and OCT functions, and two `Board.__init__` lookups | B54-B59 (`atsapi.py:576-757, 802-806, 905-910, 919-959, 1165-1176`) | delete | AlazarTech ships the full `atsapi.py`, should a lab need them | −244 |
| 15 | The commented `labscript_init` in DummyCamera's example | B22 (`DummyCamera/testing/test.py:22`) | keep | part of the documented example: it shows how to run the script outside runmanager | none |
| 16 | Deferred (Ian, step 2.2): front-panel bit packing | DEEP_PASS step 2.2 | Possible improvements (item h) | the only near-duplicate step 2.2.1 did not resolve: quantisers, ticks, status monitors and camera defaults are each one implementation now | — |
| 17 | Step 2.3's defers that are improvements: rows 18, 20 and 21 | `KNOWN_ISSUES.md` | move to Possible improvements (items b, i, j), and their known issues lines go | each is a better form of working code, not a fault; row 13, RFBlaster's missing readback, stays a known issue | −3 lines there |
| 18 | `DEEP_PASS.md` | root | delete in the last commit before `CodeHealth` merges into `Development` | the campaign's record, spent at the merge; Codex and the master read it until then | −all |
| 19 | `NI_DAQmx/models/README.txt` | `NI_DAQmx/models/` | keep | upstream's notice, beside the generated files, that they are regenerated | none |

No other file is a document: the licences, workflows, `pyproject.toml`,
`readthedocs.yaml` and `.ui` files are not.

Possible improvements, as the page would word them:

- a. **The values a manual program took.** NI_DAQmx's and PulseBlaster's
  `program_manual` return nothing, so BLACS shows the values asked for, not
  the ones the hardware took after quantising.
- b. **Connections checked when they are made.** PulseBlaster checks its
  outputs' connections, and that a board without DDS has no DDS on it, only
  when the shot compiles. AlazarTechBoard does not check its inputs'
  connections at all. Checking in `add_device` would put the error at the line
  that connects.
- c. **Measured delays.** PineBlaster's `wait_delay`, RFBlaster's
  `trigger_delay` and `wait_delay`, and Cicero's `trigger_delay` and
  `wait_delay` are estimates. Measuring each on a board would make the timing
  exact.
- d. **Andor acquisitions.** The worker waits for the camera to go idle, with a
  timeout. Counting the frames acquired would end the wait sooner, and checking
  for an abort during it would make an abort prompt.
- e. **TekScope settings per shot.** The acquisition mode and channels are
  fixed in the worker; the shot file could give them.
- f. **Waits close together.** `PseudoclockTab` polls a board's status every
  100 ms, and Cicero finds its waits from sample counts, so two waits closer
  than a poll can be taken for one.
- g. **Reporting a worker's failure.** `PseudoclockTab` tells BLACS that a shot
  failed by faking a restart of the device. A BLACS call for it would be
  plainer.
- h. **Front-panel bit packing.** NI_DAQmx's worker and parser, and PrawnDO's
  worker, each pack a port's line values into an integer and back. One helper
  beside labscript's `bitfield` could serve all three.
- i. **TekScope's module name.** The driver module `TekScope/TekScope.py` has
  the class's name, so once a worker imports it,
  `labscript_devices.TekScope.TekScope` is the module, not the class. Renaming
  the module would end that.
- j. **test_device's keyword.** `DoSomething` would be `do_something`, with the
  old name kept as a legacy keyword.

### Built

- Every row is done, row 13 too on Ian's second word.
  - Row 13 was 10 commented lines in LightCrafterDMD's tab. They hid the image
    widgets and drew the DMD on a `QGraphicsScene`, through two classes,
    `SLMGraphicsView` and `ImageWrapperWidget`, that no repo has.
  - No TODO is left in the package; atsapi's `TRIGGER_XXXXX` is a constant.
- Row 1 changes runviewer: a secondary PineBlaster is drawn 350 ns after its
  trigger, not 1 µs. Only the six triggered PineBlasters in the test shots
  trace differently.
- Row 2: RFBlaster's limits are the board's range, 0 to 350 MHz and amplitude 0
  to 1. Its phase wraps, as NovaTechDDS9M's does, rather than being refused
  past 360. Each test shot still compiles, and out-of-range values raise.
- Row 7, verified on Ian's word: the PrawnDO's `trigger_delay` is applied once
  per trigger, not twice. labscript subtracts it once per trigger, and the
  firmware resumes from a wait as it starts.
  - Probe: a PrawnBlaster master with one and three waits. Every PrawnDO change
    lands on its script time, to a 10 ns tick.
  - In its place, a known issue: PrawnDO's runviewer parser does not take its
    master's tick after a wait, so its trace runs ahead by the master's
    `wait_delay` each wait.
- Shot files: every test shot is identical to `8028a2c`, or fails the same
  way. Parsed traces are identical apart from row 1's. The docs build.
- For other owners:
  - labscript's `quantise_channel` wraps a phase before rounding it, so a phase
    just under 360°, or a tiny negative one, reaches the device as one past the
    top of its phase word (16384 of 14 bits on RFBlaster). NovaTechDDS9M has the
    same edge.
- Seen, not changed: PulseBlaster's compile code is written for two DDS, though
  the deleted `n_dds` TODO read as done. The one DDS board has two.

## Step 2.6: style

Each package restyled after the PrawnBlaster sample Ian approved (`83b11ce`),
one commit a package, the top-level modules last.

### Built

- NumPy docstrings on the public surface only: the device classes, with a
  one-line summary and the `Parameters` block on `__init__`, so that the docs'
  `autoclass_content='both'` shows each class's own keywords, and the methods a
  script calls. Internal code has one line or none. Comments are at most three
  lines and say why; error messages say what to do where it is not obvious.
  - Code changed only by f-strings, dropped `(object)`, scoped Qt enums and
    message text, apart from the fixes below; each package's other code was
    checked unchanged with its docstrings stripped.
  - Left as they are: `atsapi.py`, AndorSolis's `andor_solis.py` and
    `andor_capabilities.py`, and NI_DAQmx's generated models but for one line.
- The two PrawnBlaster fixes:
  - `3fd37cf`: for a clock other than 100 MHz, `clock_limit` was scaled by the
    ratio of the clock periods, as the times are; a rate scales the other way.
  - `eeedd65`: the firmware's `setb` refuses a block that reaches the end of
    its table, which a one-pseudoclock program can fill. The worker now sends
    that last row with `set`. A limit in the compiler would have needed two
    fewer instructions plus a stop to stay safe, giving up capacity the class
    documents. Ordinary programs' serial traffic is unchanged.
- `f2a954c`: the NI_DAQmx models' `__init__` docstring, "Class for <model>",
  rendered in place of NI_DAQmx's `Parameters`; it is removed from the template
  and from the 19 generated models, one line each.
- `e46f6c2`, the overall review: fix-its that could not work and sentences
  false of the code, corrected, and four more faults listed.
- Codex's findings:
  - `fd44105`: PrawnDO's parser resumes its nth wait on the master's tick at
    the shot's nth wait time. It searched from its own wait time, which a
    PrawnDO clock coarser than the master's rounds past the retrigger: at
    5 MHz a wait at 10.12 µs starts at 10.2 µs, after the master's 10.16 µs
    tick. A compiled shot showed it for a trigger connection (IndexError) and
    a direct clock line (a later tick, 3.2 µs late); both now resume at
    11.16 µs. The board itself is in its wait long before a real wait ends.
    The shared model below replaces it.
  - `1b750c9`: docstrings and messages made true (`QuickSynDDS.disable`,
    TekScope's `int16`, AndorSolis's EMCCD gain, `Deadline.wait`). The key
    schemas of FlyCapture2's setters, and `TriggerableCameraInterface`'s
    contracts for the cameras that implement it, are docstrings again. A
    PrawnDO wait holding the value set at its time is documented behaviour
    (`prawndo.rst`, Waits), so it is no longer a known issue.
- Lab check, on Development: a one-pseudoclock PrawnBlaster program that
  fills its table, for `setb`'s boundary, which no board has confirmed.
- Shot files: every test shot is identical to `44d9251`, or fails the same way
  with its reworded message (NovaTechDDS9M_err1, PhaseMatrixQuickSyn_err3,
  PulseBlaster_err1 to 3, PulseBlaster_SP2_24_100_32k_err2, RFBlaster_err1 and
  2, LightCrafterDMD_err1 to 8, test_device_shot2,
  myshots_my_prawndo_repeat). Parsed traces are identical. The docs build adds
  no warning, and every `Parameters` block names its signature's arguments.
- Faults found, listed in `KNOWN_ISSUES.md` and not fixed: 47 lines. Those an
  ordinary setup meets:
  - NI_DAQmx's `stop_task` never reads the samples after the last full chunk
    of an analog input acquisition.
  - AndorSolis refuses its default EMCCD gain, and EMCCD with cooldown on the
    first setup.
  - PrawnDO reports its outputs low after a shot; LightCrafterDMD's front panel
    keeps the image from before a shot.
  - TekScope's `int16` traces are garbage.
  - A serial number given as a string finds the wrong FLIR or Basler camera.
- Dead code seen, not removed:
  - RFBlaster's retry and `restart_kloned` path, which no error requests raises
    reaches, and its unused final values.
  - PineBlaster's `clock_type`; Cicero's `ReadU32` and `current_value`;
    PhaseMatrixQuickSyn's `generation` and worker `final_values`;
    LightCrafterDMD's `slm_properties`; AlazarTechBoard's `start` and
    `triggerDelay_samples`; FunctionRunner's `monotonic` import; NI_DAQmx's
    last `clock_terminal` check, which the two before it make unreachable.
- For other owners: FunctionRunner deserialises its functions with `__name__`
  and `__file__` set to the device name, for `lyse.Run` to name its results
  group after the device, but lyse takes the group from
  `sys.modules['__main__'].__file__`.

## Runviewer's model of a triggered device

- Six parsers each timed a pseudoclock device's start and its resumes after
  waits: PrawnBlaster, PrawnDO, PineBlaster, DummyPseudoclock, Cicero and
  PulseBlaster. They held 28 cases, in three versions: counting edges,
  searching by time, ignoring the clock. Masters drew each wait as lasting its
  `wait_delay`, so traces after a wait left script time, and PrawnDO's search
  (`fd44105`) ran time backward after four waits.
- `e9d1a54`: one model, `PseudoclockParser` in `runviewer_parsing.py`, on the
  script's time, in which a wait takes no time.
  - Each device resumes where its wait begins. A master's own program places
    its waits, so it carries on from there. A secondary starts and resumes
    `trigger_delay` after its trigger times, which labscript saves, in time
    order, as it rounded them (`4d88c40`, `99b4f59`, `0297dee`). That holds
    for a trigger line and for a shared clock line alike, and for waits called
    out of time order.
  - A shot file compiled before `4d88c40` falls back, under a LEGACY marker, to
    the clock's first edge and then the edge nearest each wait's time:
    labscript rounds a trigger to the nearest tick and keeps the wait's time
    unrounded.
  - Drawn against `bf3f10a`'s nearest edge, on the sweep's shots compiled with
    `4d88c40` and three PrawnDO wait shots, 183 of 187 traces are identical.
    Four PrawnDO traces differ by at most 7e-21 s, the float difference between
    the saved times and the drawn edges. None of these shots has a tie.
  - A class, not a pure function, as the parsers also shared the tick loop and
    the clock-line dict, four copies of each. The change is 79 lines shorter,
    the class included. pseudoclock.py imports BLACS, so the class lives with
    the other parser helpers.
  - No shared reader of `/waits` (Ian: "yes, drop the reader"). labscript
    writes the table already sorted, so a reader would only pass the column
    through; the class reads `f['waits']['time']` itself.
  - `tests/test_runviewer_waits.py`: a PrawnDO on a shared clock line and one
    on a trigger line, over four waits with a shared tick at 39.9 µs and three
    off the master's grid, rounding down, up and from an exact tie, change at
    their script times, and no drawn time runs backward. It fails on `1fea8d6`
    and on `41ed060`. The nearest edge drew the tie the same, as the tie's
    other neighbouring tick carries no edge. One wait is called out of time
    order: the test fails with labscript `4d88c40`, which saved trigger times
    in call order, and passes through the fallback, as `/waits` is written
    sorted.
  - Codex's finding on `e9d1a54`, fixed in `9070de8`: a master
    resumed at the unrounded wait time, before its own wait began, and a
    secondary took the first edge at or after it, which misses a retrigger
    rounded down.
- Drawn traces, against `1fea8d6`, over the sweep's 96 test shots and three
  PrawnDO wait shots: after wait n each moves earlier by n times its master's
  `wait_delay`, onto script time: 40 ns on a PrawnBlaster, 50 ns on a PrawnDO,
  2.5 µs on a PineBlaster or DummyPseudoclock, 10 ns (a clock period) on a
  Cicero, and 100 ns on a PulseBlaster. A wait row drawn at its own time moves
  less. A trace the old parsers resumed on a wrong edge moves by their error
  instead: a PrawnDO sharing its clock line with a tick at 39.9 µs resumes
  after the fourth wait at 41.00 µs, where it was drawn at 41.02, 20 ns, not
  160.
  The two PulseBlaster secondaries of `plain_trigger_devices` start at their
  trigger, 0.74 µs, where they were drawn as if triggered at 0. No other trace
  moves.

## The pass's open findings: triage (for Ian)

Every finding of the pass, steps 1 to 2.6, still open, or left by a decision:
- the 52 lines of `KNOWN_ISSUES.md` (KI);
- the rows earlier steps deferred or left;
- the dead code step 2.6 saw and did not remove;
- the docs' Possible improvements;
- the items for other owners, and the lab checks.

The step each comes from is in brackets after its file. Ranked by Ian's rule,
"can a reasonable sequence in his labs reach this?"; his labs run PulseBlaster
masters, NovaTech DDSs and NI cards. Those rows come first, then the other
devices' by severity, then dead code, then the design choices and
improvements already decided.

Every fix is in labscript-devices unless the row names another repo. "Verify
first" means the fix needs a board, a camera or a vendor SDK to be sure of;
anything fixed is checked on Development's hardware after the merge.
"Decided" quotes Ian's words, and the step; text outside the quotes is this
file's record of what he decided. Nothing is changed until Ian decides the
rest.

| # | Device, file | What goes wrong | Severity | Who reaches it | Fix, size | Verify first | Proposal | Decided |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | NI_DAQmx `blacs_workers.py` `stop_task` (2.6, KI) | the samples after each analog input acquisition's last full chunk are never read | high: lost data | every NI lab acquiring analog input, Ian's included | pass the integer task handle, as the callback does, 1 line | no | fix now | |
| 2 | PulseBlaster, PulseBlaster_No_DDS `labscript_devices.py` delays (2.3 row 3, KI) | delays reach SpinAPI as float ns, about 9% just under a whole cycle; if the labs' Windows `spinapi64.dll` truncates them, each repetition of a looped step runs a cycle short, about 39 µs over a 2,905-step ramp. Linux's library rounds | high, if it truncates | every PulseBlaster ramp in Ian's labs | pass a delay SpinAPI turns into the whole cycle, about 3 lines | the DLL's disassembly, or a long looped ramp timed on a board | verify first, on Development | step 2.3: "agree with fix now, verify first and defer groups"; this row is in verify first |
| 3 | NI_DAQmx `blacs_workers.py` wait monitor (2.3 row 4, Codex's finding 1) | built, but not run on a card: that a shot with its start pulse unplugged fails rather than hangs, and that chunked counter reads record every wait | high, if either is wrong: a hang, or a lost wait | Ian's NI labs with waits | none: two lab checks | NI card | verify first, on Development | step 2.3: "agree with fix now, verify first and defer groups"; the row is now, then hardware validation on Development. Codex's fixes: "yes send the fixes to labscript-devices" |
| 4 | NovaTechDDS9M `blacs_workers.py` `check_remote_values` (2.6, KI) | a NovaTech that does not answer raises ValueError, not the "cannot connect" error meant | low-medium: misleading error | Ian's NovaTech labs, on a dead link | test the empty reply, 3 lines | no | fix now | |
| 5 | PulseBlaster `labscript_devices.py` `get_direct_outputs` (2.6, KI) | a connection's prefix is not checked against the output's class: a DigitalOut on 'dds 1' drives flag 1 | low-medium: a typo is accepted | Ian's PulseBlaster labs, on a typo | refuse the mismatch, about 6 lines | no | fix now | |
| 6 | NI_DAQmx `labscript_devices.py` `static_AO` (2.6, KI) | `static_AO=False` is accepted on a device that cannot buffer AO, so an unclockable AnalogOut compiles | low-medium | an NI lab misconfiguring a model | refuse it, 2 lines | no | fix now | |
| 7 | DummyCamera `labscript_devices.py` guard, and labscript (2.3 row 19) | a failed `generate_code` leaves a shot file that cannot be compiled again, as labscript writes the shot file in place | low-medium | any device's failed compile, Ian's labs included | labscript's: compile to a temporary file, then move it | no | as decided | step 2.3: "agree with your views on 5, 6, 17b and 19"; the view on 19 was labscript's owner, and the in-place shot file is deferred to a later refactor |
| 8 | PulseBlaster `labscript_devices.py` `PulseBlasterDDS` (2.6, KI) | a `digital_gate` is not refused, and fails later on a gate-name clash | low | a PulseBlaster DDS user passing one | refuse it, 2 lines | no | fix now | |
| 9 | NI_DAQmx `utils.py` `split_conn_DO` (2.6, KI) | its error names the reassigned connection, not the one given | low | a typo | name the original, 1 line | no | fix now | |
| 10 | PulseBlaster `blacs_workers.py` transition abort (2.3 row 6) | a transition abort leaves the board programmed, and a secondary on BRANCH armed, until BLACS reprograms it | low: BLACS reprograms it | a PulseBlaster lab whose other device fails its transition | none | no | as decided | step 2.3: "agree with your views on 5, 6, 17b and 19"; the view on 6 was to leave it, with a one-line comment that blacs reprograms the device afterwards |
| 11 | PulseBlasterESRPro200, PulseBlaster_SP2_24_100_32k `labscript_devices.py` (2.6, KI) | `clock_resolution` is one cycle, not two, so a symmetric tick of an odd number of cycles may run long | unknown | those two boards | two cycles, if SpinAPI rounds both halves up, 1 line each | SpinAPI, or a board | verify first | |
| 12 | NI_DAQmx's old import paths `NI_PCI_6733.py`, `NI_PCIe_6363.py`, `NI_USB_6343.py` (2.4 row 1) | kept for old experiment scripts: each import gives NI_DAQmx's class, with a FutureWarning | none: legacy | old experiment scripts | remove them, on Ian's word | no | as decided | step 2.4: "for the old NI paths, do not remove them, and instead add the depriciation warnings there too" |
| 13 | AlazarTechBoard `blacs_workers.py` `find_nearest_internal_clock` (2.3's build, KI) | it makes a 0-d array of the `dict_keys` it is given, so with the default `INTERNAL_CLOCK`, `transition_to_buffered` raises TypeError (as upstream) | high: the default clock cannot run a shot | every Alazar lab on its internal clock | an array of the keys as a list, 1 line | no | fix now | |
| 14 | AndorSolis `andor_utils.py` `enable_emccd` (2.6, KI) | only the gain range's two ends pass, so the default 50 is refused | high: EMCCD cannot be used | an Andor lab using EMCCD gain | test `low <= gain <= high`, 1 line | no | fix now | |
| 15 | AndorSolis `andor_utils.py` `setup_acquisition` (2.6, KI) | EMCCD with cooldown raises on the first setup, as the gain is set before cooling starts | high, with row 14 | the same lab | enable cooldown before the EMCCD gain, a block moved | camera: the cooldown waits until stable | fix now | |
| 16 | PrawnDO `blacs_workers.py` smart programming (2.6, KI) | a program at most 10% longer than the cached one raises IndexError | medium: shot fails | a PrawnDO lab scanning a parameter that adds instructions | cache the new program whole, about 3 lines | no | fix now | |
| 17 | PrawnDO `blacs_workers.py` final values (2.6, KI) | BLACS shows every output low after a shot, from the stop row's ignored bit set | medium: front panel wrong until reprogrammed | every PrawnDO lab | read the row before the stop, 1 line | no | fix now | |
| 18 | PrawnDO `labscript_devices.py` `clock_limit` (2.6, KI) | off 100 MHz, the clock limit scales the wrong way, as PrawnBlaster's did (fixed in `3fd37cf`) | medium: too-fast updates compile, or slow ones are refused | a PrawnDO at another clock | `/= factor`, 1 line | no | fix now | |
| 19 | PrawnBlaster `blacs_workers.py` `setb` boundary (2.6) | built (`eeedd65`), but not run on a board: a one-pseudoclock program that fills its table sends its last row with `set` | medium, if wrong: that program fails | a PrawnBlaster program that fills its table | none: a lab check | board | verify first, on Development | step 2.6: "fix the two PrawnBlaster bugs before the final validation" |
| 20 | TekScope `TekScope.py` `waveform` (2.6, KI) | with `int16` the trace is garbage: 16-bit points read as 4-byte `'i'` | medium: invalid data, only with `int16` | a TekScope lab that sets `int16` | datatype `'h'`, 1 line, and the parameter's doc | scope | fix now, then check on a scope | |
| 21 | SpinnakerCamera, FlyCapture2Camera, PylonCamera workers (2.6, KI) | a `serial_number` given as a string is read as hex, so the camera looked up is wrong or missing | medium: the camera does not open | a FLIR or Basler lab that writes its serial as a string | let a camera class say its serials are decimal, about 5 lines; IMAQdx keeps hex | no | fix now | |
| 22 | TriggerableCamera `blacs_workers.py` `exception_on_failed_shot` (2.6, KI) | with it True, a grab error ends the thread silently and the shot goes on with partial images | medium: the asked-for exception is lost | any camera lab with a grab error | re-raise the thread's error in `transition_to_manual`, about 4 lines | no | fix now | |
| 23 | TriggerableCamera `blacs_workers.py` continuous acquisition (2.6, KI) | a shot with no exposures for the camera leaves continuous acquisition paused, the tab showing it running | medium | a camera lab in continuous mode, with shots that skip that camera | resume before the early return, 2 lines | no | fix now | |
| 24 | AndorSolis `blacs_workers.py` `grab_multiple` (2.6, KI) | an abort waits for the next acquisition's timeout, and `abort()` joins without one | medium: slow or stuck abort | an Andor lab aborting a shot | poll the abort flag between acquisitions, 2 lines | camera | fix now, then check on a camera | |
| 25 | AlazarTechBoard `blacs_workers.py` lone channel B (2.6, KI) | `channels=CHANNEL_B` compiles, then raises TypeError at the end of the shot | medium | an Alazar lab using only channel B | refuse it at compile, 2 lines | no | fix now | |
| 26 | AlazarTechBoard `blacs_workers.py` DMA buffers (2.6, KI) | freed only after a successful shot, so each failed or aborted shot leaks them | medium: memory grows | an Alazar lab with failures | free them at the next transition or in abort, about 4 lines | board | verify first | |
| 27 | LightCrafterDMD `blacs_workers.py` final image (2.6, KI) | after a shot the front panel keeps its earlier image while the DMD shows the shot's last | medium, rare device | a LightCrafter lab | key the final image by the ImageSet's connection, 1 line | no | fix now | |
| 28 | SpinnakerCamera `blacs_workers.py` packed formats (2.6, KI) | every Mono format not ending in 8 is read as uint16, so Mono12Packed is misread | medium, for that format | a FLIR lab choosing a packed format | refuse packed formats, 2 lines, or decode them through PySpin | SDK, to decode | fix now, as a refusal | |
| 29 | FunctionRunner `blacs_workers.py`, and lyse (2.6, KI) | a `lyse.Run` in a function names its results group after the worker's script, not the device | medium: results under an unexpected name | a FunctionRunner lab saving results through `lyse.Run` | the docstring's `run.set_group(device_name)` is the workaround; a fix needs lyse to take a group from its caller, or the false `__name__` and `__file__` dropped here, 1 line | no | ask the lyse owner, then decide; defer meanwhile | |
| 30 | TriggerableCamera `attributes_dialog.ui`, `blacs_tab.ui` (2.6, KI) | the text tells every camera's users to pass `imaqdx_attributes` to IMAQdxCamera | low-medium: wrong instructions | every camera lab | say `camera_attributes`, two strings | no | fix now | |
| 31 | RFBlaster `labscript_devices.py` (2.6, KI) | an RFBlaster without `trigger_device` compiles as the master, which BLACS cannot start | low-medium | an RFBlaster lab | refuse it at compile, 2 lines | no | fix now | |
| 32 | AlazarTechBoard external clock, rate 0 (2.6, KI) | the default rate with the 10 MHz reference gives no samples and no error | low-medium | an Alazar lab forgetting the rate | refuse rate 0 at compile, 2 lines | no | fix now | |
| 33 | AndorSolis `andor_utils.py` `enable_preamp` (2.6, KI) | gains are checked against evenly spaced values, so a camera with uneven gains has some refused | low-medium | an Andor model with uneven gains | check the camera's own list, 3 lines | no | fix now | |
| 34 | FunctionRunner `utils.py` lambda (2.6, KI) | a lambda passes `add_function`, then the worker raises KeyError | low-medium | a FunctionRunner user writing a lambda | refuse it at `add_function`, 2 lines | no | fix now | |
| 35 | AndorSolis `andor_structures.py` `ulSize` (2.6, KI) | set to the Python object's size, not the structure's | unknown | every Andor lab, if the SDK checks it | `ctypes.sizeof`, 1 line | SDK or camera | verify first | |
| 36 | FlyCapture2Camera `blacs_workers.py` `set_image_mode` (2.6, KI) | the size is rounded to the offset steps, not the image steps | unknown | a FlyCapture2 lab setting an ROI | use the image step sizes, 2 lines | camera or SDK docs | verify first | |
| 37 | AndorSolis `blacs_workers.py` attributes (2.6, KI) | the interface's attributes are AndorCam's defaults dict itself, so setting one changes the defaults | low | an Andor lab changing attributes between shots | copy the dict, 1 line | no | fix now | |
| 38 | LightCrafterDMD `blacs_workers.py` `_receive` (2.6, KI) | a reply split across TCP segments is misread | low | a LightCrafter on a busy network | read until the length is in, about 6 lines | no | mine: defer. The master's: fix now | |
| 39 | SpinnakerCamera `blacs_workers.py` release on errors (2.6, KI) | an image, or the camera list and system, are not released when decoding or `__init__` raises | low | a FLIR lab after an error | `try`/`finally`, about 6 lines | no | mine: defer. The master's: fix now | |
| 40 | FlyCapture2Camera `blacs_workers.py` `is_transient_grab_error` (2.6, KI) | every Fc2error is retried, so a real fault retries without pause until the shot ends | low | a FlyCapture2 lab with a fault | retry only the timeout code | SDK | verify first | |
| 41 | SpinnakerCamera, FlyCapture2Camera visibility level (2.6, KI) | `saved_attribute_visibility_level` is ignored; every attribute is saved | low | FLIR labs | map the level to PySpin's visibility; FlyCapture2 has none | SDK | defer | |
| 42 | The bounded abort and end-of-shot waits (step 1, Codex's re-check) | a board that confirms its abort or end of shot after the deadline counts as done | low: the hardware did finish, and each poll is bounded by the serial read timeout | a board slow to confirm | none | no | as decided | step 1, on Codex's re-check: left as is (Ian) |
| 43 | TriggerableCamera `labscript_devices.py` visibility message (2.6, KI) | a bad `saved_attribute_visibility_level` raises TypeError, not the ValueError meant | low | a typo | format the tuple, 1 line | no | fix now | |
| 44 | TekScope `blacs_workers.py` no channel shown (2.6, KI) | with no channel displayed the shot fails with UnboundLocalError | low | a TekScope lab | raise a direct error, 2 lines | no | fix now | |
| 45 | FunctionRunner `labscript_devices.py` string `t` (2.6, KI) | a `t` other than 'start' or 'stop' raises float()'s ValueError | low | a typo | a direct message, 2 lines | no | fix now | |
| 46 | ZaberStageController `blacs_tabs.py` order (2.6, KI) | 10 or more stages sort as text: 'device 1', 'device 10', 'device 2' | low | a lab with 10 stages | a sort key, 1 line | no | fix now | |
| 47 | ZaberStageController `utils.py` (2.6, KI) | a non-string connection raises AttributeError, not the message meant | low | a typo | catch it too, 1 line | no | fix now | |
| 48 | DummyIntermediateDevice `labscript_devices.py` (2.6, KI) | one with no outputs fails to compile | low: a test device | a test shot | write no table without outputs, 2 lines | no | fix now | |
| 49 | RFBlaster `blacs_workers.py` status (2.3 row 13, KI) | the board has no status readback, so the transition to manual does not wait for a secondary RFBlaster to end | unknown | RFBlaster secondaries | unknown without the board's protocol | board | as decided | step 2.3: "agree with fix now, verify first and defer groups"; this row is in defer, for the hardware |
| 50 | PhaseMatrixQuickSyn `blacs_workers.py` (2.3 row 22, KI) | three buttons do nothing, and the output is switched on without the `\r` and regardless of the shot's gate, so `QuickSynDDS.disable()` has no effect | medium, rare device | QuickSyn labs | as `KNOWN_ISSUES.md` says | no | as decided | step 2.3: left, by Ian's decision |
| 51 | FlyCapture2Camera `blacs_workers.py` `_send_format7_config` (2.3 row 22, KI) | Format7 settings that fail validation are skipped silently | low | FlyCapture2 labs | as `KNOWN_ISSUES.md` says | no | as decided | step 2.3: left, by Ian's decision |
| 52 | runviewer, below a device with no parser (2.6, KI) | nothing below a device without a runviewer parser is drawn | low | a secondary triggered from a DummyIntermediateDevice | a parser for DummyIntermediateDevice here, or runviewer loading the children regardless (runviewer) | no | defer | |
| 53 | labscript-utils' runviewer parser lookup (2.2.1, Codex's findings on Phase A) | a device registered with no runviewer parser raises ValueError, where the lookup could treat it as none | low | runviewer, for such a device | in labscript-utils | no | as decided | step 2.2.1, Ian's decisions on Codex's Phase A findings: left to that owner |
| 54 | labscript's `example.py`, and labscript-utils (2.2.1, seen) | the example puts `example3`, based on `'Vpp'`, on a PulseBlaster DDS amplitude, so its compile and BLACS warn | low: a warning | anyone running labscript's example | an `'Arb'` example class in labscript-utils, for the example to use | no | defer: brief those owners | |
| 55 | blacs `progress_bar/__init__.py:228` (seen in the runviewer model's work) | it sorts `/waits` again, which labscript writes sorted | none: redundant | nobody | blacs' owner; recorded in the meta repo's `issues/seen_while_mapping.md` | no | defer: blacs' owner | |
| 56 | CiceroOpalKellyXEM3001 `labscript_devices.py` reps (2.6, KI) | 2**32 or more ticks at one period are cut short, and a 3- or 4-tick wait can merge | low: unphysical | none in practice | cap the merge, 2 lines | no | defer | |
| 57 | CiceroOpalKellyXEM3001 `blacs_tabs.py` child lookup (2.6, KI) | it searches the wait monitor's pseudoclock | none now | nobody, as the tab makes no outputs | look under the right child, 1 line | no | defer | |
| 58 | PineBlaster `blacs_tabs.py` `'-'` (2.6, KI) | an unknown port returns `'-'` | none now | nobody | return `None`, 1 line | no | defer | |
| 59 | `docs/source/devices/pylon.rst` (2.6, KI) | the usage line has a positional serial the script refuses | low: docs | Basler users | `-sn SERIAL`, 1 line | no | fix now | |
| 60 | `docs/source/devices/alazartechboard.rst` (2.6, KI) | says atsapi.py is installed separately | low: docs | Alazar users | say it ships here, 1 line | no | fix now | |
| 61 | PylonCamera `testing/ExposureTiming.py` (2.6, KI) | the last print calls a start-to-start time end-to-start | low: a script | Basler users timing a camera | label both cases, 1 line | no | fix now | |
| 62 | RFBlaster `blacs_workers.py` retry (2.6, dead code) | no error that requests raises reaches the retry, so `restart_kloned`, `retries` and the attempt counters never run; `finalfreq`, `finalamp` and `finalphase` are unused | none | nobody | delete, about 30 lines | no | fix now | |
| 63 | CiceroOpalKellyXEM3001 `blacs_workers.py` (2.6, dead code) | `ReadU32` and `current_value` are unused | none | nobody | delete, about 7 lines | no | fix now | |
| 64 | PhaseMatrixQuickSyn `blacs_workers.py` (2.6, dead code) | the worker's `self.final_values` is unused | none | nobody | delete, 1 line | no | fix now | |
| 65 | LightCrafterDMD `blacs_tabs.py` (2.6, dead code) | `slm_properties` is passed to the worker, which does not read it | none | nobody | delete, 1 line | no | fix now | |
| 66 | AlazarTechBoard `blacs_workers.py`, `labscript_devices.py` (2.6, dead code) | `start` and `triggerDelay_samples` are unused, and `add_device` only calls `Device.add_device` | none | nobody | delete, about 6 lines | no | fix now | |
| 67 | FunctionRunner `blacs_workers.py` (2.6, dead code) | the `monotonic` import is unused | none | nobody | delete, 1 line | no | fix now | |
| 68 | NI_DAQmx `labscript_devices.py:361` (2.6, dead code) | the last `clock_terminal` check is unreachable: the two before it raise first | none | nobody | delete, 4 lines | no | fix now | |
| 69 | PineBlaster `clock_type`, PhaseMatrixQuickSyn `generation` (2.6, dead code) | public class attributes, upstream's, that nothing in the suite reads | none | a lab's own code, if any reads them | delete, 3 lines, on Ian's word | no | keep | step 2.4's rule, a public name is kept unless Ian says otherwise: "approve as proposed" |
| 70 | Unused public names (2.4 rows 3 to 6, 8, 10, 13, 14, 16, 17) | kept: the old-style camera route, `expose`'s old order, the SDK wrappers' unused names, `ImageSet.set_array`, `hold_phase`, TekScope's three methods, the documented scripts and `test_device` | none | lab code | none | no | as decided | step 2.4: "approve as proposed" |
| 71 | A core `DirectOutputs` class (2.2.1, D1) | not built: PulseBlaster, RFBlaster and PrawnDO share only the empty shell | none | nobody | none | no | as decided | step 2.2.1: the plan Ian approved, "move forward with the work", drops D1 and D2 |
| 72 | A clock-table writer in `PseudoclockDevice` (2.2.1, D2) | not built: the `[period, reps]` table is PineBlaster's format, which the dummy copies, so they stay siblings; four devices share only the equal-period merge loop | none | nobody | that loop as a small labscript helper, if wanted | no | as decided | as row 71 |
| 73 | Improvement a, the values a manual program took (2.5 row 8) | NI_DAQmx's and PulseBlaster's `program_manual` return nothing, so BLACS shows the values asked for, not those the hardware took | none: an improvement | Ian's NI and PulseBlaster labs | larger than a small change | no | as decided | step 2.5, moved to Possible improvements: "I approve all else" |
| 74 | Improvement b, connections checked when they are made (2.3 row 18, 2.5 row 17) | PulseBlaster checks its connections only at compile, and AlazarTechBoard not at all | none: an improvement | a misconnected script | checks in `add_device` | no | as decided | step 2.3, in defer, then as row 73 |
| 75 | Improvement f, waits close together (2.5 rows 8, 12) | a pseudoclock tab polls every 100 ms, so a Cicero fails a shot whose two waits both pass between polls | none: an improvement | a Cicero lab with close waits | larger than a small change | board | as decided | as row 73 |
| 76 | Improvement g, reporting a worker's failure (2.5 row 8) | a pseudoclock tab fails a shot by faking a restart of the device | none: an improvement | nobody sees it | a BLACS call (blacs) | no | as decided | as row 73 |
| 77 | Improvement h, front-panel bit packing (2.2, 2.2.1 card 9) | NI_DAQmx's worker and parser, and PrawnDO's worker, each pack a port's lines | none: an improvement | nobody sees it | one helper beside labscript's `bitfield` | no | as decided | step 2.2: deferred, near-duplicates left for now, not rejected; step 2.2.1: card 9 left, by Ian's decision; then as row 73 |
| 78 | Improvement c, measured delays (2.5 row 8) | PineBlaster's, RFBlaster's and Cicero's delays are estimates | none: an improvement | those boards' labs | measure each on a board | board | as decided | as row 73 |
| 79 | Improvement d, Andor acquisitions (2.5 row 8) | the worker waits for the camera to go idle, then aborts on a timeout | none: an improvement | Andor labs | end the wait on the expected frames | camera | as decided | as row 73 |
| 80 | Improvement e, TekScope settings per shot (2.5 row 8) | the acquisition mode, stop condition and channels are fixed in the worker | none: an improvement | TekScope labs | take them from the shot file | scope | as decided | as row 73 |
| 81 | Improvement i, TekScope's module name (2.3 row 20, 2.5 row 17) | `TekScope/TekScope.py` shadows the class once a worker imports it | none: an improvement | a process importing both | rename the module, about 3 lines | no | as decided | step 2.3, in defer, then as row 73 |
| 82 | Improvement j, test_device's keyword (2.3 row 21, 2.5 row 17) | `DoSomething` is CamelCase | none: an improvement | nobody | `do_something`, the old name a legacy keyword | no | as decided | as row 81 |

In all, 82 rows:
- fix now 42: 1, 4 to 6, 8, 9, 13 to 18, 20 to 25, 27, 28, 30 to 34, 37, 43
  to 48, 59 to 68;
- verify first 5: 11, 26, 35, 36 and 40;
- defer 10: 29 (until the lyse owner answers), 38, 39, 41, 52, 54 to 58;
- already decided 25: 2, 3, 7, 10, 12, 19, 42, 49 to 51, 53, 69 to 82.

On the master's proposal for 38 and 39, fix now is 44 and defer 8.

### Built

The 35 simple rows (Ian: "have all of the simple no-brainers fixed and checked
off. I will consider the remaining issues with actual repercussions later this
evening"): 1, 4, 9, 13, 14, 16 to 18, 20, 22, 23, 25, 27, 30 to 34, 37, 43 to 48
and 59 to 68. One commit a device, naming its rows; each fixed row's
`KNOWN_ISSUES.md` line goes, 28 of them. With the one Fable's review added, 25
remain.

| Rows | Commit |
| --- | --- |
| 1, 9, 68 | `0e17cfe`, and for 1 `75df455`, `d46f7b6`, `e9392fd`, `8879e24`, NI_DAQmx |
| 4 | `462bc30` NovaTechDDS9M |
| 13, 25, 32, 60, 66 | `2279ec9` AlazarTechBoard |
| 14, 33, 37 | `50bc1d8` AndorSolis |
| 16, 17, 18 | `7ab4679`, and for 16 `db069af`, `f1b6a4d`, PrawnDO |
| 20, 44 | `66645fa` TekScope |
| 22, 23, 30, 43 | `9eaf4f6` TriggerableCamera |
| 27, 65 | `5ed79fa` LightCrafterDMD |
| 31, 62 | `d16c7f1` RFBlaster |
| 34, 45, 67 | `6a940b2` FunctionRunner |
| 46, 47 | `27210f5` ZaberStageController |
| 48 | `4f1b717`, `e7d10e0` DummyIntermediateDevice |
| 59, 61 | `aa4dcfd` PylonCamera |
| 63 | `35dac4b` CiceroOpalKellyXEM3001 |
| 64 | `b5b9901` PhaseMatrixQuickSyn |

- Where a fix went beyond its row's line:
  - 20: the time axis had half the points at twice the spacing, to match the
    old 4-byte read; it now has one per point, and is unchanged for 8-bit.
  - 4: only the four lines used are checked, so a NovaTech that sends no
    fifth line still works.
  - 25: any `channels` without channel A is refused; 32: rate 0 is refused only
    with the external clock, as the internal clock takes its nearest rate.
  - 62: RFBlaster's request no longer loops; its errors were never caught, so
    a request raises as it did, and no retry remains (Ian, step 2.3: "do not
    have RFBlaster retry").
- Each fault's fix was probed, with fakes for the hardware, and most also
  against `4938a2a`, where the fault shows; RFBlaster's requests behave as they
  did. The removals and text changes had no probe.
- Shots, against `4938a2a`: every test shot is identical or fails the same
  way, but for row 31's intended refusal: `RFBlaster_shot1` and
  `RFBlaster_shot3` make an RFBlaster the master, which BLACS cannot run, and
  `RFBlaster_err1` has no trigger device either, so it now stops at that.
  Traces are identical; the docs build adds no warning; the suite passes, and
  every `Parameters` block names its signature's arguments.
- Codex's three findings, all fixed:
  - 16: the cache was written only once every row was set, so a failure
    part-way left it naming rows the board no longer had. It is forgotten while
    programming, and kept again only once `run` succeeds, so any failure forces
    a full reload.
  - 1: one read could not take all that a late callback left, and an
    untriggered task's empty read counted as data. `stop_task` now reads the
    samples pending when it is called, a finite count, at most a `read_array`
    at a time; DAQmx may refuse a read larger than its array. Counting again
    each pass never ended while manual mode's clock ran.
- Fable's review of the re-check's fixes, before Codex:
  - 1: a DAQmx error in that read, such as a buffer overflow, left the task
    set, so manual mode never restarted; the task is now stopped and cleared
    whatever the read does. The tail is read only for a shot, since manual
    mode's is discarded.
  - 1: whether DAQmx waits for a running callback, which waits on `tasklock`,
    before `StopTask` or `ClearTask` returns is not in NI's documentation; a
    `KNOWN_ISSUES.md` line, as upstream has the same structure.
  - 16: the firmware keeps the program through an abort, so the cache stays
    valid. In `prawn_do.c` (upstream `ec7d967`), `abt` only requests the abort
    (`:332-336`), and its handling (`:234-237`) stops the DMA and the state
    machine (`stop_sm`, `:128-132`); only `cls`, `set`, `add` and `adm` change
    the program.
  - 16: a shorter program leaves the old rows past its end, which never run:
    `prawn_do.pio` ends at the first two rows of reps 0 (`wait_end`), and
    `set` of such a row cuts the program there (`prawn_do.c:416-418`).
- Ian, on a task left by a failed stop: "This is a major issue that acutally
  requires us to restart USB based hardware and reboot the computer with PCI
  hardware ... This must be fixed." Every NI_DAQmx teardown now clears every
  task whatever raises first, takes each off the worker before, and still
  raises the error. Each leaked a task before:
  - the output worker's `stop_tasks`, when AO's `StopTask` raised, kept both
    tasks and never stopped DO;
  - its `transition_to_manual` and abort, when an output had not finished,
    dropped both tasks uncleared;
  - the acquisition worker's `stop_task`, when `StopTask` raised, kept its task;
  - the wait monitor's `stop_tasks`, when its thread failed or would not stop,
    or its `StopTask` raised, kept both.

  `clear_tasks` clears them in the three teardowns of two tasks.
  - Checked at `8879e24` as above, with the same three RFBlaster shots alone
    differing.
- Lab checks, on Development:
  - row 1: an NI shot's analog input keeps the samples after its last full
    chunk, all of them when a callback is late, and those reads raise no buffer
    error; stopping a shot's acquisition while a callback runs does not hang;
    and after a failed stop every task is released, so the next shot runs
    without a driver reset;
  - row 20: a TekScope shot with `int16`, its points and time axis.
