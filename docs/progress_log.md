# H.A.L.O. Progress Log

## Continuation checkpoint

**Date:** 2026-09-05
**Repository:** `C:\Users\Parth\Desktop\HAR_for_BAS`
**Active UI:** React dashboard at `http://127.0.0.1:5767`
**Current branch information:** `main`.

## Verified before this continuation

- Existing project handover reports 81 pytest tests passing.
- Ruff lint and format checks were clean.
- React dashboard and web smoke test were passing.
- CUDA inference was previously verified as `cuda:0` on the RTX 5050.
- The supplied red/blue sorting MP4 was previously accepted by the demo sequence tracker.
- Existing training CLIs are present: `prepare-yolo-dataset`, `annotate-yolo`, `train-yolo`, and
  `export-onnx`.
- The old PySide6 UI is absent; React is the active UI.
- The current generic evidence evaluator still reports `object_state` as not implemented.
- The current color sequence tracker contains red/blue demo-specific logic and must not become the
  generic activity path.

## Decisions recorded from the user

- Training data and logs stay on the laptop.
- Training Studio is part of the existing React dashboard.
- New procedures are created through a guided builder that generates validated YAML.
- Initial model organization is one package per activity.
- Initial camera assumption is one fixed calibrated view per activity.
- Annotation uses AI-assisted proposals with user review.
- Deliberate error examples should be included when available.
- Evaluation uses automatic session-level 70/20/10 splits.
- Live guidance is advisory only.
- Every trained package requires manual approval before Operations use.

## This checkpoint change

- Saved the complete approved plan in `docs/training_studio_plan.md`.
- Saved this continuation log so another agent can resume from the same decisions and boundaries.
- Next implementation work begins with schema/package contracts and registry plumbing.

## Checkpoint 1: package contracts and registry

**Status:** complete

- Added `halo/schema/activity_schema.py` with typed activity, take, timeline, bounding-box,
  visual annotation, dataset, job, evaluation, and model-release contracts.
- Added `halo/studio/registry.py` for local filesystem-backed activity packages.
- Added `activities_dir()` to the central path configuration.
- Added schema and registry tests.
- Verification: 11 targeted tests passed; full suite passed; Ruff lint and format checks passed.
- Next exact action: expose the registry through the existing web service and add the React Training
  Studio shell.

## Checkpoint 2: browser ingestion and ground truth

**Status:** complete

- Added local video ingestion with SHA-256 deduplication and OpenCV metadata probing.
- Added `/api/activities/<id>/takes` list and upload endpoints.
- Added CSV/Excel timeline parsing with seconds and `HH:MM:SS.mmm` support.
- Added duration and take-reference validation plus persistent `timeline.jsonl` records.
- Added `/api/activities/<id>/timeline` and downloadable CSV template endpoints.
- Added React drop zones for training videos and ground-truth timelines, including recording-session
  metadata.
- Added the `studio` extra for optional Excel parsing.
- Verification: full suite passed; 80 tests passed; Ruff lint and format checks passed; React build
  passed.
- Next exact action: add the guided procedure builder and validated plan persistence.

## Checkpoint 3: guided procedure builder

**Status:** complete

- Added validated activity-plan load/save services under `halo/studio/plans.py`.
- Added `/api/activities/<id>/plan` GET and PUT endpoints with package-path safety checks.
- Added the React procedure builder for objects, detector classes, evidence kinds, steps, and
  transitions.
- The builder persists a normal `ExperimentPlan`, so the existing generic FSM can consume it.
- Verification: full suite passed; 101 tests passed; Ruff lint and format checks passed; React build
  and web smoke passed.
- Next exact action: connect dataset preparation and CUDA-aware training to background jobs visible
  from the Training Studio.

## Checkpoint 4: dataset and training job plumbing

**Status:** complete

- Added laptop hardware discovery with CUDA device, GPU name, and VRAM reporting.
- Added activity-derived YOLO dataset configuration and dataset metadata persistence.
- Added background dataset-preparation and training job managers with durable job JSON records.
- Added laptop-safe, balanced, and quality presets; `auto` resolves to the available CUDA device or
  CPU fallback.
- Added Training Studio controls for dataset preparation, training start, job state, GPU, and VRAM.
- Added failure-path tests for missing videos and missing datasets.
- Verification: full suite passed; 103 tests passed; Ruff lint and format checks passed; React build
  passed.
- Next exact action: add assisted frame annotation, dataset-quality checks, and held-out evaluation.

## Checkpoint 5: annotation, quality, evaluation, and release gate

**Status:** complete

- Added browser keyframe endpoints and human visual-annotation persistence in
  `halo/studio/annotations.py`, including frame extraction, bounded box validation, and
  append-only `annotations.jsonl` storage.
- Added a React keyframe reviewer with take selection, configurable sampling, drag-box labels, and
  saved detector classes.
- Added dataset integrity reports in `halo/studio/quality.py` for split counts, missing labels,
  malformed YOLO rows, class coverage, and held-out split availability.
- Persisted the actual recording-session membership of each train, validation, and test split and
  surfaced warnings for prototype-only or limited-robustness datasets.
- Enforced session-level splitting in the normal activity preparation path so multiple videos from
  one recording session cannot cross train, validation, and test boundaries.
- Connected reviewed boxes to dataset preparation. Manual annotations replace auto-colour labels on
  corrected frames and extract an extra image when the reviewed frame was not sampled.
- Added held-out detector metrics and background evaluation jobs in `halo/studio/evaluation.py`.
  The quality gate runs before model inference and reports precision, recall, F1, TP, FP, FN, and a
  per-image failure gallery.
- Added a downloadable CSV evaluation report from the React dashboard.
- Added checksummed model candidates plus explicit reviewer approval and activation in
  `halo/studio/releases.py`; failed evaluations cannot create candidates.
- Added API routes and Training Studio controls for quality checks, held-out evaluation, reports,
  release candidates, and reviewer approval.
- Verification: full suite passed; 115 tests passed; Ruff lint and format checks passed; React build
  and web smoke passed.
- Known limitation: real model training/evaluation still requires the user’s labeled takes and a
  locally available Ultralytics model; no release is activated automatically.
- Follow-up completed in Checkpoint 6: package verification, release audit export, and approved
  activity selection.

## Checkpoint 6: approved activity selection in Operations

**Status:** complete

- Added `/api/operations/activities` and `/api/operations/select`.
- Operations lists only approved or active activity packages, verifies the release model file, and
  loads the package plan and model path together.
- Activity switching is rejected while capture is running; draft activities cannot enter Operations.
- Added the approved-activity selector to the React Operations header.
- Verification: full suite passed; 115 tests passed; Ruff lint and format checks passed; React build,
  `startup.bat test`, plan validation, and web smoke passed.
- Added package verification reports and a release audit CSV export.
- Known limitation: Operations still uses the existing generic capture runner and does not yet expose
  a package-specific failure-media viewer or full release audit UI.
- Next exact action: harden offline/replay coverage and extend generic package evidence adapters.

## Checkpoint 7: user-provided activity intake and cleanup

**Status:** cleared on user request

- A user-provided activity package was temporarily imported to verify the timeline and training
  workflow.
- The exact project-local package and all derived artifacts were removed: 529 files totaling
  44,749,709 bytes.
- The original source file outside the repository was left untouched; the user can import it again
  through Training Studio.
- No user-provided activity identifiers, timestamps, labels, or media remain in the project package.
- The reusable Training Studio implementation and the background-job race fix remain available.
- Next exact action: import the activity through `startup_training_studio.bat` and complete labeling
  when the user is ready.

## Checkpoint 8: fresh Training Studio annotation setup

**Status:** ready for visual annotation

- Recreated the activity package through the React Training Studio.
- Filled and validated the eight-step procedure, uploaded the training take, and assigned its
  recording session.
- Imported and validated all eight timestamp ground-truth records.
- Prepared the dataset and loaded full-video keyframes at 30-frame spacing, covering the complete
  take within the Studio keyframe limit.
- Selected the first detector class so the next action is drawing and saving object boxes.
- No model training was started; additional independent sessions and visual labels are still needed
  before the quality gate can pass.
- Next exact action: draw boxes for each visible detector class, then add independent takes before
  quality checking and CUDA training.

## Checkpoint 9: compact frame selector for annotation

**Status:** ready for visual annotation

- Replaced the horizontally scrolling keyframe strip in `web/src/TrainingStudio.jsx` with a frame
  dropdown in STEP 05.
- Frame options show ordinal position, timestamp, and saved-label count; selecting a frame clears
  any unsaved draft box and loads that frame directly.
- Updated the annotation layout in `web/src/styles.css` for the additional frame control and
  responsive two-column and single-column layouts.
- Set the default sampling interval to 30 frames so a typical 103-second take fits within the
  browser keyframe limit and remains fully selectable after refresh.
- Verified with `cmd /c startup.bat test` and `npm.cmd run build`.
- Next exact action: choose a frame from the dropdown, draw and save boxes for each visible class,
  then add independent takes before quality checking and CUDA training.

## Checkpoint 10: save-and-advance annotation shortcut

**Status:** ready for rapid visual annotation

- STEP 05 now saves the current human-drawn box and automatically loads the next keyframe.
- Pressing `Enter` while a draft box is present triggers the same save-and-advance action; form
  controls are excluded so normal text and select interaction remains safe.
- Starting a drag focuses the annotation image, so the shortcut works immediately after choosing a
  detector class from the label dropdown.
- Fixed frame-dropdown navigation by normalizing numeric frame IDs received from the backend to
  the string values emitted by HTML select controls; invalid selections no longer clear the editor.
- Fixed frame zero display by keeping its explicit `0` value instead of treating it as empty.
- The primary action is labeled `Save & next frame`, and the current frame status displays the
  keyboard shortcut.
- Verified with `cmd /c startup.bat test` and `npm.cmd run build`.
- Next exact action: use the dropdown or `Enter` shortcut to label the remaining frames and classes.

## Checkpoint 11: annotation reset with activity data preserved

**Status:** ready to annotate from the first frame

- Removed the prior visual box annotations from the concrete hardening activity package.
- Reset the Training Studio browser view without removing the activity package or its workflow data.
- Verified that the plan and uploaded take remain present, the recording-session count is 1, the
  timeline still contains 8 rows, and the annotation count is 0.
- Next exact action: select the activity, choose the first frame and detector class, draw the box,
  then press `Enter` to save and load the next frame.

## Checkpoint 12: frame dropdown navigation fix

**Status:** annotation navigation verified

- Fixed STEP 05 frame selection by matching HTML select string values to backend numeric frame IDs.
- Prevented invalid dropdown values from clearing the active annotation frame.
- Fixed the first frame's `0` value so it remains visibly selected instead of reverting to the
  placeholder.
- Verified live forward and backward navigation between `0.00s` and `1.20s`; existing annotations
  were preserved.
- Verified with `cmd /c startup.bat test` and `npm.cmd run build`.
- Next exact action: continue drawing and saving boxes with the dropdown or `Enter` shortcut.

## Checkpoint 14: annotation audit and dataset regeneration

**Status:** labels complete; multi-session data required

- Audited the saved visual annotations: 87 rows cover all 87 sampled keyframes from 0.00s through
  103.16s, with no missing frames, invalid image-bound boxes, or duplicate frame/class pairs.
- Confirmed all six detector classes are represented: glovebag 12, container 10, mixing_tool 7,
  syringe 27, laptop 22, and esa_logo 9.
- Regenerated `dataset_v1` so the 87 manual boxes are applied to the training dataset.
- Ran the quality gate. It correctly reports FIX because the activity currently has one recording
  session, producing 517 train images and no independent validation or test session.
- Next exact action: add at least two more independently recorded sessions, import them under unique
  recording-session IDs, annotate them, regenerate the dataset, and rerun the quality gate.

## Checkpoint 13: high-contrast annotation dropdown

**Status:** ready for visual annotation

- Updated STEP 05 frame dropdown styling with a dark native color scheme, bright readable option
  text, green selected options, and muted placeholder text.
- Preserved the existing frame-navigation, save-and-advance, and annotation data behavior.
- Verified with `cmd /c startup.bat test` and `npm.cmd run build`.
- Next exact action: continue drawing and saving boxes with the dropdown or `Enter` shortcut.

## Checkpoint 15: current single-session training result

**Status:** no trained model produced

- The current dataset contains the 87 audited manual annotations and 517 training images, but no
  validation or test images because the only recording session is assigned to train.
- Two laptop-safe training attempts resolved to `cuda:0` but stopped at 5% before any epochs because
  no validation images existed; video-level splits require at least three videos.
- No model artifact or evaluation report was produced; the quality gate remains FIX.
- A one-video prototype mode could be added later using frame-level splitting, but its metrics would
  be optimistic because frames from the same video would leak across splits.

## Next exact checkpoint

1. Harden offline/replay coverage for activity packages.
2. Add generic package evidence adapters for state, regions, hand actions, and pose labels.
3. Collect representative sessions, label them, train CUDA models, and evaluate on unseen sessions.
4. Add a full release audit view and failure-media viewer to Training Studio.
5. Run pytest, Ruff, React build, plan validation, and web smoke; append results here.

## Rules for future entries

Each implementation entry must record:

- date and checkpoint;
- files or subsystem changed;
- behavior completed;
- tests and commands run;
- known limitation or next exact action.

Do not mark a phase complete without the corresponding tests and smoke checks. Do not touch parked
3D HMR, Jetson, or learned temporal-head work without a new user decision.

## Checkpoint 16: MELFI activity intake

**Date:** 2026-09-06
**Status:** staged for manual visual annotation

- Created the separate activity `cold_stowage_melfi` so the MELFI video is not mixed with the
  Concrete Hardening procedure.
- Saved and validated a six-step procedure named `Cold Stowage and MELFI Overview`.
- Uploaded `studying cells in space.mp4` as take `studying_cells_in_space-c2dce8af89` under
  recording session `cold_stowage_melfi_session_001`.
- The Studio-probed metadata is 153.04 seconds, 25.0065 FPS, and 768x432. This supersedes the
  analyser's reported 29.97 FPS and 1920x1080.
- Imported six timeline records with the actual generated take ID. The supplied records cover
  0.0–105.0 seconds, leaving 48.04 seconds for manual review; no unsupported events were added.
- No visual annotations, dataset, training job, evaluation report, or release exists for this
  activity yet.
- The plan currently includes five physical detector candidates plus `nasa_logo`, `esa_logo`, and
  `title_card`. The quality gate will require labels for every plan class, so contextual classes
  must either be boxed consistently or removed from the detector plan before quality checking.

**Next exact action:** select `cold_stowage_melfi` in the React Studio, review the final 48.04 seconds
of the video and the six imported records, then draw and save boxes in STEP 05. Add independent
recording sessions before relying on validation, evaluation, or training metrics.

## Checkpoint 17: MELFI tail timeline completion

**Date:** 2026-09-06
**Status:** timeline complete; ready for visual annotation

- Inspected the previously uncovered 105.0–153.04-second interval from the actual MP4.
- Confirmed visible astronaut/computer activity from 105.0–143.04 seconds without assigning the
  surrounding unidentified ISS hardware a false MELFI label.
- Confirmed the ESA animation/end card from 143.04–153.04 seconds.
- Aligned the activity camera profile to the verified take at 25 FPS and 768x432.
- Added `astronaut_1` and `computer` object classes and `step_007`/`step_008` to the validated
  activity plan.
- Replaced the six-row timeline with eight records covering the full 0.0–153.04-second take.
- No visual boxes, dataset, training job, evaluation report, or release has been created.

**Next exact action:** draw and save the intended detector boxes in STEP 05. Add independent
recording sessions before trusting validation or training metrics.

## Checkpoint 18: collaborator handoff documentation

**Date:** 2026-09-08
**Status:** repository ready for external MELFI annotation

- Added `dataset_progress.md` with the activity inventory, exact MELFI take metadata, eight-step
  timeline, object classes, annotation rules, current Concrete Hardening limitations, and next
  actions.
- Added `training_guide.md` with clone/setup instructions, the six Studio stages, frame-boxing
  workflow, class-specific guidance, CUDA checks, quality-gate rules, and AI coding-tool rules.
- Updated `README.md` with the collaborator quick start and documentation index.
- Extended `HANDOVER.md` with the collaborator handoff and the current no-annotation/no-training
  state for MELFI.

**Next exact action:** the collaborator annotates `cold_stowage_melfi` in STEP 05, then runs the
quality gate before any training or evaluation claim.

## Checkpoint 19: Claude Code continuation handoff

**Date:** 2026-09-13
**Status:** detailed continuation brief saved

- Added `CLAUDE_CODE_HANDOVER.md` as the dated authoritative continuation brief.
- Documented Git state, setup and verification commands, architecture/data flow, package map,
  locked decisions, implemented features, parked phases, risks, exact MELFI and Concrete
  Hardening states, red/blue demo caveats, and the ordered next-work plan.
- Documented a mandatory progress-entry format so future annotation and training work can be
  handed across agents without relying on chat history.
- Linked the new brief from `README.md` and `HANDOVER.md`.

**Verification pending:** run the full `cmd /c startup.bat test` gate after this documentation
change, then commit and push the handoff.

## Checkpoint 20: MELFI visual annotation (agent-performed)

**Date:** 2026-09-13
**Agent:** Claude Code (owner's collaborator plan fell through; owner asked Claude Code to box
the take directly instead of waiting on a human annotator)

- Started the Training Studio server (`halo.web.server`, plan `experiments/red_blue_box/experiment_plan.yaml`,
  `models/yolo11n.pt`, device auto) and drove STEP 05 through the browser to draw and save human
  bounding boxes on `studying_cells_in_space-c2dce8af89` (`cold_stowage_melfi`).
- Sampled every 40 frames (96 keyframes across the 153.04 s take) and did a single visual pass
  across the whole timeline, boxing every instance of a plan class that was actually visible.
- **Important finding:** the footage from roughly 30 s to at least 94 s (spanning the plan's
  step_003–step_006 window, i.e. classes `melfi_freezer`, `dewar_compartment`, `sample_container`,
  `control_panel`) is not those objects. It is close-up footage of a piece of hardware explicitly
  labelled on-camera as a **"...ciences Glovebox (LSG)"** — a Life Sciences Glovebox. There is no
  defined plan class for this equipment, so per project rules (no inventing classes, no forcing
  ISS hardware into an unrelated label) this footage was left **unlabelled**.
  - `title_card` and `nasa_logo` were also never observed anywhere in the take; not labelled.
  - One `sample_container` box was added at 4.80 s (a white/soft case the interviewee is shown
    handling) — a genuine, if singular, match.
- Saved annotations by class after this pass: `interviewee` 11, `astronaut` 8, `computer` 3,
  `esa_logo` 7, `sample_container` 1. Total 30 human-reviewed boxes in
  `activities/cold_stowage_melfi/annotations.jsonl`.
- Ran `dataset/prepare` (sample_every=5) to create `datasets/dataset_v1` (766 train images, 0
  val, 0 test — only 1 recording session exists) and then `dataset/quality/check`.
- **Quality gate result: FAILED.** `passed: false`. Reported issues:
  - `classes have no labels: melfi_freezer, dewar_compartment, control_panel, nasa_logo, title_card`
  - `fewer than 3 independent recording sessions; validation is prototype-only`
  - validation and test splits are both empty (no independent session to populate them)
- No dataset re-preparation with a tighter `sample_every`, no training job, no evaluation was
  attempted — none of those are meaningful until the class-policy and multi-session gaps below
  are resolved.

**Open decisions for the owner (not resolved by this checkpoint):**
1. The plan needs revision for the 5 unmatched classes: either drop
   `melfi_freezer`/`dewar_compartment`/`sample_container`/`control_panel`/`title_card`/`nasa_logo`
   that don't appear in this take, add a `glovebox`-type class instead, or supply footage that
   actually contains the originally intended hardware.
2. The owner has said a second video will be provided; when it arrives, import it as a second
   take (ideally a second `recording_session`) under `cold_stowage_melfi` so the quality gate's
   session-count and split-population warnings can clear.

**Next exact action:** once the owner supplies another video, import it via the Studio (STEP 02),
re-run this same annotation sweep on it, decide the class-policy question above, then re-run
`dataset/prepare` and `dataset/quality/check` before ever attempting `dataset/training`.

## Checkpoint 21: multi-object annotation fix + denser MELFI pass

**Date:** 2026-09-13
**Agent:** Claude Code

- **Studio bug fix:** `web/src/TrainingStudio.jsx` STEP 05 previously forced `saveFrameAnnotation`
  to always advance to the next keyframe, so a frame with several visible objects could only ever
  get one saved box per visit (the owner noticed this while watching the annotation pass). Split
  the action: `saveFrameAnnotation(advance)` now takes a boolean; a new "Save label" button saves
  and stays on the same frame, "Save & next frame" (Shift+Enter) saves and advances as before, and
  a new "Next frame" button moves forward without requiring a save. Enter alone now saves-and-stays;
  Shift+Enter saves-and-advances. Rebuilt `web/dist` via `npm run build` and verified in-browser
  that two labels (`interviewee` + `esa_logo`) can now be saved on the same frame without losing
  either draft box.
- Used the fix to do a denser second pass over `cold_stowage_melfi` /
  `studying_cells_in_space-c2dce8af89`: filled in previously-skipped keyframes in the interviewee
  segment (frames 07-26, ~0-40s) and added a second `computer` label alongside `astronaut` on
  frames in the 105-110s window where both are visible in the same shot.
- Also discovered the glovebox-only footage starts earlier than first estimated: as early as
  ~30-41s (frame 27, 41.59s), not 65s. Still no matching plan class for it; left unlabelled per
  Checkpoint 20's reasoning.
- Annotation totals after this pass: `interviewee` 27, `astronaut` 9, `computer` 5, `esa_logo` 8,
  `sample_container` 1. Total 50 human-reviewed boxes (up from 30).
- Re-ran `dataset/prepare` (sample_every=5) and `dataset/quality/check`. **Still FAILS** for the
  same two reasons as Checkpoint 20: `melfi_freezer`, `dewar_compartment`, `control_panel`,
  `nasa_logo`, `title_card` still have zero labels (confirmed absent from the footage, not a
  labelling gap), and only 1 recording session exists so val/test splits are still empty. No
  training attempted.
- Owner said a second video is coming soon; when it arrives it should be annotated the same way
  and, ideally, treated as a second `recording_session` so the quality gate's session-count
  warning can clear.

**Next exact action:** import the owner's next video into `cold_stowage_melfi` (or a new activity,
per the owner's choice) as soon as it's provided, then repeat this annotation workflow on it.

## Checkpoint 22: new activity `foaming_fluid_science` (FOAM-C) created, researched, and annotated;
## MELFI missing-class issue resolved

**Date:** 2026-09-13
**Agent:** Claude Code

**Research before touching the video (per owner's explicit instruction):** the owner supplied
`stuying_fluid_sciences_in_space.mp4` with a description mentioning "Foaming Fluid Science." Before
building any plan or class list, searched the web and confirmed this is ESA/Airbus's **FOAM-C**
(Foam Coarsening) experiment, which runs in the **Fluid Science Laboratory (FSL)**, a rack-mounted
facility in the Columbus module, not the Microgravity Science Glovebox and not MELFI. FOAM-C
studies aqueous foam stability/coarsening in microgravity by loading Experiment Container
cartridges into the FSL's Central Experiment Module. Sources: esa.int FSL and FOAM-C pages,
Airbus 2020 press release, aeronomie.be B.USOC report.
Then extracted contact-sheet and per-second frames with ffmpeg and visually cross-checked the
research against the actual footage before finalizing classes (per the standing project rule:
verify visual content, never assume from a description alone).

**Activity created:** `foaming_fluid_science` -- manifest, `plan.yaml` (objects: `astronaut`,
`experiment_container`, `control_panel`, `computer`, `esa_logo`; 3 steps), take
`stuying_fluid_sciences_in_space-4fe26c68f3` (52.44 s, 25.02 fps, 768x432, session
`foaming_fluid_science_session_001`), and a timeline (3 records) -- all created via direct calls to
the running server's REST API (`POST /api/activities`, `PUT .../plan`, `POST .../takes`,
`POST .../timeline`) rather than only the Studio UI, to move faster.

**Studio-driven annotation:** sampled every 30 frames (~1.2 s spacing, 44 keyframes over 52.44 s)
and boxed every frame using the new multi-label-per-frame workflow from Checkpoint 21. Noted two
extra crew members appear briefly (one in a red shirt, one handling an unrelated "Frog #" cargo
box) -- boxed as `astronaut` where genuinely a person, did not invent a class for the unrelated
frog-experiment box. Final counts: `astronaut` 32, `esa_logo` 8, `control_panel` 3, `computer` 2,
`experiment_container` 1 (only one confident, if partially cropped, view of the white container was
found across all 44 keyframes -- true content limitation, not an annotation gap). Total 46 boxes.
Ran `dataset/prepare` + `dataset/quality/check`: **no missing-class warnings** -- every plan class
has at least one label. Only warning is the expected single-session one (needs a second
recording of this same experiment before validation/test splits can populate).

**MELFI missing-class issue resolved:** per the owner's explicit request, fixed
`cold_stowage_melfi/plan.yaml` (bumped to v0.2.0). Removed `melfi_freezer`, `dewar_compartment`,
and `control_panel` -- confirmed via the new video's research that these do not belong to this
footage either (FOAM-C is a distinct experiment/facility from Cold Stowage/MELFI, so the new
video could not and did not supply missing MELFI evidence). Replaced them with
`life_sciences_glovebox`, matching the on-screen "...ciences Glovebox (LSG)" label found during
Checkpoint 20's annotation pass. Renumbered the plan's steps (title_card -> interviewee ->
life_sciences_glovebox -> astronaut/computer -> esa_logo) and re-imported a corrected
`timeline.csv` that fixes the false "MELFI freezer" / "dewar compartment" / "control panel" claims
in the old timeline with an honest description of the glovebox footage. `title_card` and
`nasa_logo` were left untouched (out of the scope the owner asked for; still 0 labels, still
unresolved).

**Not done in this checkpoint:** no `life_sciences_glovebox` boxes were added yet to
`cold_stowage_melfi` (the class was only just created) -- that is real, valuable, available
annotation work for a future session. No training was attempted for either activity.

**Next exact action:** (1) box `life_sciences_glovebox` instances in the already-imported MELFI
take now that the class exists; (2) when the owner provides a second take of either experiment,
import and annotate it the same way, then re-run `dataset/prepare` + `quality/check` before ever
touching training.

## Checkpoint 23: MELFI glovebox annotated; found and worked around a stale-dataset bug;
## owner confirmed no more videos coming, training/finetuning gated on explicit owner approval

**Date:** 2026-09-13
**Agent:** Claude Code

**Owner decision (binding going forward):** no more source videos will be provided. If accuracy
from training/evaluation is later found to be low, more videos will be added then. **Training or
finetuning must not be started without the owner's explicit go-ahead each time** -- this
instruction was explicit and repeated; treat it as a hard gate, not a one-time reminder.

**MELFI glovebox annotation:** boxed `life_sciences_glovebox` across its full extent in
`studying_cells_in_space-c2dce8af89` (roughly 29-101s, sampled non-uniformly across that span for
diversity rather than every single keyframe) plus a few incidental extra `interviewee` boxes where
the glovebox rack was visible in the same wide shots. 19 `life_sciences_glovebox` boxes saved.
Activity total after this pass: 70 human-reviewed boxes (`interviewee` 28, `life_sciences_glovebox`
19, `astronaut` 9, `computer` 5, `esa_logo` 8, `sample_container` 1).

**Bug found and worked around (not a code fix, a data workaround):**
`halo/studio/datasets.py::ensure_dataset_config` only writes `datasets/dataset_v1/data.yaml`
the first time it is created (`if not data_path.is_file(): write`) and never regenerates it after
that, even when the activity's `plan.yaml` class list changes. This meant the Checkpoint 22 plan
fix (removing `melfi_freezer`/`dewar_compartment`/`control_panel`, adding
`life_sciences_glovebox`) never actually reached the prepared dataset -- the quality gate kept
reporting the old, deleted class names with zero labels and never listed
`life_sciences_glovebox` at all, even after re-running `dataset/prepare`. Diagnosed by inspecting
`data.yaml` and the label `.txt` files directly. Worked around by deleting
`activities/cold_stowage_melfi/datasets/dataset_v1/` entirely and re-running `dataset/prepare`,
which regenerated `data.yaml` from the current plan. Did **not** patch the underlying code --
that's a real latent bug (`ensure_dataset_config` should regenerate `data.yaml` whenever the plan's
class list no longer matches what's on disk, not only when the file is absent) worth fixing
properly in a future session, but out of scope for a data-annotation task the owner did not ask
for a code fix on.

**Quality gate after the fix:** `class_counts` now correctly shows `life_sciences_glovebox: 19`
and no longer references the removed MELFI classes. Only `classes have no labels: nasa_logo,
title_card` remains (out of the scope the owner asked to resolve; still untouched) plus the
expected single-session warning (still needs a second video, which per the owner will only be
added later if accuracy turns out low).

**Not done:** no training or evaluation was started -- explicitly withheld per the owner's
standing instruction. `foaming_fluid_science`'s single-session warning is likewise unresolved and,
per the owner, will stay that way unless training results warrant more footage.

**Next exact action:** wait for the owner's explicit instruction before running
`dataset/training` or any finetuning for either activity. If/when asked, use the `laptop_safe`
preset with `device: auto` first, verify `torch.cuda.is_available()` and the resolved device, and
report the quality gate / training completion / evaluation status separately rather than
conflating "job queued" with "model trained" (per AGENTS.md / CLAUDE_CODE_HANDOVER.md §17).

## Checkpoint 24: first successful detector training (MELFI) + self-test

**Date:** 2026-09-13/14
**Agent:** Claude Code
**Authorization:** owner explicitly approved training and asked Claude Code to test the model on one
of the training videos.

**Activity selection:** `cold_stowage_melfi` (70 human-verified boxes). `concrete_hardening_msl` was
rejected despite 87 boxes after a visual spot-check: 3 of 4 sampled `container` boxes are drawn on
the burned-in subtitle text, and `syringe` boxes cover the whole glovebag work area.
`foaming_fluid_science` has too few instances for 3 of its 5 classes.

**Why the Studio training button cannot work today:** `halo/studio/jobs.py::_run` calls
`scripts.train_yolo._validate_dataset(..., allow_missing_classes=False)`, which raises when the
val split is empty (always true with one recording session) and when any plan class has zero
labels (`nasa_logo`, `title_card`). This explains the earlier failed Concrete Hardening attempts.

**Dataset:** deleted and re-prepared `datasets/dataset_v1` with `sample_every=250`. Annotated frames
are extracted on demand by `_apply_visual_annotations`, so all 62 labelled frames are kept while
background drops to 12 images (74 total, 84% labelled; `sample_every=5` had given 766 images, 92%
unlabelled). Added `datasets/dataset_v1/data_selfcheck.yaml` with an absolute `path` (Ultralytics
resolves `path: .` against CWD) and `val: images/train`.

**Training (self-check run):** `python -m scripts.train_yolo data_selfcheck.yaml --model
models/yolo11n.pt --epochs 50 --imgsz 512 --batch 4 --workers 0 --patience 15 --device auto
--allow-missing-classes`. torch 2.11.0+cu128, CUDA:0 RTX 5050 Laptop GPU, ultralytics 8.4.138.
50 epochs in 3.4 min. Weights: `datasets/dataset_v1/runs/melfi_selfcheck_v1/weights/best.pt`.
Metrics on the training images (fit, not generalization): all mAP50 0.633 / mAP50-95 0.480;
interviewee 0.944, life_sciences_glovebox 0.852, astronaut 0.785, esa_logo 0.672, computer 0.544,
sample_container 0.000 (single example).

**Video self-test:** ran `best.pt` (conf 0.25) over all 3,826 frames of the MELFI take. Recall on the
70 human boxes at IoU>=0.5 with matching class: 62/70 = 88.6% (interviewee 27/28, astronaut 9/9,
esa_logo 7/8, computer 4/5, glovebox 15/19, sample_container 0/1). Visual montage of unlabelled
frames showed correct boxes for every trained class; glovebox confidence is low (~0.45) though
correctly placed, computer mean confidence 0.38.

**Held-out check (same video, unseen frames):** separate 50/12 labelled-frame split (seed 26174),
trained with identical settings (2.4 min). Held-out mAP50 0.693 / mAP50-95 0.466 on 12 frames, 13
boxes: interviewee 0.786 (6), life_sciences_glovebox 0.745 (2), astronaut 0.995 (1), esa_logo 0.245
(4, mostly the small corner watermark). The val set is tiny so per-class values are noisy, and
frames come from the same video, so this is an upper bound on performance on new footage.

**Status:** model trained; no held-out-session evaluation; no release candidate created. Scratch
artifacts (test script, annotated video, held-out split) live outside the repo.

**Next exact action:** await owner decision. Evidence suggests accuracy on new footage will be
lower than these numbers: the detector learned classes with 18+ examples well and failed on the
1-example class. Adding footage or more boxes for `computer`/`sample_container`, and deciding
whether to drop `nasa_logo`/`title_card`, are the highest-leverage options.

## Checkpoint 25: procedure-engine replay with the trained MELFI detector

**Date:** 2026-09-14
**Agent:** Claude Code
**Question from owner:** can the model alert the astronaut about whether a task is performed
correctly, and does it understand the experiment / decode next steps?

**Method:** scratch script (outside repo) fed every frame of the MELFI take into the real
`ProcedureEngine`: YOLO detections from `melfi_selfcheck_v1/best.pt` (conf 0.25) plus MediaPipe pose
from `halo.perception.PoseEstimator` (pose found on 68% of frames). Two engines ran on identical
perception: A = `plan.yaml` as-is; B = same plan without `step_001` (title_card). Replay wall time
140.4 s for 153.0 s of video, so the engine's wall-clock pause and cooldown timers ran at ~92% speed.

**Result A (plan as-is):** stuck on `step_001` for the entire video. `title_card` never appears and has
zero training labels. `SKIP_DETECTED` fired every ~5 s (27 alerts, limited only by `rate_limit_s`), plus
one `PAUSE_EXCEEDED`. In live use this would continuously and wrongly nag the astronaut.

**Result B (without title_card):** all four steps completed in order, each close to the corrected
human timeline:

| step | evidence | engine completed | human timeline start |
|---|---|---|---|
| step_002 | actor_visible (pose) | 0.16 s | 5.00 s (interviewee already on screen at 0 s) |
| step_003 | life_sciences_glovebox | 38.39 s | 40.00 s |
| step_004 | computer | 101.97 s | 100.00 s |
| step_005 | esa_logo | 143.16 s | 143.04 s |

Two `PAUSE_EXCEEDED` alerts (74.1 s, 132.7 s) were false alarms: the glovebox and astronaut segments
legitimately last ~60 s and ~43 s, but `pause_tolerance_s` is 30 s and pause detection only watches
for the current step's own completion evidence, not continued activity. `expected_duration_s`
is not used by the engine.

**What the system can and cannot do (verified from code, not assumed):**
- Can: announce step completion, detect later-step evidence appearing early (`SKIP_DETECTED`), and
  flag stalls (`PAUSE_EXCEEDED`), then speak them through the TTS worker.
- Cannot judge whether an action was done correctly. Evidence kinds are object/actor presence,
  region location, and a heuristic hand-object tag; `object_state` returns
  "not yet implemented (Phase 3)".
- Does not understand the experiment or infer next steps. "Next step" is the `next` list a human
  wrote in the YAML plan; the detector only reports which trained objects are visible.
- The MELFI video is an explanatory tour, not an executed procedure, so "correct execution" is not
  defined for it; this replay tests step tracking only.
- The replay used the training video, so it is an optimistic result.

**No repo code or plan changed in this checkpoint.**

**Next exact action:** owner decision. Candidate fixes: remove `title_card`/`nasa_logo` from the MELFI
plan, make pause tolerance respect each step's `expected_duration_s`, and — for genuine correctness
feedback — author a real procedure plan with object-state/location checks (requires the Phase 3
`object_state` work).

## Checkpoint 26: MELFI plan fixes, drag-and-drop experiment analysis, video-time engine

**Date:** 2026-09-14
**Agent:** Claude Code
**Owner request:** apply the two fixes from Checkpoint 25, then make it possible to drop a video on the
dashboard, have it recognise the experiment, and announce step completion/failure by itself.

**Fix 1 — MELFI plan (v0.3.0):** removed `step_001` (title card) and the `title_card`/`nasa_logo`
objects, which never appear in the take; `step_002` expected duration set to 40 s; timeline re-imported
(interviewee now 0–40 s). Saved through `PUT /api/activities/cold_stowage_melfi/plan`.

**Fix 2 — stall limit follows step duration (`halo/procedure/engine.py`):** after a step completes,
the pause tolerance while waiting for the next step is `max(pause_tolerance_s, 1.5 ×
completed.expected_duration_s)` (`PAUSE_DURATION_MARGIN`), because the completed step's activity is
still under way. New `use_media_time` option (off by default; on for uploaded files) drives pause and
cooldown timers from `PerceptionResult.ts_ms` instead of wall clock, since pose + hands + detection runs
slower than real time (~18–19 fps for 25 fps video). Media-time events carry `extra.video_time_s`;
skip alerts carry `extra.detected_step_id`.

**Recognition — first attempt rejected by evidence:** voting with each activity's trained detector
misclassified 2 of 3 real videos (Foaming and Concrete both → MELFI). Each detector is trained on one
video only, so the MELFI model labels any person "interviewee" and any enclosure "glovebox". Replaced
before merge.

**Recognition — shipped approach (`halo/studio/recognition.py`, schema
`halo/schema/recognition_schema.py`):** 24 frames of the uploaded video are embedded with the COCO
`models/yolo11n.pt` backbone (`YOLO.embed`, 256-d, no download) and compared with 32 frames from each
activity's stored takes. A frame votes for its most similar activity only if cosine similarity ≥ 0.90.
Recognised when the winner has ≥ 50% of frames and leads the runner-up by ≥ 25 points. Calibration of the
0.90 floor on real videos (frames with best similarity ≥ 0.90): MELFI 24/24, Foaming 22/24, Concrete
24/24, unrelated red/blue demo 0/24 (its maximum was 0.882). Results: MELFI → Cold Stowage 92%; Foaming →
Foaming 79%; Concrete → Concrete 96% (flagged "no trained detector", monitoring not started); red/blue
demo → not recognised. Limitation: every test video is also a stored reference take, and genuinely new
footage of the same experiment will score lower; the 0.90 floor has not been validated on such footage.

**Detectors:** trained a Foaming detector (same laptop-safe settings as MELFI, CUDA, 44 images / 40
labelled; train-set mAP50 0.549, `experiment_container` 0.0 from its single label) under the owner's
earlier training approval. Activity detectors now live at `activities/<id>/models/detector.pt` (MELFI
and Foaming). These `.pt` files are not covered by `.gitignore` (which only ignores root `models/`).

**Server (`halo/web/server.py`):** `POST /api/analyze` (raw video body, `X-Filename`) saves to
`logs/uploads/`, runs recognition, and on a match with a detector replaces the plan, sets the detector,
and starts `SessionRunner(..., filter_default_classes=False, use_media_time=True)`. Unrecognised uploads
are deleted. When a run ends, status carries `summary` (completed/missed steps, `source_finished`);
status also carries `analysis`. Fixed a latent bug: the runner always filtered detections to
`DEFAULT_TARGET_CLASSES` (cup, bottle, …), which would silently drop every custom-class detection; this
now applies only to the default COCO path (also turned off in the approved-release select path).

**Dashboard (`web/src/App.jsx`, `styles.css`):** drop a video anywhere on the Operations page (or use
"Choose video"); shows recognition verdict and per-activity scene scores; speaks recognition, step
completions, skip and stall alerts, and a final spoken summary via browser `speechSynthesis` (toggle
"Voice alerts"); lists completed ✓ / missed ✗ steps; events show video time. Upload errors are held in
separate state because the 0.7 s status poll overwrote them.

**End-to-end verification (real server, real videos):**
- Synthetic drop event in the browser: drop zone highlights, file POSTs to `/api/analyze`, invalid file
  is rejected and deleted.
- MELFI (`studying cells in space.mp4` from Downloads): recognised; CUDA; step_002 0.16 s, step_004
  101.97 s, step_005 143.16 s; **4 of 4 steps completed, zero PAUSE_EXCEEDED** (previously false alarms
  at 74.1 s and 132.7 s); spoken completions and "Analysis finished. 4 of 4 steps completed."
- Foaming (`stuying_fluid_sciences_in_space.mp4`): recognised; **0 of 3 completed**. `step_001`
  (experiment_container) never detected, so the strict step order never advanced; SKIP_DETECTED alerts
  showed step_002 and step_003 evidence being seen out of order, plus one PAUSE_EXCEEDED at 30 s. This is
  a data limitation (one container label), not a pipeline failure, but the spoken result is misleading.
- `cmd /c startup.bat test`: 155 passed, Ruff clean, formatting clean, demo plan valid, smoke test passed.

**Tests added:** `tests/test_recognition.py`, `tests/test_recognition_schema.py`, media-time and
duration-tolerance cases in `tests/test_procedure_engine.py`, analyze endpoint cases in
`tests/test_web.py`.

**Not committed.** No release candidate created; the analyze path bypasses release approval and is a
prototype.

**Next exact action:** owner decision on Foaming — add boxes for `experiment_container` (or drop/reorder
that step) so the plan can advance; decide whether steps seen out of order should still count as
completed in the summary; decide whether to gitignore `activities/*/models/*.pt`; commit when approved.

## Checkpoint 27 - 2026-09-14 - MELFI-only hardening and manual experiment picker

- Perception now runs pose / hand tracking only when the plan's evidence rules need them (`perception_needs`); MELFI needs pose only.
- Engine: a later step whose evidence persists for `skip_persistence_frames` frames now advances the procedure; the steps jumped over are recorded `skipped` (SKIP_DETECTED alert), and a skipped step seen afterwards is completed with an OUT_OF_ORDER alert. Alert rate limit and silence window follow video time in media-time mode. `EngineOutput.events` carries every event from a frame; the server records all of them.
- Run summary gains `skipped_steps` and `out_of_order_steps`; `missed_steps` now means never reached. Dashboard and speech updated.
- Operations page: "Experiment" picker next to "Choose video" (default "Auto-detect from video"). Choosing one sends `X-Activity-Id` to `/api/analyze`, which skips scene recognition and monitors that activity. New `GET /api/analyze/activities` lists activities with detector availability.
- Fixes: upload rejected for file type now drains the body (was a Windows connection-reset race in tests); upload is deleted if the chosen activity's plan fails to load.
- Baseline eval (old engine, pose+hands, 14-17 fps): original MELFI take 4/4 in order, no alerts. The cut variants were made at 40 s but the glovebox is already visible at 38.4 s, so they do not cleanly remove it; variants need re-cutting before they can test skip handling.

## Checkpoint 28 - 2026-09-14 - MELFI robustness: cached-perception replay and windowed skip confirmation

- Cached MELFI detector + pose output per frame once (pose only, no hands: 25.8 fps, real time for the 25 fps take) and replayed it through the engine with spliced scenarios, simulated detection dropout, scattered false positives and false-positive bursts.
- Detector timings on the take: glovebox 38.1-101.8 s, computer 101.8-132.5 s, esa_logo 143-153 s; single-frame false glovebox/esa_logo hits near 29.5 s and 38.2 s. The earlier variant videos were cut at 40 s and did not remove the glovebox.
- Consecutive-frame skip confirmation was either fooled by a 0.6 s false burst (5 frames) or never confirmed real skips under 20% dropout (25+ frames). Replaced with a sliding window: a later or skipped step is confirmed when its evidence matched in at least 60% of the last 1.5 s of frames (`SKIP_CONFIRM_S`, `SKIP_CONFIRM_RATIO`; window never shorter than `skip_persistence_frames`).
- Results with the window: original, no-glovebox, no-computer, swapped, no-endcard, stopped-early and missing-middle splices all correct; real skips confirmed within ~1-2 s with up to 40% dropout; false esa_logo bursts up to 0.9 s and scattered false detections up to 10% cause no change.
- Remaining weakness: normal completion of the current step still needs only `min_frames` (5) consecutive matches, so 20% scattered false esa_logo completed step_005 early (126 s). step_002 (actor_visible) still completes at 0.16 s. Both wait on the owner's MELFI context before changing plan semantics.

## Checkpoint 29 - 2026-09-14 - MELFI restarted on the Slawosz (Ignis) video; state checker and inside_of

- The MELFI package held `studying_cells_in_space` (Life Sciences Glovebox footage, not MELFI). It was copied with its take, 70 boxes, timeline, dataset and detector into a new activity `studying_cells_lsg`; `cold_stowage_melfi` was cleared and now holds `slawosz_using_melfi-8821822197` (67.16 s, 25 fps, 768x432, session `melfi_ignis_session_001`, actor `astronaut_slawosz`).
- New MELFI plan v1.0.0 from the owner's context: 19 objects (sample, melfi_freezer, dewar_1-4, dewar_latch, dewar_hatch open/closed, tray_1-4 in/out, compartment_1-2 open/closed, compartment_knob, astronaut_slawosz, astronaut_other, ice_vapor, fabric) and 8 steps. Quadrant numbering facing MELFI: 1 top-right, 2 top-left, 3 bottom-left, 4 bottom-right (Slawosz opens the top-right door). Timeline imported with approximate 1 s times for the owner to refine. The owner does the boxing; training waits for the owner.
- Schema (owner-approved): `ObjectSpec.states`, `EvidenceRule.inside_of`; plan validation checks inside_of references and that object_state states are declared. Detector classes for stateful objects are `<class>__<state>` (`ExperimentPlan.detector_classes()`); boxes carry the state in the existing annotation `state` field.
- Evidence: `object_state` implemented (matches the state class, reports "object in another state"); `object_visible` matches any state of a class; `inside_of` needs >=80% of the box inside a container detection and works on object_visible and object_state.
- Engine: a later step is not a skip candidate while an earlier pending step needs the same object in a different state (so "hatch closed" at the start is not step 8).
- Datasets: data.yaml is rewritten whenever the plan's detector classes change (fixes the stale class list bug); boxes map to state classes and a stateful box without a valid state is rejected at save and at prepare.
- Studio: State picker, per-frame box list (change state, redraw, delete), class colours, show/hide box labels, copy boxes from the previous frame, keyframe limit 1000, procedure builder fields for object states and step state/inside_of, and saving the procedure keeps the loaded camera, alert policy, version and extra evidence rules. `DELETE /api/activities/<id>/annotations/<annotation_id>` added. Verified in the browser: a hatch box drawn inside a dewar box with state "open", then both deleted.
- Issue alerts (ice vapour, fabric) are deferred until after training at the owner's request.

## Checkpoint 30 - 2026-09-15 - MELFI detector trained on the owner's boxes; 8/8 steps on the Slawosz video

- Owner boxed 55 frames (every 30 frames, 0-66 s): 775 boxes. Added the `logo` object (ESA end card, 7 boxes) and `dewar_latch` states left (closed) / right (open). tray_3 out and compartment_2 open never occur in the video.
- Dataset built from boxed frames only (no unboxed background frames, which would teach "no MELFI" on frames where it is present). Horizontal flips disabled in training because dewar/tray quadrant numbers and latch left/right are orientation-specific. imgsz 768, yolo11n, 200 epochs.
- Held-out run (44 train / 11 held-out frames): mAP50 0.791, mAP50-95 0.421. Strong: melfi_freezer, dewars, hatch closed, trays, slawosz, fabric (~0.9-0.99). Weak: sample 0.25, compartment_knob 0.33, rare states (tray_2 in, compartment_1 closed). Final model trained on all 55 frames (mAP50 0.981 on frames it trained on, not a fair score) installed as `activities/cold_stowage_melfi/models/detector.pt`.
- Detector now predicts at the model's trained image size (read from the checkpoint) instead of Ultralytics' 640 default; PerceptionPipeline accepts `conf_threshold`.
- Checker fixes found by testing on the video: (1) overlapping boxes of the same object in different states now keep only the more confident state (`resolve_state_conflicts`, IoU >= 0.5), which stopped "compartment 1 closed" firing while it was open; (2) step completion now needs the evidence in >= 80% of the last `min_frames` frames instead of `min_frames` in a row, matching the flicker-tolerant skip window and removing a false SKIP/OUT_OF_ORDER pair; (3) state and inside_of rules use min_frames 15 (0.6 s).
- Plan v1.1.0: one observable action per step; step 5 requires the sample inside compartment 1 while compartment 1 is open; step 8 requires the dewar 1 hatch closed and the dewar 1 latch left. Timeline replaced with box-derived change points (e.g. compartment 1 opens 20.4-21.6 s, closes 26.4-27.6 s).
- Final model on the full video (1679 frames, 84 fps on the RTX 5050): all 8 steps completed in order, no alerts, each within about 1 s of the box-derived change window (step_01 0.16, step_02 12.95, step_03 15.35, step_04 21.11, step_05 22.43, step_06 27.34, step_07 35.14, step_08 42.77).
- Caveat: one video, and the final model has seen the 55 boxed frames; the other 1624 frames are unseen but strongly correlated. A second recording is needed for a real generalisation score. The Studio's own "Start laptop-safe training" button still uses Ultralytics' default horizontal flip, which is wrong for this activity's quadrant/left-right classes.

## Checkpoint 31 - 2026-09-15 - Real-speed, smooth dashboard playback on the GPU

- Owner's test (started with `startup.bat`, watched in their own browser) ran at 0.20x real time (42.8 s of video in 217.6 s, from `logs/web_cold_stowage_melfi_1789482805.jsonl`). Profiling ruled out CPU inference (25 ms/frame on this CPU), FP16 (slower on the RTX 5050: 21.7 vs 8.7 ms) and power throttling. Reproducing with the in-app browser attached gave 1.88x, so the exact trigger in the owner's browser was not reproduced; the pipeline was restructured so no viewer, disk or encode work can slow analysis.
- `SessionRunner` now uses three threads: analysis (decode, GPU detect, engine; unchanged step logic), presenter (overlay + JPEG encode from a newest-frame `LatestSlot`), and recorder (MP4 backup from a drop-oldest queue, only for live cameras/RTSP; uploads skip it).
- File sources are paced by `PlaybackClock` to the video's own frame rate; frames are skipped for detection only when more than 0.5 s behind. The MJPEG stream now waits on a `threading.Condition` (`WebState.wait_for_frame`) instead of polling at 30 Hz.
- GPU: detector warm-up before playback; stream JPEGs encoded with nvjpeg (`halo/web/frame_encoder.py`, OpenCV fallback); overlay blends only the header strip. Status exposes `realtime_factor`, `lag_s`, `timings_ms`, `display_fps`, `encoder`, `cpu_fallback`; the dashboard shows a speed readout and a red banner if running on CPU with an NVIDIA GPU present. Per-session perf lines are written to `<session log>.perf.jsonl`. The dashboard re-fetches the plan and activity list only when `plan_revision` changes.
- Verified with the server started like `startup.bat` and a browser attached: 1.000x real time, 25.0 fps delivered to the stream client (gap mean 40 ms, p95 50 ms), zero skipped or dropped frames, device cuda:0 with nvjpeg, all 8 MELFI steps at the same video times as Checkpoint 30 with no alerts.

## Checkpoint 32 - 2026-09-15 - Voice alerts keep up with step completions

- Owner reported the browser TTS lagging behind task completion. Cause: every event queued a full-sentence utterance ("Step completed. Slawosz opens compartment 1 with its knob.") on `speechSynthesis`, so close-together steps (4, 5, 6 within ~6 s) built an ever-growing backlog.
- `web/src/App.jsx` now drives speech through a small controller: step completions use a short phrase ("Step 4 done, opens compartment 1.", clause-trimmed from the step description) at rate 1.15; completions that arrive while speaking are merged ("Steps 5 and 6 done."); alerts interrupt routine speech; the final summary clears anything pending; turning voice off cancels speech.
- Verified with a recording speech mock in the dashboard during a real-speed run: every announcement started within about 1.7 s of its step completing (most immediately), with no growing backlog; the summary spoke once at the end.
- Follow-up: the owner heard no voice or beeps afterwards. The voice was silent because the in-app browser pane still had the speech recorder mock used for the timing check (reloading the page removed it). Beeps came only from the server process (`winsound`), which is not guaranteed to be audible when the server is started from a background shell, so the dashboard now also plays its own tones through Web Audio: a short 880 Hz beep for each completed step and a double 440 Hz tone for alerts, following the Voice alerts switch.

## Checkpoint 33 - 2026-09-22 - Described, not trained: open-vocabulary detection plus VLM frame questions

- Problem the owner raised: the trained MELFI detector only works on the video it was trained on, and boxing a video per activity is slow. Measured this first on an unseen MELFI video (`studying cells in space.mp4`, a different astronaut, same freezer, MELFI visible for roughly the first 22 s of 153 s): the trained detector misses the freezer, dewars, tray and sample, and labels the Life Sciences Glovebox as `melfi_freezer` on 63% of frames.
- MMAction2 was evaluated and rejected: its `mmcv` wheels stop at torch 2.4 / CUDA 12.1, while the RTX 5050 is Blackwell (compute 12.0) and needs CUDA 12.8 with torch >= 2.7. It is also a clip classifier, not a source of object state, so it would not answer "is the hatch open".
- Two new perception paths, both used without any training:
  - `halo/perception/open_vocab.py` - YOLOE with the MobileCLIP text encoder. `ObjectSpec.prompts` holds plain-text descriptions ("freezer rack with round doors"); `ExperimentPlan.prompt_classes()` maps each prompt back to a class name so the rest of the pipeline is unchanged. Weights live in `models/yoloe-11s-seg.pt` (27.8 MB) and `models/mobileclip_blt.ts` (599.8 MB, gitignored).
  - `halo/perception/vlm.py` - `VisualQuestionAnswerer` (Qwen3-VL-2B-Instruct, Apache-2.0, bfloat16, frames resized to 768 px) answers a list of yes/no questions about one frame, and `AsyncVisualQuestioner` runs it on a background thread with a newest-frame slot, so the 25 fps analysis thread never waits for it. Answers reach the engine as `PerceptionResult.questions` and a new evidence kind `visual_question`.
- Question phrasing turned out to matter more than the model. Absence-phrased questions failed outright on the unseen video (tray pushed back: recall 0.00; all doors closed: recall 0.00; compartment closed: accuracy 0.24). `EvidenceRule.expect: yes|no` was added so every question is asked positively and the closing steps expect the answer "no" to the same question. Asking questions in small batches was also worse than one call with all of them (more unanswered questions), so they stay in a single call.
- `ProcedureEngine._state_change_pending` was generalised (`_change_key`) to cover `visual_question` + `expect` as well as `object_state`, because step 8's "door open? -> no" is trivially true at video start and previously made the engine mark the whole procedure skipped in the first two seconds.
- `activities/melfi_zeroshot/` is the described-not-trained MELFI plan: 6 objects with prompts, 8 steps, 5 questions, no detector file and no boxes. The server picks zero-shot mode automatically when an activity has no `models/detector.pt` but its objects have prompts (status reports `mode: zero_shot` and the live answers; the dashboard shows a "described, not trained" row and a "what the model sees" panel).
- Honest result on the unseen video. Plan v0.2.0 completed all 8 steps, but the times gave it away: steps 6, 7 and 8 completed at 35.7, 54.6 and 59.3 s, long after MELFI leaves the frame at about 22 s - the glovebox footage trivially satisfies "compartment open? no" and "door open? no". v0.3.0 adds a "is a large freezer wall with round doors visible" guard to the closing steps; the same video then completes steps 1-5 at 4.9, 8.5, 8.6, 13.7 and 17.2 s, all inside the real MELFI section, and leaves 6-8 open. Steps 2 and 3 completing 0.12 s apart is still too fast to be a true reading of two separate actions.
- So the claim this supports is: a plan written only in English recognises the first half of a procedure in a video nobody trained on, which the trained detector cannot do at all. It is not yet as sharp as the trained detector is on its own video (all 8 steps within ~1 s of the boxed change points). Fine states (a compartment lid, a latch side) remain the weak part; coarse ones (tray out: accuracy 0.87, recall 0.94 on the unseen video) work.
- Unprompted side effect to be aware of: Ultralytics auto-installed `clip`, `ftfy`, `regex`, `tqdm` and `wcwidth` into `.venv` when YOLOE first loaded its text encoder.

## Checkpoint 34 - 2026-09-23 - Described mode made fast and honest; hybrid mode; two corrections to Checkpoint 33

**Corrections to Checkpoint 33 first.**
- `studying cells in space.mp4` contains **two** full MELFI cycles, not one (checked on 0.5 s frame sheets): cycle 1 (a retrieval) opens the door at ~3.5 s, pulls a tray at 4.0 s, takes a pink sample bag out at 5.0 s, pushes the tray back at 6.5 s and closes the door at ~7.5 s; cycle 2 opens at ~16 s, tray out 16.5 s, item out ~18 s, tray back 20.5 s, door closed 21.0 s; the glovebox footage starts at 22 s. Checkpoint 33 judged step times against a single-cycle reading, so its "steps 1-5 at the right times" is not supported.
- The "is a large freezer wall with round doors visible" guard did not work: once answers were read as probabilities it scored 1.00 on every frame of that video, glovebox included (the glovebox also has round ports). The v0.3.0 run left steps 6-8 open for other reasons.

**What changed.**
- Answers are now probabilities read in one forward pass (`VisualQuestionAnswerer.ask`, `filled_answer`): the JSON answer is pre-filled once with every slot "yes" and once with every slot "no", and the yes-vs-no probability at each slot is averaged. Scored on the owner's 55 boxed Slawosz frames (the VLM has never seen them): it is as well calibrated as generating the answer (tray out: accuracy 0.98 at a plain 0.5 cut, AUC 1.00) and 4.6x faster (0.61 s vs 2.85 s for 9 questions; ~0.4 s for 3-5 questions). Asking each question on its own is badly biased towards "yes" (tray accuracy 0.45 at 0.5) and calibrating against a grey image did not fix that - the model needs to see the questions together.
- Evidence uses a dead band: yes at p >= 0.6, no at p <= 0.4, "unsure" in between matches neither (`question_verdict`). A question the model cannot answer (the compartment-lid question sits at 0.45-0.55 all video) can no longer complete a step by chance. On cached answers this cut wrong completions on Slawosz from 5 to 1.
- The questioner always asks the plan's full question set (narrowing is gone): the cost is now nearly flat in question count, and probabilities shift when the set of questions changes.
- Answer smoothing was tried and removed: blending each answer with the previous one delayed short events (the tray is out for only 2.5 s in cycle 1) and made results worse once scored against the corrected times.
- In zero-shot mode the open-vocabulary detector is skipped when no rule reads detections (`detections_needed`, `PerceptionPipeline(run_detector=False)`). With the detector and the VLM sharing the GPU, analysis fell to ~9 fps and a 10-frame hold became ~1.1 s; without it analysis runs at 25 fps.
- Plan `melfi_zeroshot` v0.4.0: five steps using only what the camera can see - holds sample, tray out, sample leaves hands while the tray is out, tray back in with the open door visible, door closed - three questions, 10-frame (0.4 s) hold. The compartment lid (hidden under the glove) and the door while the tray blocks it are left to a trained detector; the probability timelines showed the model reports "door open" only when the dark opening is actually visible.
- Hybrid mode: a trained detector plus `visual_question` rules in the same plan now reports `mode: hybrid`. Dashboard shows each question's probability and a yes/no/unsure mark.
- Studio bug fixed: the procedure builder dropped `expect` on a step's first rule, so re-saving a plan turned "done when: no" into "yes" and inverted the step. It now loads, edits and saves `expect`.

**Results (live dashboard, real time, cuda:0).**
- New video, zero-shot v0.4.0: all five steps in order during cycle 1, no alerts, nothing completed during the 130 s of glovebox footage: tray out 5.4 s (true 4.0), sample released 6.8 s (4.5), tray back with door open 8.3 s (6.7), door closed 9.0 s (7.5) - consistently 1.4-2.3 s behind the action. 25 fps analysis, 406 answers over 153 s.
- Slawosz video, hybrid (trained detector + one question on step 1, temporary copy of the activity, since deleted): 8/8 in order, no alerts, each step ~0.6 s later than trained-only. The cost: the trained detector slows from ~9-18 ms to ~70-100 ms per frame while the VLM runs, and more than half the frames skip detection to stay real-time. A separate CUDA stream for the VLM did not help (median 73 ms vs 72 ms) - the laptop GPU is simply saturated.

**Blocked:** installing `bitsandbytes` (4-bit quantisation, needed to run Qwen3-VL-4B inside 8 GB) was refused by the permission system; not attempted another way.

**Later the same day: the 4B model and the deployed plan's own numbers.**
- Qwen3-VL-4B was downloaded and run with the layers that don't fit in 8 GB spilled to the CPU (1.8 s per answer; for measurement only). On the 55 boxed Slawosz frames it is clearly better on the weak questions - door open AUC 0.86 -> 0.96 (accuracy at 0.5: 0.65 -> 0.84), hand reaching into the tray 0.95 -> 0.97 (0.44 -> 0.87) - but end to end on the new video it is worse: on that overhead fisheye view it answers "no tray" while he is plainly holding the tray (0.02-0.47 at 4.4-5.2 s) and cannot judge the hand-in-tray question at all (flat 0.49). Replayed through the engine it misses cycle 1 entirely. A bigger model trades weaknesses rather than winning outright, so 4-bit quantisation is not the obvious next step.
- A 6-step plan adding "hand reaching into the tray" / "hand back out" (a visible stand-in for the compartment steps) did not earn its place with the 2B: that step fired 5 s early on Slawosz. v0.4.0 stays.
- Deployed plan v0.4.0 (exactly its 3 questions), replayed: new video 4/4 checkable steps within 2.5 s (5.1, 6.3, 7.5, 8.3 s vs 4.0, 4.5, 6.7, 7.5); Slawosz 2/5, with every miss early rather than random - tray out 12.7 s (true 15.35, he is reaching into the dewar), sample leaves hands 16.7 s (22.43; on this video the sample floats free long before it is placed, so the step's meaning does not fit), door closed 39.1 s (42.77; fabric hides the open door).
- Answers depend on the whole question set: adding one unused question to the same call moved Slawosz from 2/5 to 4/5 with identical steps. Test plans exactly as deployed.

## Checkpoint 35 - 2026-09-25 - Operations dashboard redesign

- The owner asked for the Operations dashboard (not the Training Studio) to be rebuilt. New `web/src/Operations.jsx` (presentational components and inline SVG icons) and `web/src/operations.css` (scoped `ops-` classes and `--o-` tokens, so the Studio keeps its styles untouched). `App.jsx` keeps the tested polling, upload and voice logic and composes the new layout.
- Layout: app bar (workspace tabs, GPU, connection); session header with the procedure name, mode chip, one-line status and a single toolbar (one Procedure picker replacing the two old ones, Live source, Open video, Stop, voice toggle); a notice area for alerts and problems; video beside a procedure stepper; session log beside model answers and a collapsible System details panel.
- Behaviour changes: step states come from actual completion, skip and out-of-order events instead of the position of the current step, with the video time of each completion; the session log keeps every event of the run (the server only returns the last 40); the latest alert shows as a dismissible banner with Silence; picking a procedure previews its steps before a video is opened; a finished run shows its last frame from `/api/frame.jpg` (the push stream sends nothing to a new connection once a run has ended); the live-source field is no longer pre-filled with the path of an uploaded video.
- Offline-safe system fonts (Segoe UI Variable / Cascadia Mono) instead of Google Fonts for the Operations screen.
- Server: the burned-in 76 px header strip on streamed frames was removed (it duplicated the page and covered ~18% of a 432 px frame); detection boxes are now drawn with a filled label tag. Frame drawing fell from ~2-4 ms to ~0.1 ms. `/api/analyze/activities` gained `mode` (`trained` / `described` / `unavailable`, from `_activity_run_mode`) so the picker can say which procedures can actually run.
- Verified in the in-app browser on idle, live described-mode (new video) and finished trained (Slawosz, 8/8, 1.00x real time) sessions, at desktop and narrow widths. 208 tests pass, Ruff clean, React build clean.

## Checkpoint 36 - 2026-09-25 - Voice fix, box toggle, logo, and a second pass on the dashboard design

- Voice: the owner heard some steps announced twice and others merged ("steps 4 and 5 done"). The run logs had no duplicate events, so the cause was in the browser: two dashboards open at once (the in-app browser pane had been left on the dashboard) each speaking, plus the deliberate merge-when-busy logic. New `web/src/voice.js`: a single speaking window is elected through a localStorage heartbeat (whichever window was last clicked or focused takes over; the voice button shows a dot when another window has the voice), and a strict queue speaks every step on its own, in order, never merged or dropped; alerts go ahead of queued steps without interrupting the one being spoken; the final summary waits for pending steps; a watchdog skips an utterance the browser never finishes. Verified against the real module with a Node harness (7 checks: two windows, takeover, queued steps, alert priority, summary, watchdog).
- Detection boxes: 1 px outlines and small translucent dark tags with light-blue text instead of 2 px lines and solid blue tags. New `DisplaySettings` schema and `POST /api/display {"show_boxes": bool}`; the presenter draws on a copy of each frame, and toggling after a run redraws the last still frame. The dashboard's "Detection boxes" switch follows the server's setting and only pushes a preference the user saved in that browser. Tests: `tests/test_display_schema.py`, `test_display_toggle_redraws_the_still_frame_without_boxes`.
- Logo: original SVG mark (orbit ring with a gap, satellite, check: "procedure verified in orbit") on a deep-blue tile; used in the app bar and as `web/public/favicon.svg`. Rendered at 16-160 px on dark and light backgrounds and in browser-tab mock-ups; proportions refined once (wider gap, check re-centred).
- Scrollbars (the "sidebar" complaint): thin dark scrollbars matching the theme on the page and inside panels.
- Design pass: Inter and JetBrains Mono bundled locally (OFL, `@fontsource-variable`, offline-safe); 4 px spacing grid, 20 px gaps, 32 px gutters; layered near-black cards with hairline borders; segmented workspace switch; hero header with status pill; four metric cards (progress, current step, alerts, video time); video card with a "Now" bar and the boxes switch below the picture (nothing drawn over the video); timeline whose rail fills as steps complete, with completion times; session log with All / Steps / Alerts / Evidence filters. Status now carries `video_time_s`. Static server registers `.woff2` and `.svg` content types.
- Verified with full-resolution headless Edge captures at 1440, 1280 and 900 px and in the in-app browser at 375 px (no horizontal overflow): idle, trained run mid-way (Slawosz), finished 8/8, boxes off after a run, and a described-mode run with a skipped-step alert. 213 tests pass, Ruff clean, React build clean.

## Checkpoint 37 - 2026-09-26 - Product-page README and overlay confidence filter

- README rebuilt in the style of leading open-source projects (uv, Supabase, Ollama): light/dark hero banner, badges, an animated demo, highlights, two product shots, a train-free section with a live model-answers card, an architecture diagram, quick start, performance and credits. `USP.md` kept alongside.
- Every visual was captured from the running product with headless Edge over the DevTools protocol (`docs/assets/`): `demo.webp` (5.1 MB, 34 s of the Slawosz run at 3x) and `demo.mp4` (full quality), `dashboard-live.jpg`, `dashboard-complete.jpg`, `model-answers.png`. The banner and diagram are HTML designs rendered at 2x with embedded Space Grotesk, Inter and JetBrains Mono (all OFL), in light and dark variants.
- New display setting `DisplaySettings.min_confidence` (default 0, show everything): detections below it are not drawn on the video; the engine still uses them. `POST /api/display` now merges partial updates, so the dashboard's on/off switch keeps the threshold. Status reports `min_box_confidence`. The README captures used 0.6. 215 tests pass, Ruff clean.

## Checkpoint 38 - 2026-09-26 - Light theme and a light-only README

- The Operations dashboard has a light theme. A sun/moon button in the app bar switches it and the choice is saved in the browser (`halo-theme`); `?theme=light` or `?theme=dark` forces one. The video stage stays dark in both themes. The Training Studio is unchanged.
- Every README image is now light: the demo, both product shots and the model-answers card were re-captured from the light dashboard, and the dark banner and diagram were removed.
- The README follows patterns from awesome-readme: a collapsible table of contents, back-to-top links, a "Why it matters" section, a feature-grid graphic (`features.png`), a recognition-modes graphic (`modes.png`: described, trained, hybrid), a gallery, a collapsible FAQ and a "Built with" strip. 215 tests pass, Ruff clean.

## Checkpoint 39 - 2026-09-26 - Every SIH26174 requirement closed and verifiable

Prompted by the competitor scan (51 rival repositories): we held real footage, real weights and real metrics, but requirement 5 was half-met, requirement 2 was only implicit, the "tamper-evident" log was per-line CRC, and there was nothing a judge could run.

- **Stream to a specific IP (requirement 5):** `halo/io/stream_out.py` `UdpStreamPublisher` sends the annotated video as MPEG-TS over UDP (h264_nvenc, then libx264, h264_mf, mpeg2video) on its own thread with a newest-frame slot. `StreamOutputSettings` schema; `GET/POST /api/stream-out`; `--stream-to udp://ip:port`; `HALO_STREAM_TO` and opt-in `HALO_HOST` in `startup.bat`; a "Stream to IP" card in the dashboard. Recordings now go to a per-session folder under `logs/buffer/<exp>/`.
- **Next step spoken (requirement 2):** `StepSpec.instruction` and `ExperimentPlan.spoken_name` (keyed `en`/`hi`), filled in for the MELFI, MELFI-described and red/blue plans. `web/src/speech.js` builds every phrase in English and Hindi: "Monitoring ... First: ...", "Step N done. Next: ...", "Procedure complete.", alerts and the summary. The Now bar shows the next instruction. Local voices only; English prefers an en-IN voice; the EN/हिं switch falls back to English with a notice when Windows has no Hindi voice.
- **Step overdue alert:** the engine raises `STEP_OVERDUE` once when a step stays current past its plan `timeout_s`.
- **Signed record (requirement 4):** `halo/io/signed_log.py`: each line is `{seq, payload, prev, hash, sig}` with a SHA-256 chain and an Ed25519 signature by a per-machine station key in `keys/` (gitignored). At session end a signed downlink report (~1 KB) seals the final hash and event count. The dashboard shows it verified with the size ratio, and `/api/downlink` and `/api/session-log` download it. `cryptography` is now a core dependency (AGENTS.md rule 4 updated).
- **Reproduction for judges:** `python -m halo verify` (also `startup.bat verify`) validates every plan, runs the ISS take through the dashboard's own session runner, checks 8/8 in order, 0 alerts and both signatures, then runs `activities/cold_stowage_melfi/verification/step1_removed.mp4` (the same footage from 12 s) and checks the skip is caught. Result: 8/8 checks pass in about a minute. `verify-log` and `verify-downlink` subcommands.
- **Offline:** the vision-language model loads with `local_files_only=True` first.
- **Fix:** starting from the launch config with a custom detector filtered detections to the stock classes, so MELFI stuck on step 1. The server now filters only when every plan class is a stock class.
- **Docs:** `docs/SIH_REQUIREMENTS.md` (traceability), `docs/VERIFICATION.md` (three commands and expected output), `docs/JURY_DEMO.md` (timed five-minute script). README gains a requirements table, "Verify it yourself", new features and FAQ entries, and a refreshed `features.png`. USP.md updated. 276 tests pass, Ruff clean.

## Checkpoint 40 - 2026-09-26 - Intro video in Remotion

- New `video/` Remotion 4.0.529 project (React + TypeScript). It renders `docs/assets/intro.mp4` (1920×1080, 30 fps, 66 s, 11.8 MB) and `docs/assets/intro-poster.jpg`.
- Nine calm scenes, one idea each, on the light product palette:
  1. procedure → missed step;
  2. name;
  3. recognises equipment and its state;
  4. tells the crew what comes next;
  5. notices skips and out-of-order steps;
  6. plain-language setup;
  7. offline in real time;
  8. signed kilobyte record;
  9. close.
- Everything shown is real:
  - the ESA Ignis clip, with boxes from the trained detector's own output (`public/detections.json`), curated to the one part that matters at each moment;
  - step times from a verified downlink report;
  - the skip timings from the step-1-removed clip;
  - the 80% answer from the model-answers card;
  - the 1,002-byte report.
- Audio: the dashboard's announcement "Step 2 done. Next: pull tray 2 out of dewar 1." spoken by Microsoft Heera through the Windows speech API, over a synthesised ambient pad about 7 dB below it.
- The upscaled footage clip is gitignored and regenerated with the ffmpeg command in `video/README.md`. The README links the intro next to the demo.
- Second pass, same day: the intro is now 36 s and much more kinetic.
  - Visuals: word-by-word headlines rising out of a mask; cards flying in with a 3D tilt; a slow camera push on every scene; a drifting backdrop; scenes that dolly into each other with a blur.
  - Details: a detection scan line; boxes that draw their outline; check marks that pop with a burst; a "Next" highlight that glides between rows; a pulsing alert that shakes in; count-up stats; and a byte counter running from 9,720,664 down to 1,002 as the log collapses into the signed report.
  - Footage now plays at 1.7×.
  - Sound: synthesised whooshes, ticks, chimes and impacts, plus the dashboard's own 440 Hz alert, over a 112 BPM music bed that ducks under the voice line.
- Third pass: every animation keeps its speed, and each beat is now followed by a short hold (0.6–1 s) so viewers can take it in. The scene freezes while the backdrop keeps drifting; holds are listed per scene in `video/src/Intro.tsx` and remapped with `<Freeze>`. The video is now 50.5 s. Also fixed the byte counter, which stopped at 10,494 instead of 1,002 because its easing never reached 1.
- Fourth pass: the ISS footage no longer pauses. Its scene has no holds; instead the clip plays at 1.2x (was 1.7x) over a longer scene, so each detection box stays readable while the footage keeps moving. Box carry-over widened to 20 detection frames to bridge a 0.76 s gap in the hatch detections. The video is now 50.8 s.

## 2026-09-28 — H.A.L.O. rename, presentation video, repo cleanup

- Project renamed to H.A.L.O. (Human Activity Logging in Orbit); the package is `halo`, the
  command is `python -m halo`, and the packaging spec is `packaging/halo_gui.spec` (`halo-web`).
- Presentation video: all product clips re-recorded with a headless-Edge recorder (human cursor
  motion, sorted screencast frames, a deflicker pass); the Remotion `Pitch` composition cuts them
  into a 2:57 video with one reusable caption design, matched to the voice-over script. Grey
  frames in the described-mode clip's video panel are repaired by holding the last good frame.
- Repo cleanup: runtime logs, scratch, the promo workspace, old `output/` artefacts, local tool
  state, reference frame dumps and the old BAS-HAR presentation script are no longer tracked.
- Verified: 276 tests pass; `python -m halo verify` passes all 8 checks.
