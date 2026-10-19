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
- Step 2.2's table and Ian's decisions, the two bugs fixed on his word
  (`719fe26`, `d0c300e`), and step 2.2.1's Phase A: `02b4a52..` the commit that
  records this line. Phase A alone is `93cdc48..` the same commit.
- Codex's findings on Phase A, and Ian's decisions on them: `4a74e3e..` the commit
  that records this line.
- Step 2.2.1's Phase B: `25c2f22..` the commit that records this line, coupled
  with labscript `2e47a79`, `608013c`, `f9d64b9`, `1d5ea89`, `58c5445` and `1988218`.
  - **Outcome:** each package gives its old module's own names, and the device
    classes it imported, as the same objects. Its labscript-side names make up
    `__all__`. The incidental imports are dropped, by Ian's decision. The names
    are listed under step 2.2.1.
  - The package check skips only AlazarTechBoard's missing library.
- Codex's findings on Phase B: `e0243fa..` the commit that records this line,
  coupled with labscript `ab2ffae`.
  - The ValueError for a device with no runviewer parser needs labscript-utils'
    lookup to treat a `None` registration as none, so it is left to that owner.
  - **Outcome:** Codex's re-check found two points. Fixed in 02b4a52: an error
    from PrawnDO's abort after a timeout, such as a `SerialException`, is logged
    and the `TimeoutError` raised, where it used to replace it. Left as is (Ian):
    a board that confirms its abort or end of shot after the deadline counts as
    done, since the hardware did finish and each poll is bounded by the serial
    read timeout.

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
| 5 | DummyPseudoclock's `generate_code` (32 lines) and parser (45) copy PineBlaster's, pulse-program format included | Yes: labscript's tests and labs' test setups use the dummy | DummyPseudoclock's package, whose imports are light. `PineBlaster` and its `RunviewerClass` subclass the dummy's classes, keeping their names, their own `__init__`, `max_instructions` and the parser's `trigger_delay`. Not the reverse: `PineBlaster.py` imports BLACS at module level, so the dummy would pull BLACS into every compile | about −75 | PineBlaster compiles and runviewer; no change to the dummy | open: step 2.2.1 |
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
- **The reviews' fixes** (`f9c09d9`, `a1afd1f`, `b58f9ed`).
- **Card 10** (`82c42cc`): `TriggerableCameraInterface` composes
  `set_attributes`, which keeps the `attr_dict` keyword, and `snap`, and
  `DictAttributesMixin` holds dict attributes.

Merge coupling: this range must merge with labscript `2e47a79`, `608013c`,
`f9d64b9`, `1d5ea89`, `58c5445`, `1988218` and `ab2ffae`.

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
- `CiceroOpalKellyXEM3001`: `__all__` CiceroOpalKellyXEM3001; by name CiceroOpalKellyXEM3001Tab, int_to_bytes, bits_to_int, add_instruction_to_bytearray, CiceroOpalKellyXEM3001Worker, RunviewerClass; dropped Device, PseudoclockDevice, Pseudoclock, ClockLine, LabscriptError, set_passed_properties, compiler, IntermediateDevice, WaitMonitor, DigitalOut, runviewer_parser, BLACS_tab, BLACS_worker, labscript_device, np, labscript_utils, h5py, ensure_str, CiceroOpalKellyXEM3001Pseudoclock, CiceroOpalKellyXEM3001DummyPseudoclock, CiceroOpalKellyXEM3001DummyClockLine, CiceroOpalKellyXEM3001DummyIntermediateDevice, define_state, Tab, PseudoclockWorker, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab.
- `DummyIntermediateDevice`: `__all__` DummyIntermediateDevice; by name DummyIntermediateDeviceTab, DummyIntermediateDeviceWorker; dropped labscript_device, BLACS_tab, BLACS_worker, IntermediateDevice, DigitalOut, AnalogOut, compiler, np, DeviceTab, Worker.
- `LightCrafterDMD`: `__all__` arr_to_bmp, WIDTH, HEIGHT, BLANK_BMP, ImageSet, LightCrafterDMD; by name LightCrafterTab, LightCrafterWorker; dropped base64, os, struct, time, PIL, BytesIO, labscript_utils, h5py, labscript_device, BLACS_tab, BLACS_worker, runviewer_parser, Device, IntermediateDevice, LabscriptError, Output, compiler, np, Worker, define_state, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab, Signal.
- `NovaTechDDS9M`: `__all__` bauds, NovaTechDDS9M; by name NovatechDDS9MTab, NovatechDDS9mWorker, RunviewerClass; dropped runviewer_parser, BLACS_tab, IntermediateDevice, DDS, StaticDDS, Device, compiler, LabscriptError, set_passed_properties, NovaTechDDS9mFreqConversion, NovaTechDDS9mAmpConversion, np, labscript_utils, h5py, time, Worker, define_state, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab.
- `PhaseMatrixQuickSyn`: `__all__` QuickSynDDS, PhaseMatrixQuickSyn; by name PhaseMatrixQuickSynTab, QuickSynWorker; dropped np, BLACS_tab, runviewer_parser, Device, StaticDDS, StaticAnalogQuantity, StaticDigitalOut, compiler, LabscriptError, set_passed_properties, labscript_utils, Worker, define_state, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab, UiLoader, os.
- `PineBlaster`: `__all__` PineBlaster; by name PineblasterTab, PineblasterWorker, RunviewerClass; dropped PseudoclockDevice, Pseudoclock, ClockLine, compiler, LabscriptError, set_passed_properties, runviewer_parser, BLACS_tab, np, labscript_utils, h5py, PineBlasterPseudoclock, define_state, PseudoclockWorker, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab.
- `PulseBlaster`: `__all__` PulseBlasterDDS, PulseBlasterBase, DDSPulseBlasterMixin, PulseBlaster, PulseBlasterDirectOutputs; by name PulseBlasterBaseTab, DDSPulseBlasterTabMixin, PulseBlasterTab, PulseBlasterBaseWorker, DDSPulseBlasterWorkerMixin, PulseblasterWorker, profiles, profile, start_profile, stop_profile, PulseBlasterBaseParser, PulseBlasterParser (new: PulseBlasterBase, DDSPulseBlasterMixin, PulseBlasterBaseTab, DDSPulseBlasterTabMixin, PulseBlasterBaseWorker, DDSPulseBlasterWorkerMixin, PulseBlasterBaseParser); dropped BLACS_tab, runviewer_parser, dedent, Device, PseudoclockDevice, Pseudoclock, ClockLine, IntermediateDevice, DigitalQuantity, DigitalOut, DDS, DDSQuantity, LabscriptError, set_passed_properties, compiler, np, labscript_utils, h5py, time, define_state, PseudoclockWorker, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab, UiLoader, qtutils, os, QtCore, QtGui.
- `PulseBlaster_No_DDS`: `__all__` PulseBlaster, PulseBlaster_No_DDS; by name Pulseblaster_No_DDS_Tab, PulseblasterNoDDSWorker, PulseBlaster_No_DDS_Parser, PulseBlasterParser; dropped BLACS_tab, runviewer_parser, PseudoclockDevice, compiler, LabscriptError, np, define_state, PseudoclockWorker, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab, UiLoader, qtutils, os, QtCore, QtGui, QtWidgets.
- `PulseBlasterESRPro200`: `__all__` PulseBlaster_No_DDS, PulseBlasterESRPro200; by name Pulseblaster_No_DDS_Tab, pulseblasteresrpro200, PulseblasterNoDDSWorker, PulseblasterESRPro200Worker, PulseBlaster_No_DDS_Parser, PulseblasterESRPro200Parser; dropped BLACS_tab, runviewer_parser.
- `PulseBlasterESRPro500`: `__all__` PulseBlaster_No_DDS, PulseBlasterESRPro500; by name Pulseblaster_No_DDS_Tab, pulseblasteresrpro500, PulseblasterNoDDSWorker, PulseblasterESRPro500Worker, PulseblasterESRPro500Parser (new: PulseblasterESRPro500Parser); dropped BLACS_tab, runviewer_parser.
- `PulseBlasterUSB`: `__all__` PulseBlaster_No_DDS, PulseBlasterUSB; by name Pulseblaster_No_DDS_Tab, PulseblasterUSBTab, PulseblasterNoDDSWorker, PulseblasterUSBWorker, PulseBlaster_No_DDS_Parser, PulseBlasterUSBParser; dropped BLACS_tab, runviewer_parser.
- `PulseBlaster_SP2_24_100_32k`: `__all__` PulseBlaster_No_DDS, PulseBlaster_SP2_24_100_32k; by name Pulseblaster_No_DDS_Tab, PulseBlaster_SP2_24_100_32k_Tab, PulseblasterNoDDSWorker, PulseBlaster_SP2_24_100_32k_Worker, PulseBlaster_SP2_24_100_32k_Parser, PulseBlasterParser; dropped BLACS_tab, runviewer_parser.
- `RFBlaster`: `__all__` RFBlaster, RFBlasterDirectOutputs; by name RFBlasterTab, MultiPartForm, RFBlasterWorker; dropped os, PseudoclockDevice, Pseudoclock, ClockLine, IntermediateDevice, DDS, compiler, startupinfo, LabscriptError, set_passed_properties, np, BLACS_tab, runviewer_parser, setup_logging, RFBlasterPseudoclock, define_state, PseudoclockWorker, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED, DeviceTab.
- `test_device`: `__all__` test_device; by name Tab, Worker, Parser; dropped BLACS_tab, runviewer_parser, Device, LabscriptError, set_passed_properties.
