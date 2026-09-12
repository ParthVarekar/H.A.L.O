# Claude Code Handover — bas-har

Last updated: 2026-09-13

This is the authoritative continuation brief for Claude Code or another coding agent taking over
the repository. It records the project intent, current implementation, exact data state, verified
commands, known limitations, and the safest next actions. Read this file together with
HANDOVER.md; when they differ, this file's dated current-state sections and the files on disk are
the source of truth.

## 1. Repository identity

- Local path: C:\Users\Parth\Desktop\HAR_for_BAS
- GitHub remote: https://github.com/ParthVarekar/HAR_for_BAS.git
- Active branch: main
- Last known commit: 1a96e69, docs: prepare collaborator training handoff
- Last known remote branch: origin/main at 1a96e69
- Working tree at handoff: clean
- Application: React Training Studio plus Python HAR service
- Studio URL: http://127.0.0.1:5767/?workspace=studio
- Project mission: SIH26174 AI human activity recognition for on-board Bharatiya Antariksh
  Station experiments and operations

The project is not production-ready. It is an MVP and research/prototype pipeline with a working
schema, procedure engine, React annotation studio, replay/live service, dataset preparation,
quality gates, and training/evaluation plumbing. There is no trustworthy trained detector for the
MELFI activity yet.

## 2. What the owner wants next

The owner is handing the repository to a friend or coding agent so the friend can annotate the
second video. The second video is the Cold Stowage/MELFI video already stored in the repository.
The immediate human task is drawing bounding boxes in the React Studio. The immediate engineering
task after labels exist is quality-gate verification, session-level dataset preparation, CUDA
baseline training, and held-out evaluation.

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
7. docs/training_studio_plan.md
8. docs/progress_log.md
9. bas_har/schema/plan_schema.py
10. bas_har/procedure/engine.py
11. bas_har/web/server.py
12. web/src/App.jsx
13. web/src/TrainingStudio.jsx

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
activities can be approved: offline/replay hardening, generic package evidence adapters, and
object_state support. Do not implement activity-specific shortcuts as a substitute for those
generic contracts.

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
