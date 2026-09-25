# Claude Code Handover — bas-har

Last updated: 2026-09-15 (see Section 19 for the current state; Sections 1-18 predate the real
MELFI video and are retained for historical context)

This is the authoritative continuation brief for Claude Code or another coding agent taking over
the repository. It records the project intent, current implementation, exact data state, verified
commands, known limitations, and the safest next actions. Read this file together with
HANDOVER.md; when they differ, this file's dated current-state sections and the files on disk are
the source of truth.

## 1. Repository identity

- Local path: C:\Users\Parth\Desktop\HAR_for_BAS
- GitHub remote: https://github.com/ParthVarekar/HAR_for_BAS.git
- Active branch: main
- Last known commit (per `git log`): d0686d3, feat: trained on three vids
- Working tree at last full check: has uncommitted MELFI/streaming/voice work — see Section 19;
  the owner has not asked for a commit
- Application: React Training Studio plus Python HAR service
- Studio URL: http://127.0.0.1:5767/?workspace=studio
- Project mission: SIH26174 AI human activity recognition for on-board Bharatiya Antariksh
  Station experiments and operations

The project is not production-ready. It is an MVP and research/prototype pipeline with a working
schema, procedure engine, React annotation studio, replay/live service, dataset preparation,
quality gates, and training/evaluation plumbing. As of Section 19, the MELFI activity has a real
video, real boxes, and a trained detector that completes all 8 steps on its own source video, but
this is not yet evidence of generalisation to a different recording.

## 2. What the owner wants next (as of Section 19)

The owner boxes the MELFI video themselves — there is no "hand this to a friend" workflow anymore
(see Section 19). Do not box `cold_stowage_melfi` on the owner's behalf unless explicitly asked
again. The immediate next real work is a second independent MELFI recording session, and the
ice-vapour/fabric issue alerts (deferred; the owner will say when to start them). Sections 2-18
below describe the earlier "hand to a collaborator" plan and are historical only.

Do not start by redesigning the system. First preserve the current activity data, verify the
annotation workflow, and record every new result in this document and docs/progress_log.md.

## 3. Locked decisions — do not silently change

- The authoritative technical specification is
  C:\Users\Parth\Downloads\SIH26174_AI_HAR_BAS_TechnicalDoc_v1.0_2026-08-27.docx.
- The active UI is React on localhost port 5767. Do not restore the old PySide6 interface.
- The red/blue box experiment is the simple regression demo, not the final experiment scope.
- The intended scope includes experiments, maintenance, training, exercise, and complex space
  procedures, but only explicitly represented and labelled data can support a claim.
- The edge target is the owner's laptop with an RTX 5050 8 GB GPU and 24 GB RAM.
- Jetson work is parked.
- 3D HMR and models such as HMR 2.0, SMPLer-X, or smplfitter are parked and must not be
  imported.
- The rule/procedure FSM is the primary sequence engine. A learned temporal head is an explicit
  future v2 direction.
- Use the term orientation-diverse augmentation, not microgravity simulation.
- YAML is the experiment knowledge source; do not hard-code activity-specific class names or
  rules into generic Python.
- Do not change the activity schema, demo, edge target, or parked phases without asking the owner.
- No code comments unless specifically requested.

## 4. Required reading order for code changes

1. CLAUDE_CODE_HANDOVER.md
2. HANDOVER.md
3. AGENTS.md
4. docs/architecture.md
5. docs/validation_matrix.md
6. docs/risk_register.md
7. docs/progress_log.md
8. bas_har/schema/plan_schema.py
9. bas_har/procedure/engine.py
10. bas_har/web/server.py
11. web/src/App.jsx
12. web/src/TrainingStudio.jsx

(`docs/training_studio_plan.md` was retired on 2026-09-16 — it was the original planning document
and every item in it had already been implemented or superseded by the current docs above.)

AGENTS.md is binding for coding style: Python 3.11–3.13 only, pathlib instead of os.path,
type hints on public functions, loguru instead of logging.getLogger, specific exceptions,
schema-first changes, tests for public behavior, Ruff clean, and pytest clean before handoff.

## 5. Exact environment and verification

The repository expects Python >=3.11 and <3.14. On the original machine the py -3.11 launcher
was unreliable, so the existing .venv came from an installed uv-managed CPython 3.11.9 runtime.
A fresh collaborator may use a working Python 3.11 installation instead.

Setup from PowerShell:

    cd C:\Users\<user>\path\to\HAR_for_BAS
    py -3.11 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -e ".[perception,streaming,voice,packaging,dev]"

The repository's current quick-start batch uses perception, streaming, voice, studio, and dev.
The packaging extra is only needed for PyInstaller work.

Full verification from repository root:

    cmd /c startup.bat test

This currently performs:

- 115 pytest tests
- ruff check .
- ruff format --check .
- demo plan validation
- React build if needed
- headless React/web smoke test

The last verified result was all green: 115 passed, Ruff clean, 96 files formatted, demo plan
valid, and all BAS-HAR checks passed. Also verified separately with npm.cmd run build from web.

The direct smoke commands are:

    .\.venv\Scripts\python.exe -m pytest -q
    .\.venv\Scripts\python.exe -m ruff check .
    .\.venv\Scripts\python.exe -m ruff format --check .
    cd web
    npm.cmd run build

Before any handoff, run the full batch gate again. Documentation-only changes still require the
gate because the project convention is to leave a fully verified tree.

## 6. How to start the application

Training Studio:

    startup_training_studio.bat

Then open http://127.0.0.1:5767/?workspace=studio.

The launcher:

- requires .venv\Scripts\python.exe;
- builds web/dist if it is missing;
- starts or reuses the local server on 127.0.0.1:5767;
- uses the red/blue plan and models\yolo11n.pt for server startup;
- opens the Studio URL.

The general launcher is startup.bat. Relevant commands:

    startup.bat test
    startup.bat web C:\path\to\video.mp4
    startup.bat live 0
    startup.bat analyze C:\path\to\video.mp4
    startup.bat prepare C:\path\or\folder
    startup.bat annotate
    startup.bat train

The general dashboard currently uses the red/blue demo plan. Training Studio activity packages
are loaded by the React service from the activities directory and are not selected by changing
the demo plan path in startup.bat.

## 7. Architecture and data flow

The system has these main layers:

1. Input and I/O: webcam, MP4, or RTSP through OpenCV/AV capture; rotating MP4 buffer and
   CRC-verified JSONL event output are implemented.
2. Perception: YOLO detector, MediaPipe pose/hands, and heuristic hand-object interaction.
   Device selection can resolve to CUDA.
3. Procedure: YAML-driven evidence rules and finite-state engine with persistence, skip, pause,
   silence, alert rate limiting, and optional JSONL sink.
4. Voice/feedback: pyttsx3 worker and asynchronous confirmation sound. TTS is enabled by default
   with --no-tts as opt-out.
5. Web UI: Python service exposes health, plan, status, frame, stream, events, source controls,
   and Training Studio APIs. React renders the live dashboard and the annotation studio.
6. Dataset/training: activity packages persist plans, takes, timeline, annotations, datasets,
   job records, quality reports, evaluation reports, and release candidates.

Cross-cutters are the Pydantic schema contracts and packaging. The schema is the contract between
YAML, the generic procedure engine, evidence evaluators, and UI activity packages.

The normal Training Studio path is:

    activity/plan -> take import -> timeline import -> keyframes -> boxes -> quality gate
    -> YOLO dataset -> training job -> evaluation -> manual release approval

Training data is split by recording session, not by adjacent frames. This prevents leakage from
the same video appearing in both training and held-out metrics.

## 8. Repository map

Important top-level files and directories:

- AGENTS.md: coding conventions.
- HANDOVER.md: earlier detailed engineering handoff.
- CLAUDE_CODE_HANDOVER.md: this dated continuation brief.
- dataset_progress.md: collaborator-facing data inventory and annotation checklist.
- training_guide.md: human instructions for cloning, using Studio, boxing, and training.
- startup.bat: general checks/dashboard/training launcher.
- startup_training_studio.bat: Studio launcher on port 5767.
- pyproject.toml: Python version, dependencies, extras, CLIs, Ruff, pytest.
- bas_har/schema: plan, event, activity, take, annotation, dataset, job, evaluation, release
  contracts.
- bas_har/procedure: engine and evidence evaluation.
- bas_har/perception: detector, pose, hands, HOI, and related inference code.
- bas_har/io: capture, stream, buffer, and event output code.
- bas_har/voice: TTS and confirmation feedback.
- bas_har/web: local Python HTTP service and Studio API.
- web/src/App.jsx: React dashboard shell.
- web/src/TrainingStudio.jsx: React training workflow and annotation UI.
- web/src/styles.css: visual styling.
- scripts: CLIs, smoke tests, dataset prep, training, evaluation, replay, and analysis.
- tests: unit/integration tests.
- experiments/red_blue_box: six-step regression plan and recording notes.
- activities: persisted generic activity packages.
- datasets/red_blue_box: classic demo dataset workspace.
- models/yolo11n.pt: 5.6 MB cached YOLO model.
- docs: architecture, validation, risks, training-studio plan, and progress history.
- output: generated PDF/screenshots and other artifacts.

## 9. Current Git and documentation state

At the time of this handoff:

- main is synchronized with origin/main at 1a96e69.
- No uncommitted source or data changes were present.
- The last commit added dataset_progress.md, training_guide.md, README links, and current
  collaborator notes in HANDOVER.md and docs/progress_log.md.
- The docs intentionally preserve historical decisions and checkpoints; do not delete history
  just because a newer section supersedes it.

When making a change, append a dated checkpoint to docs/progress_log.md containing files changed,
behavior completed, verification commands, and the next exact action. Update this handoff if the
current data state, implementation status, or next action changes materially.

## 10. MELFI activity — exact current state

Activity directory: activities/cold_stowage_melfi/

Activity metadata:

- ID: cold_stowage_melfi
- Name: Cold Stowage and MELFI Operations
- Kind: experiment
- Version: 0.1.0
- Lifecycle: imported
- Plan: activities/cold_stowage_melfi/plan.yaml

Take:

- Take ID: studying_cells_in_space-c2dce8af89
- Stored file: activities/cold_stowage_melfi/takes/studying_cells_in_space-c2dce8af89.mp4
- Original filename: studying cells in space.mp4
- SHA-256 prefix in metadata: c2dce8af89; full hash is in takes.jsonl
- Recording session: cold_stowage_melfi_session_001
- Duration: 153.04 seconds
- FPS: 25.00653423941453 according to the Studio probe
- Resolution: 768 x 432
- Plan camera: 25 FPS and [768, 432]

The Studio-probed media metadata is authoritative. An external analyser previously claimed 29.97
FPS and 1920 x 1080; those values were not used.

Timeline records:

- event_001, 0.00–5.00, step_001: title card and logos
- event_002, 5.00–65.00, step_002: interviewee explains Cold Stowage and MELFI
- event_003, 65.00–75.00, step_003: MELFI freezer unit shown
- event_004, 75.00–85.00, step_004: dewar compartments visible
- event_005, 85.00–95.00, step_005: sample containers inside dewar shown
- event_006, 95.00–105.00, step_006: control panel and display shown
- event_007, 105.00–143.04, step_007: astronaut works with visible ISS equipment and mounted
  computer
- event_008, 143.04–153.04, step_008: ESA logo animation/end card

The eight records are contiguous and cover the full take. The 105.00–153.04 tail was manually
reviewed from the actual MP4 because the initial imported timeline stopped at 105.00 seconds.
The surrounding ISS hardware in the astronaut segment was intentionally not assigned a MELFI
class without direct evidence.

MELFI object classes in plan.yaml:

- interviewee_1 -> class interviewee
- melfi_freezer -> class melfi_freezer
- dewar_compartment -> class dewar_compartment
- sample_container -> class sample_container
- control_panel -> class control_panel
- astronaut_1 -> class astronaut
- computer -> class computer
- nasa_logo -> class nasa_logo
- esa_logo -> class esa_logo
- title_card -> class title_card

MELFI procedure steps:

- step_001: title card and logos appear; object_visible title_card; expected 5 s.
- step_002: interviewee explains the topic; actor_visible; expected 60 s.
- step_003: MELFI freezer unit shown; object_visible melfi_freezer; expected 10 s.
- step_004: dewar compartments visible; object_visible dewar_compartment; expected 10 s.
- step_005: sample containers shown; object_visible sample_container; expected 10 s.
- step_006: control panel/display shown; object_visible control_panel; expected 10 s.
- step_007: astronaut works with visible equipment and mounted computer; object_visible computer;
  expected 38 s.
- step_008: ESA animation/end card; object_visible esa_logo; expected 10 s.

Every plan step currently has min_frames 5, timeout_s 60, and a next-step link except step_008.
The plan has no regions and no region_geometries.

Current MELFI labels and training status:

- Bounding-box annotations: 0.
- Dataset: not prepared for MELFI.
- Training jobs: none for MELFI.
- Evaluation report: none for MELFI.
- Release candidate: none for MELFI.

Important annotation caveat: the quality gate counts every plan object class. The plan currently
includes title/logo classes as detector objects. The annotator must either box them consistently
where visibly identifiable or the plan must be revised to move them to scene metadata before the
quality gate. Do not silently label absent or ambiguous classes. Do not label generic ISS hardware
as melfi_freezer.

Recommended annotation setup:

- Use the existing take; do not duplicate it.
- Use STEP 05 in the Studio.
- Generate keyframes with every_frames=40. The take is about 3,826 frames and this gives about
  1.6-second spacing within the current 120-keyframe limit.
- Choose only the exact visible classes from the selector.
- Draw tight boxes around visible instances.
- Use Enter or Save & next frame to save and advance.
- Multiple boxes can be saved on one frame.
- Use the frame dropdown to revisit frames. It was changed to a compact, high-contrast dropdown
  to avoid horizontal scrolling and washed-out native options.

Persisted annotation path:

    activities/<activity>/annotations.jsonl

## 11. Concrete Hardening activity — reference only

Activity directory: activities/concrete_hardening_msl/

- Take: Material_Sciences_test_1-17b6df0d55
- Original video: Material_Sciences_test_1.mp4
- Session: msl_concrete_hardening_session_001
- Duration: 103.4 seconds
- FPS: approximately 25.0097
- Resolution: 768 x 432
- Timeline: 8 rows
- Annotation JSONL rows: 87
- Represented classes: glovebag, container, mixing_tool, syringe, laptop, esa_logo
- Generated dataset: dataset_v1 with 517 train images
- Validation images: empty
- Test images: empty
- Quality report: passed=false because there is only one recording session
- Training attempts: two CUDA-resolved laptop-safe attempts stopped before a valid epoch/report
- Reliable model/evaluation result: none

This activity proves that the annotation/dataset plumbing can persist data, but it is not evidence
of production accuracy. Do not claim the project has successfully trained a useful detector from
this activity.

## 12. Red/blue demo state

The red/blue plan at experiments/red_blue_box/experiment_plan.yaml remains the regression demo.
The supplied video Man_sorting_blocks_in_box_202609030054.mp4 was accepted by the color-sequence
recognizer, completing six expected steps with events around 0.791, 1.916, 3.333, 4.458, 5.458,
and 6.875 seconds. The verified real-engine path used cuda:0 for YOLO and wrote CRC-verified
JSONL events.

The pre-trained COCO model does not contain the demo's custom red_box, blue_box, or big_box
classes. The accepted sequence result is therefore the plan-driven/color-sequence regression
path, not proof that an un-finetuned detector recognizes the custom objects robustly. Real
representative takes must be recorded, boxed, split by session, fine-tuned, and evaluated.

Each completed demo event also triggers one asynchronous confirmation ping through the Windows
audio device. The worker is shut down with the capture session.

## 13. Implemented functionality

Implemented and covered by tests:

- Pydantic plan schema with extra-forbid validation and discriminated evidence kinds.
- YAML plan validation and CLI.
- Procedure FSM with evidence persistence, transitions, explicit branches, skip detection, pause,
  silence windows, rate limiting, and optional JSONL sink.
- object_location in_region and outside_of with validated region geometries.
- YOLO/MediaPipe perception stack and GPU-aware device selection.
- webcam, MP4, and RTSP capture.
- rotating MP4 circular-buffer behavior in the web runner.
- CRC-verified JSONL event output.
- asynchronous TTS and confirmation sound workers.
- React dashboard on 5767 with live frame, telemetry, events, source controls, and stream.
- Training Studio activity registry and package persistence.
- guided procedure builder and activity plan validation.
- video take import with probed media metadata.
- CSV/Excel ground-truth timeline import.
- keyframe generation and drag-box annotation.
- compact frame dropdown with backward/forward navigation fixes.
- Save & next frame behavior and Enter shortcut.
- dataset preparation, deterministic session-level splits, quality report, training jobs,
  evaluation/failure gallery, release candidate, checksum, and manual approval plumbing.
- PyInstaller React-server bundle verification.

## 14. Not finished or deliberately parked

Active unfinished work:

- annotate MELFI frames;
- decide whether title/logo classes should be detector targets or scene metadata;
- add independent MELFI recording sessions;
- pass the MELFI quality gate;
- train a laptop-safe CUDA baseline;
- evaluate on held-out sessions and inspect failure media;
- approve a release only after metrics and manual review.

Not finished and deliberately parked:

- 3D HMR and mesh/SMPL pipelines;
- learned temporal head;
- Jetson/TensorRT/INT8 deployment;
- multi-astronaut tracking;
- federated learning;
- AR overlay;
- final trained-model packaging asset.

Generic evidence gaps noted in the architecture plan may still require work before complex
activities can be approved: offline/replay hardening and generic package evidence adapters.
`object_state` support (and the `inside_of` containment rule) is now implemented — see Section 19
— and used by the MELFI plan. Do not implement activity-specific shortcuts as a substitute for
those generic contracts.

## 15. Known risks and traps

1. Dataset size: one video can demonstrate plumbing but cannot measure generalization.
2. Session leakage: never split neighboring frames from one video across train/val/test.
3. MELFI class ambiguity: generic ISS equipment is not automatically MELFI hardware.
4. Contextual class gate: title/logo classes can make quality fail if not labelled or removed.
5. GPU claims: the UI showing an RTX name is not proof of active CUDA use; check torch and job
   logs, and use nvidia-smi while a job is running.
6. YOLO base labels: COCO classes do not equal plan object IDs or custom experiment classes.
7. Media metadata: use the Studio probe, not analyser guesses.
8. Python compatibility: MediaPipe 0.10.21 and the current OpenCV/NumPy constraints target
   Python 3.11/3.12-era environments.
9. Capture performance: the web capture path can be CPU-heavy; benchmark after the custom model
   and avoid claiming real-time performance without measurement.
10. Historical docs: HANDOVER.md contains older checkpoints and historical next-task lists;
    use its current Sections 12–17 and this document rather than the old Phase 1 list.

## 16. Safest next work plan

### First: verify before touching data

1. Check git status and branch.
2. Read this file, HANDOVER.md, AGENTS.md, schema, engine, server, and Studio files.
3. Run cmd /c startup.bat test.
4. Confirm the MELFI take file and metadata exist.
5. Do not delete or reset activities/cold_stowage_melfi.

### Second: help the human annotator

1. Start startup_training_studio.bat.
2. Open the Studio workspace and select cold_stowage_melfi.
3. Use the existing take studying_cells_in_space-c2dce8af89.
4. In STEP 05 set the interval to 40 frames.
5. Generate/load keyframes and draw boxes using only exact visible classes.
6. Save each frame with Enter or Save & next frame.
7. Record the final annotation count and any classes that never appear.

### Third: validate labels and data

1. Run the quality gate and inspect its report, not just its boolean.
2. If the gate fails due to title/logo classes, stop and ask the owner whether to keep them as
   detector targets or revise the plan to treat them as scene metadata.
3. Add at least two independent MELFI sessions before trusting validation/test metrics. Ten or
   more varied sessions is a stronger long-term target.
4. Re-run dataset preparation after any annotation correction; do not hand-edit generated labels.

### Fourth: train and evaluate

1. Use auto device selection and the laptop_safe preset first: 50 epochs, 512 image size, batch
   4, workers 0, patience 15.
2. Verify torch.cuda.is_available(), GPU name, resolved job device, and nvidia-smi utilization.
3. Save training logs and metrics.
4. Evaluate only after non-empty session-separated train/val/test splits exist.
5. Inspect false positives/negatives and failure gallery before any tuning.
6. Do not create or activate a release candidate unless evaluation passes and the owner reviews it.

## 17. Progress logging protocol

Every future agent should append a checkpoint to docs/progress_log.md and update this handoff when
a material change happens. Each checkpoint must include:

- date;
- agent or collaborator role if known;
- objective;
- exact files changed;
- data records added, removed, or reset;
- commands run and their results;
- GPU/device used if training or inference ran;
- known failures or limitations;
- next exact action;
- commit hash and push status when committed.

Never report a model as trained merely because a job was queued or resolved to CUDA. Report the
quality gate, training completion, validation/test availability, metrics, evaluation status, and
release approval separately.

## 18. Completion criteria for the current MELFI milestone

The MELFI milestone is not complete until all of the following are recorded:

- boxes saved for intended MELFI keyframes;
- class policy resolved for title_card, nasa_logo, and esa_logo;
- quality gate passes or a documented owner-approved exception exists;
- at least three independent recording sessions for meaningful held-out evaluation;
- non-empty train, validation, and test splits;
- laptop_safe training completes with a recorded device;
- evaluation report and failure gallery exist;
- manual review decides whether a candidate is safe to release;
- progress log and this handoff contain exact counts, paths, commands, and commit.

Until then, the correct status is staged for annotation, not production-ready.

## 19. Current state — 2026-09-15 (supersedes Sections 2, 10, 14-18 for MELFI)

Everything above this section describes the repository before the owner supplied the real MELFI
video and its context on 2026-09-14/15. Full detail, in order, is `docs/progress_log.md`
Checkpoints 27-32. Summary:

**The video changed.** The take described in Sections 10 and 14-17
(`studying_cells_in_space-c2dce8af89`, an interview plus Life Sciences Glovebox footage) was never
MELFI hardware. It was moved intact — video, 70 boxes, timeline, dataset, and its trained detector
— to a new activity, `studying_cells_lsg`, kept as a reference for a later broad-video showcase.
`cold_stowage_melfi` was cleared and now holds the real video the owner described:
`slawosz_using_melfi-8821822197.mp4` (67.16 s, 25 fps, 768x432, session
`melfi_ignis_session_001`): ESA astronaut Slawosz stores a sample pouch in MELFI during the Ignis
mission.

**The schema gained two owner-approved features.** `ObjectSpec.states` (a list like `["open",
"closed"]`) expands each class into per-state detector classes via `state_class`/`base_class`
helpers and `ObjectSpec.detector_classes()` / `ExperimentPlan.detector_classes()` /
`ExperimentPlan.class_states()`; the annotation `state` field carries this on each box, and dataset
preparation (`bas_har/studio/datasets.py::annotation_class`) maps label+state to the right YOLO
class, rewriting `data.yaml` whenever the plan's classes change (fixing a stale-class-list bug).
`EvidenceRule.inside_of` mirrors the existing `outside_of` (`bas_har/procedure/evidence.py`,
`INSIDE_MIN_FRACTION = 0.8`) so a step can require one box mostly inside another, e.g. "sample
inside the open compartment".

**The new plan (v1.1.0) has 20 objects and 8 steps**, each one observable state change (earlier
drafts had bundled several actions per step; that was split apart after the first test run showed
it made the checker unable to tell which action happened): sample, melfi_freezer, dewar_1..4,
dewar_latch (states left/right), dewar_hatch (open/closed), tray_1..4 (in/out), compartment_1/2
(open/closed), compartment_knob, astronaut_slawosz, astronaut_other, ice_vapor, fabric, logo.
Quadrant numbering, confirmed against the video: 1 top-right, 2 top-left, 3 bottom-left, 4
bottom-right, facing the open MELFI door.

**The owner boxed the video themselves**: 775 boxes across 55 frames. Claude Code did not draw any
of these boxes — the owner explicitly said they would do the boxing and Claude Code should only
set up the Studio. The Studio gained, to support this: a state picker tied to the selected class; a
per-frame box list with redraw/change-state/delete; per-class colours; a show/hide box-labels
toggle; "copy boxes from previous frame"; and `DELETE
/api/activities/<id>/annotations/<annotation_id>` (`bas_har/studio/annotations.py::delete_annotation`).
Drawing a new box always starts fresh even when the drag begins inside an existing box, so nested
objects (sample inside compartment inside tray inside dewar) were already boxable — the earlier gap
was in labelling coverage, not the drawing tool.

**A detector was trained after the owner's explicit go-ahead**: yolo11n, image size 768, trained
with `fliplr=0`/`flipud=0` (mirroring would swap dewar/tray quadrant numbers and the latch's
left/right state — this is NOT the Studio's own "Start laptop-safe training" button, which still
mirrors by default and should not be used for this activity until that's fixed). Held-out run (44
train / 11 held-out frames): mAP50 0.79, weak on `sample` and `compartment_knob`. The installed
model (`activities/cold_stowage_melfi/models/detector.pt`) was retrained on all 55 boxed frames, so
its own metrics are not a fair held-out score.

**Checker bugs were found and fixed by testing on the real video, not by inspection**:
1. Two boxes of the same base class in different states overlapping (e.g. `compartment_1__open`
   and `compartment_1__closed` both detected on one frame) let the wrong state win by luck of which
   rule ran first; fixed by keeping only the higher-confidence one per frame
   (`resolve_state_conflicts`, IoU >= 0.5).
2. Step completion and skip confirmation both required consecutive matching frames; a single
   dropped frame or false positive flipped the result. Both now require the evidence in >= 80% of
   a short sliding window (`COMPLETION_RATIO`, `SKIP_CONFIRM_RATIO`) instead of every single frame.
3. A step whose final state matches its starting state (e.g. hatch closed at both the very start
   and the very end) was being flagged as "already skipped ahead to" at time zero; the engine now
   tracks which state-changes are still pending before treating a later step as reachable.

**Verified on the real video** (via `melfi_video_test.py` cached-perception replay and via the live
dashboard, both by picking the activity manually with the new picker below and via automatic scene
recognition): all 8 steps complete in order, zero alerts, each within about a second of the
state-change time visible in the owner's own boxes.

**Playback was measured at about 0.2x real time and is now 1.0x.** `SessionRunner`
(`bas_har/web/server.py`) is now three threads — analysis (decode/detect/engine, unchanged logic),
presenter (overlay + JPEG encode from a `LatestSlot`), recorder (MP4 backup via a drop-oldest
queue, skipped entirely for uploads) — so no viewer or disk work can slow detection. File sources
are paced to their own frame rate by `PlaybackClock`; the MJPEG stream is push-based
(`WebState.wait_for_frame` on a `threading.Condition`) instead of polling at 30 Hz; JPEG encoding
uses nvjpeg via `bas_har/web/frame_encoder.py` with an OpenCV fallback; the detector warms up
before playback starts. Status now exposes `realtime_factor`, `lag_s`, `timings_ms`, `display_fps`,
`encoder`, `cpu_fallback`; the dashboard shows a live readout and a red CPU-fallback banner.
Verified with a real browser attached, started the way `startup.bat` starts it: 1.000x real-time
factor, 25.0 fps delivered to the stream client (mean gap 40 ms, p95 50 ms), zero frames skipped or
dropped, unchanged step results.

**Voice alerts went through three fixes, in order**: (1) merged into short phrases at a faster
rate because a full sentence per step fell behind when steps completed close together (the queue is
now capped and duplicate/adjacent completions are merged, e.g. "Steps 5 and 6 done."); (2) found to
be completely silent afterward because the in-app browser pane still had a test speech-recorder
mock installed from timing verification, and because the server's own `winsound` beep isn't
guaranteed audible when the server runs in a background shell — fixed by removing the mock and
adding the dashboard's own Web Audio tones (a beep per step, a double tone for alerts) so sound
doesn't depend on the server process; (3) sped up again on request, now 1.5x rate.

**A manual "Experiment" picker was added** to the Operations dashboard's analyse panel: choosing an
activity skips scene recognition and monitors it directly (`X-Activity-Id` header on
`POST /api/analyze`; new `GET /api/analyze/activities`).

**`close_startup.bat` and `close_training_studio.bat`** were added at the repository root. Each
stops only the processes its matching launcher (`startup.bat` / `startup_training_studio.bat`)
started, told apart by the `--no-start` flag only the Studio launcher passes; `--list` previews
without stopping anything.

**Not yet done**: a second independent MELFI recording session (required before any generalisation
claim — every current MELFI number is measured on the video the model trained on); the ice-vapour
and fabric issue alerts (owner said to build these after training, and will say when); wiring
`fliplr=0` into the Studio's own training button for orientation-sensitive plans generally, not
just via a one-off script.

**Test suite**: 193 passing (`pytest -q`), Ruff and formatting clean, React build clean, as of this
section. New test files since Section 18: `tests/test_state_checker.py`,
`tests/test_web_streaming.py`, `tests/test_frame_encoder.py`.

## 20. Described-not-trained recognition — 2026-09-22 (supersedes Section 19 where they disagree)

Read this with `HANDOVER.md` Section 19, `docs/progress_log.md` Checkpoint 33 and risk register
rows 26-29. Nothing about trained activities changed; this is an additional mode.

**New files**
- `bas_har/perception/open_vocab.py` — `OpenVocabDetector`, same surface as `ObjectDetector`,
  driven by text prompts instead of trained classes.
- `bas_har/perception/vlm.py` — `build_prompt`, `parse_answers`, `FrameQuestioner` protocol,
  `VisualQuestionAnswerer` (Qwen3-VL-2B), `AsyncVisualQuestioner` (background thread).
- `activities/melfi_zeroshot/` — plan v0.3.0 + activity.yaml. No takes, no annotations, no model.
- `tests/test_zero_shot.py` — 11 tests covering prompt mapping, the new rule kind, evidence with
  `expect`, prompt/answer parsing, and the async questioner's non-blocking behaviour.

**Changed files**: `bas_har/schema/plan_schema.py` (`prompts`, `visual_question`, `expect`,
`prompt_classes()`, `visual_questions()`), `bas_har/perception/types.py` (`questions`),
`bas_har/perception/pipeline.py` (prompt/questioner wiring), `bas_har/procedure/evidence.py`
(`_eval_question`), `bas_har/procedure/engine.py` (`_change_key`),
`bas_har/web/server.py` (zero-shot selection, questioner lifecycle, status fields),
`web/src/App.jsx`, `web/src/TrainingStudio.jsx`, `web/src/styles.css`, `.gitignore`.

**Rules for anyone editing a zero-shot plan**
1. Every question is phrased positively. Use `expect: 'no'` for closed/removed/finished. A
   question containing "not", "closed" or "empty" will score near zero — this is measured, not a
   guess.
2. Every closing step must also require a positive "is the equipment visible" question, or footage
   with none of the equipment in it will complete it.
3. Keep the question count small and shared across steps. All active questions go in one VLM call;
   splitting them into several calls made answers go missing.
4. After any plan change, check *when* steps completed against where the equipment actually
   appears in the video. A clean "all steps completed" is the failure mode to distrust.

**State of the unseen-video test**: 5 of 8 steps, correct times, no false completions, no alerts,
1.0x real time. Do not describe this as full recognition of the procedure.

**Environment note**: loading the YOLOE text encoder auto-installed `clip`, `ftfy`, `regex`,
`tqdm`, `wcwidth` into `.venv`. Nothing depends on removing them; 204 tests pass with them present.

## 21. Described mode, second pass — 2026-09-23 (supersedes Section 20 where they disagree)

Read `HANDOVER.md` Section 20 and `docs/progress_log.md` Checkpoint 34 first. Two claims in
Section 20 were wrong and are corrected there: the new video has two MELFI cycles, and the
equipment-visible guard never worked.

**Code facts that changed**
- `bas_har/perception/vlm.py`: `ask()` returns yes-probabilities from one forward pass over a
  pre-filled answer (`filled_answer`, `ANSWER_FILLS`). `parse_answers`, `set_questions` and answer
  smoothing are gone (smoothing was measured and made things worse).
- `bas_har/procedure/evidence.py`: `QUESTION_YES_MIN = 0.6`, `QUESTION_NO_MAX = 0.4`,
  `question_verdict()`; `detections_needed()` (exported from `bas_har.procedure`).
- `bas_har/perception/pipeline.py`: `run_detector=False` gives a pipeline with no detector.
- `bas_har/web/server.py`: `_recognition_mode` -> `zero_shot` / `hybrid` / `trained`; status
  `answers` is `{question: {"p": float, "verdict": "yes|no|unsure"}}`; `_active_questions` removed.
- `web/src/TrainingStudio.jsx`: "done when: yes/no" picker; `expect` now survives load/save.

**Rules (in addition to Section 20's)**
1. Don't split a plan's questions across calls or narrow them per step: probabilities depend on
   the whole question set.
2. Before trusting a question, look at its probability timeline on a real video. A flat ~0.5 line
   means the model can't see it; that step needs boxes.
3. Judge step times against frame sheets at 0.5 s or finer. A 1 fps sheet hid a whole second cycle
   in the new video.

**Scratch tooling** (session scratchpad `…/b76c5e62-…/scratchpad/vqa/`, not in the repo):
`score.py` (question AUC/accuracy on the 55 boxed Slawosz frames, several answer methods),
`cache_answers.py` + `replay.py` (cache probabilities every 0.4 s, then replay the real engine
with plan tweaks in seconds), `crop_test.py`, `contention.py`.

**Blocked**: `pip install bitsandbytes` was refused by the permission system; ask the owner
before trying 4-bit models again. Qwen3-VL-4B is cached in the Hugging Face cache (~9 GB); with
CPU offload it was not a clear win (Checkpoint 34), so this is low priority.
