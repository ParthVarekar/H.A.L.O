# BAS-HAR Progress Log

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

- Added `bas_har/schema/activity_schema.py` with typed activity, take, timeline, bounding-box,
  visual annotation, dataset, job, evaluation, and model-release contracts.
- Added `bas_har/studio/registry.py` for local filesystem-backed activity packages.
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

- Added validated activity-plan load/save services under `bas_har/studio/plans.py`.
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
  `bas_har/studio/annotations.py`, including frame extraction, bounded box validation, and
  append-only `annotations.jsonl` storage.
- Added a React keyframe reviewer with take selection, configurable sampling, drag-box labels, and
  saved detector classes.
- Added dataset integrity reports in `bas_har/studio/quality.py` for split counts, missing labels,
  malformed YOLO rows, class coverage, and held-out split availability.
- Persisted the actual recording-session membership of each train, validation, and test split and
  surfaced warnings for prototype-only or limited-robustness datasets.
- Enforced session-level splitting in the normal activity preparation path so multiple videos from
  one recording session cannot cross train, validation, and test boundaries.
- Connected reviewed boxes to dataset preparation. Manual annotations replace auto-colour labels on
  corrected frames and extract an extra image when the reviewed frame was not sampled.
- Added held-out detector metrics and background evaluation jobs in `bas_har/studio/evaluation.py`.
  The quality gate runs before model inference and reports precision, recall, F1, TP, FP, FN, and a
  per-image failure gallery.
- Added a downloadable CSV evaluation report from the React dashboard.
- Added checksummed model candidates plus explicit reviewer approval and activation in
  `bas_har/studio/releases.py`; failed evaluations cannot create candidates.
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
