# labscript-devices deep pass

A planning document for the code-health campaign in labscript-devices
(`issues/code_health_campaign.md` in the meta repo): the test contract, then the
deep pass's candidates for Ian's review, one section per step. It is deleted
when the pass is done. Nothing is removed until Ian has reviewed each entry.

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
- Tests: 38, after step 1 removed three with their behaviours (entries 2, 4 and 7).
- Marks: keep 25, rename 1, trim 4, cut 8.

### A decision the list depends on

The four `ContractTests` check how the vendor camera classes are written
(which methods each defines, what it inherits), not what they do. They are cut
under rule 13 (attribute names). They are also the only check that runs on the
vendor classes, whose SDKs are absent here, so a refactor that dropped, say,
`Pylon_Camera.snap` would pass the suite. If Ian keeps that guard, the first
of the four stays and the other three still go.

### tests/test_camera_interface.py

- `ContractTests.test_every_camera_writes_the_members_only_it_can`: each of the six cameras defines `set_attributes`, `snap`, `grab`, `configure_acquisition`, `stop_acquisition` and `close`. **cut** (structure), see above.
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
- `NI_DAQmxTests.test_the_acquisitions_table_is_written_as_earlier_versions_wrote_it`: the acquisitions table's strings are fixed-length bytes, as readers expect. **rename** → `test_the_acquisitions_table_stores_its_strings_as_bytes`.

### tests/test_triggerable_camera_tab.py

- `CopyAttributesTests.test_copy_puts_the_attributes_on_the_clipboard`: the attributes dialog's Copy button copies its text. **keep**.

### tests/test_dummy_camera.py

- `AbsorptionImageTests.test_one_image_is_compiled_for_each_exposure`: one uint16 image per exposure, at the sensor's size. **keep**.
- `AbsorptionImageTests.test_the_images_are_stored_in_the_order_the_triggers_arrive`: images are stored in time order, not `expose()` order. **keep**.
- `AbsorptionImageTests.test_the_images_follow_a_global_the_function_uses`: a shot global changes the image. **keep**.
- `AbsorptionImageTests.test_the_frames_of_one_absorption_image_agree_with_each_other`: **cut** (duplicate): M3 failed it together with ten others, and its optical-density check repeats the lyse test's.
- `CoordinateGridTests.test_the_grid_is_the_object_plane_in_micrometres`: the grid is pixels scaled by `pixel_size/magnification`. **keep**.
- `DefaultImageTests.test_an_exposure_with_no_function_gets_a_blank_frame`: an exposure with no function stores zeros. **keep**.
- `RejectedFunctionTests.test_a_function_returning_a_nan_says_so`: a non-finite image stops the compile. **trim**. Step 2.1, entry 1.
- `SensorSizeTests.test_a_camera_never_told_its_size_says_so_before_it_compiles`: a camera without `Width` and `Height` stops before the shot file is written to. **trim**.
- `SavedImageTests.test_the_images_are_saved_where_a_real_camera_saves_them`: frames land in `images/<camera>/<name>/<frametype>`, uint16, with the save path's attributes. **keep**.
- `SavedImageTests.test_each_frame_is_saved_under_the_exposure_that_asked_for_it`: each saved frame is the compiled one for its exposure. **keep**.
- `SavedImageTests.test_the_saved_images_are_marked_as_not_real_data`: the saved group carries `NOT_REAL_DATA`. **keep**.
- `SavedImageTests.test_the_datasets_declare_themselves_to_be_images`: saved frames carry `CLASS=IMAGE`, as every camera's do. **keep**.
- `SavedImageTests.test_an_analysis_script_reads_them_as_it_reads_any_camera_s`: lyse's `get_images` reads them back. **keep**.
- `SaturationTests.test_a_pixel_saturates_at_the_depth_pixelformat_gives`: counts clip to the `PixelFormat` depth. **keep**. Step 2.1, entry 3.
- `WrongShapeTests.test_a_function_returning_the_wrong_shape_says_which_exposure`: an image of the wrong shape stops the compile. **trim**. Step 2.1, entry 8.
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
