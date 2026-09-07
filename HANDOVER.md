# Handover — bas-har

**Repo**: `C:\Users\Parth\Desktop\HAR_for_BAS`
**Authoritative spec**: `docs/SIH26174_AI_HAR_BAS_TechnicalDoc_v1.0_2026-08-27.docx` (in `C:\Users\Parth\Downloads`)
**Mission**: SIH26174 — AI HAR for on-board BAS experiments (ISRO, Gaganyaan/BAS-01 2028).
**Branch you'll be picked up from**: main.
**Last verified state**: 115 pytest passing, `ruff check` and formatting clean, React dashboard build and smoke pass, SIH PDF rendered and visually checked. The React Training Studio contains a separate MELFI activity with one uploaded take, an eight-step plan, and eight imported timeline records covering the full take; visual annotation has not started.

---

## 1. How to run

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[perception,streaming,voice,packaging,dev]"

# Validate the demo plan
.\.venv\Scripts\validate-plan experiments\red_blue_box\experiment_plan.yaml

# Start the React dashboard with the Downloads MP4
cmd /c startup.bat web

# Start with a webcam, MP4, or RTSP source
cmd /c startup.bat live 0

# Run the engine + real perception on a video
.\.venv\Scripts\run-engine experiments\red_blue_box\experiment_plan.yaml `
    "C:\Users\Parth\Downloads\Man_sorting_blocks_in_box_202609030054.mp4" --max-frames 60

# Run the engine with mocked perception (text DSL)
.\.venv\Scripts\replay-motor experiments\red_blue_box\experiment_plan.yaml `
    scripts\samples\red_blue_box_golden.txt

# Run all tests
.\.venv\Scripts\python.exe -m pytest -q

# Lint
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

**Python**: pinned to `<3.14,>=3.11` because MediaPipe 0.10.x caps at 3.13 and we pin
`mediapipe==0.10.21` (the 1.x line removed `mp.solutions`). See `pyproject.toml`.

**Console script entry points** (defined in `pyproject.toml`):
- `bas-har` — placeholder, prints version (`python -m bas_har`)
- `validate-plan` — `validate-plan <yaml>...`
- `record-dataset` — webcam OR MP4 recorder
- `preview-perception` — annotated live preview
- `replay-motor` — DSL-driven mocked engine run
- `run-engine` — real MP4/webcam + real perception + real engine
- `run-gui` / `run-web` — React dashboard server on port 5767

---

## 2. What's done

| Phase | Status | Notes |
|---|---|---|
| 0 — Schema + validator + demo plan | done | `bas_har/schema/`, `experiments/red_blue_box/experiment_plan.yaml`, `validate-plan` CLI |
| 1 — Perception pipeline | done | YOLOv11-n + MediaPipe Pose + Hands + HOI heuristic, ONNX-ready, `models/yolo11n.pt` cached |
| 2 — Procedure engine | done | FSM, evidence evaluator, two-stage alert filter, JSONL sink; **works on a real MP4** via `run-engine` |
| 3 — Region polygons / advanced evidence | done | `region_geometries` is schema-validated; `in_region` and `outside_of` evaluate BBox geometry in `bas_har/procedure/evidence.py`; demo YAML uses the restored rules |
| 3a — Voice (TTS) | done | `bas_har/voice/tts.py` uses a queue+thread and shutdown handling; `voice` extra installs pyttsx3; TTS is enabled by default with `--no-tts` as opt-out |
| 3b — React dashboard | done | `web/` plus `bas_har/web/server.py`: live frame, current step, telemetry, event stream, source controls, and port 5767 service |
| 4 — IO (RTSP + MP4 circular buffer + CRC) | done | Web capture uses `VideoCaptureSource`, retains bounded MP4 segments, and writes CRC-verified JSONL events |
| 5 — 3D HMR / Jetson / learned temporal head | NOT done (parked) | (renamed to Phase 9 in the plan) |
| 6 — SIH idea submission docs | done | `output/pdf/SIH26174_AI_HAR_BAS_submission.pdf` |
| 7 — Packaging (ONNX export + PyInstaller) | partial | `train-yolo`, `prepare-yolo-dataset`, `annotate-yolo`, and `export-onnx` CLIs are ready; the React PyInstaller bundle is verified, while a trained model bundle remains |

**115 pytest passing.** `ruff check` and `ruff format --check` both clean. The React build and web smoke pass.

The supplied video `Man_sorting_blocks_in_box_202609030054.mp4` is accepted by the plan-driven color sequence recognizer. It completes all six expected steps with events at 0.791s, 1.916s, 3.333s, 4.458s, 5.458s, and 6.875s. The run uses `cuda:0` for the YOLO path and writes a CRC-verified JSONL event log.

Each completed event also calls the asynchronous Windows `ConfirmationSound` worker once, producing a short ping without blocking capture or inference.

---

## 3. Architecture (5 layers + 2 cross-cutters)

```
Layer 5: React dashboard + web service [done]
Layer 4: Voice (pyttsx3)              [done, TTS optional]
Layer 3: Procedure engine (FSM+YAML)  [done]
Layer 2: Temporal model               [v0: rule-only; v1: learned head — future]
Layer 1: Perception (YOLO+pose+hands) [done]
Layer 0: I/O (capture, RTSP, MP4)     [done]
```

Cross-cutters:
- **Schema** (YAML step-graph, JSONL event schema) — both swappable without code.
- **Packaging** (ONNX, PyInstaller) — React server bundle verified; trained-model bundle remains.

---

## 4. Critical files to read first

1. `HANDOVER.md` — current state, conventions, and next action.
2. `AGENTS.md` — AI-assistant conventions (Ruff, no comments, schema-first, Python pin, etc.).
3. `docs/architecture.md` — phase architecture and boundaries.
4. `docs/validation_matrix.md` — current pass/fail table.
5. `docs/risk_register.md` — known issues and mitigations.
6. `bas_har/schema/plan_schema.py` — the YAML schema contract.
7. `bas_har/procedure/engine.py` — the FSM brain.
8. `web/src/App.jsx`, `web/src/TrainingStudio.jsx`, and `bas_har/web/server.py` — the active React shell, Studio, and service.

---

## 5. Key design decisions (locked)

- **Demo**: red/blue box experiment from the SIH PS, 6 steps. YAML is the single source of truth; `experiments/cfe_vane_gap/` is a swap-in path (just write a new `experiment_plan.yaml`).
- **Authoritative spec**: Tech Doc v1.0 (27 Aug 2026). Strategic Research doc's terminology ("orientation-diverse augmentation") is preferred over "microgravity simulation".
- **Edge target**: laptop (RTX 5050 8GB) for now. Jetson is parked.
- **3D HMR**: parked (not imported). Future work.
- **Sequence engine**: rule/procedure engine (FSM over YAML) primary. Learned temporal head is the explicit v2.
- **No comments in code** (per AGENTS.md).
- **No ML deps in core `dependencies`**; ML lives under `perception` extra. `pyproject.toml` is the source of truth for what's installable.
- **YAML rule kind**: discriminated literal (`kind: hand_object_interaction | object_visible | object_state | object_location | actor_visible`), not a Pydantic Union, so the YAML reads cleanly.

---

## 6. Known issues / unfinished corners (check before major work)

1. **Real detector validation still needs representative red/blue takes.** The provided sorting video opens and is processed end to end, but COCO-pretrained YOLO does not contain the demo's red/blue box classes. Record and label representative takes before fine-tuning.

2. **The web capture path is CPU-heavy with the current perception stack.** The dashboard remains usable for MP4 validation, while RTX 5050 benchmarking and model tuning remain hardware-dependent.

3. **A trained model bundle is still required for deployment packaging.** The generic PyInstaller React server is verified, but ONNX export and the final model asset should follow detector fine-tuning.

4. **MediaPipe 0.10.21 + opencv-python<5 + numpy<2** is the only working combo on 3.11. If anyone bumps Python to 3.13+, they'll need to migrate `bas_har/perception/pose.py` and `bas_har/perception/hands.py` to the new `mediapipe.tasks` API.

5. **The dashboard polls status every 700 ms.** A completed MP4 remains visible as the last annotated frame and reports `Source complete`; a future UI iteration could add replay controls.

6. **The replay engine is monotonic-time-based for pause/silence tests.** The pause test uses `time.sleep(pause_tolerance_s * 1.5)` — make sure the test runs at expected speed.

7. **`scripts/smoke_gui.py`** is now a compatibility alias for the headless React/web smoke test. Use `scripts/smoke_web.py` for the active dashboard.

8. **The `engine.py` `_pick_next` resets accumulator state for candidate steps.** This is the right behavior for the transition path but means each frame resets the persistence counter. The skip path's `_find_later_step_match` does NOT reset, so skip detection has continuous persistence. If you change the engine, keep this asymmetry in mind.

9. **YOLOv11n's class labels are COCO-pretrained**; the red/blue/big box classes are NOT in COCO. Once you record real takes and fine-tune, swap the model path in `bas_har/perception/detector.py` (or via `--yolo-model` on `preview-perception` / `run-engine`).

10. **The MELFI timeline was initially incomplete.** The final 48.04 seconds were reviewed from
    the actual video and added as two evidence-backed records: astronaut/computer activity through
    143.04 seconds and the ESA end card through 153.04 seconds. The surrounding station hardware
    remains deliberately unclassified.

11. **The analyser metadata was inaccurate.** The Studio measured 25.0065 FPS and 768x432 for
    `studying cells in space.mp4`, not the analyser's 29.97 FPS and 1920x1080. Uploaded-take
    metadata is authoritative.

12. **The MELFI plan includes contextual classes.** `nasa_logo`, `esa_logo`, and `title_card` are
    currently in the detector-class list because they are referenced by the supplied procedure.
    If they are not manually boxed, the quality gate will report missing classes. Decide whether
    they should remain detector targets or be moved to non-detector scene metadata before quality
    checking.

---

## 7. Test inventory

```
tests/
  conftest.py
  test_cli.py                    (6 tests — validate-plan CLI)
  test_config.py                 (4 tests — runtime paths)
  test_deployment_cli.py         (4 tests — training/export command surfaces)
  test_engine.py                 (2 tests — engine surface)
  test_event_schema.py           (5 tests — EventRecord)
  test_evidence.py               (3 tests — polygon evidence)
  test_io.py                     (7 tests — capture, buffer, CRC)
  test_io_schema.py              (4 tests — I/O configuration)
  test_perception.py             (9 tests — types, HOI heuristic, model load)
  test_plan_schema.py            (20 tests — Pydantic schema)
  test_procedure_engine.py       (7 tests — golden, skip, pause, silence, rate limit, sink)
  test_sequence.py               (2 tests — color sequence recognizer)
  test_training_pipeline.py      (3 tests — video extraction and auto-labeling)
  test_voice.py                  (2 tests — TTS and confirmation workers)
  test_web.py                    (3 tests — web service surface and MJPEG stream)
```

Total: 115 tests. All passing as of this handover. The continuation adds coverage in
`test_activity_schema.py`, `test_activity_registry.py`, `test_annotations.py`, `test_datasets.py`,
`test_evaluation.py`, `test_jobs.py`, `test_quality.py`, `test_releases.py`, `test_takes.py`,
`test_timeline.py`, and `test_web.py`.

---

## 8. Where the dashboard smoke proves things work

```
# Active headless smoke check:
.\.venv\Scripts\python.exe scripts\smoke_web.py
```

---

## 9. Historical next chunks before the React migration

The list below is retained for historical context only. It is superseded by the current status in
Sections 12–16 and must not be treated as an open task list.

The user wants the **fastest working prototype / MVP**. Per the locked decisions:

1. Live capture is implemented by the React web service; the old PySide6 path is removed.
2. The `voice` extra and default TTS behavior are implemented.
3. Region geometry and `in_region`/`outside_of` evidence are implemented and tested.
4. Phase 5 I/O, SIH submission documentation, and React PyInstaller packaging are implemented.
5. Real model training still depends on user-labelled, independent activity sessions.
6. Phase 9 remains parked: 3D HMR, Jetson bring-up, and learned temporal head.

---

## 10. Conventions the next agent MUST follow (from AGENTS.md)

1. No comments unless asked. Code reads like prose.
2. Schema-first: any new feature starts with a Pydantic model in `bas_har/schema/`.
3. YAML is the only place experiment-specific knowledge lives. No hard-coded class names in Python.
4. No ML deps in core `dependencies`; use the `perception` extra.
5. Tests mandatory for every public function. No `_` prefixes unless private.
6. Python `<3.14` only (per `pyproject.toml`).
7. `pathlib.Path` only, no `os.path.join`.
8. Ruff clean. Run `ruff check .` and `ruff format .` before any commit.
9. Type hints on every public function.
10. Use `loguru.logger`, not `logging.getLogger`.
11. Specific exceptions, never bare `raise Exception`.
12. f-strings, double quotes.
13. Imports: stdlib → third-party → local, one blank line between groups.
14. `pytest -q` and `ruff check .` must both pass before handing back.

---

## 11. Quick smoke test (one liner)

After any change, run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q ; .\.venv\Scripts\python.exe -m ruff check .
```

Both should be silent (no failures, no errors). If you only changed docs / docs-only, pytest still runs all 49 and they should all still pass.

## 12. Current state after MVP continuation

The older phase and issue notes above are historical. The following items are now implemented:

- React dashboard uses a Python background capture session and serves the Vite build on port 5767.
- The `voice` extra installs pyttsx3, and TTS is enabled by default with `--no-tts` as the opt-out.
- `region_geometries` is part of the plan schema, and `in_region` plus `outside_of` evidence is evaluated against BBox geometry.
- The red/blue plan contains table geometry and the restored placement, location, and visibility rules.
- Phase 5 I/O covers webcam, file, and RTSP capture, rotating MP4 segments in the web runner, and CRC-verified JSONL events.
- `prepare-yolo-dataset` extracts sampled video frames, performs deterministic video-level splits, and proposes red/blue labels; `annotate-yolo` is a local drag-box labeler; `train-yolo` selects CUDA automatically and validates dataset completeness before training; `export-onnx` exports the trained model.
- The React Training Studio creates local activity packages, imports videos and CSV/Excel timelines,
  reviews sampled keyframes with drag-box labels, runs dataset quality checks, and persists split
  session membership.
- Manual browser labels are applied to YOLO data, including frames outside the automatic sample
  interval. Held-out evaluation produces metrics and a failure gallery; passed reports can create
  checksummed candidates that require explicit reviewer approval before activation.
- Activity dataset preparation assigns whole recording sessions, not individual videos, to splits;
  this prevents session leakage in the normal Training Studio workflow.
- `packaging/bas_har_gui.spec` builds the React server executable; `dist/bas-har-web.exe` has passed packaged HTTP health and static-page checks.
- The test suite currently passes 115 tests and Ruff plus formatting are clean.
- The dashboard video feed uses `/api/stream.mjpg` for continuous frames while telemetry remains independently polled.
- The plan-driven color sequence recognizer accepts the supplied red/blue sorting video and emits six CRC-verified timed events. The verified run uses `cuda:0` at 42.5 FPS.
- Each successful step emits one asynchronous confirmation ping through the Windows audio device; the confirmation worker shuts down with the capture session.
- `startup.bat analyze "C:\Users\Parth\Downloads\Man_sorting_blocks_in_box_202609030054.mp4"` runs the full checks and sequence acceptance test.
- The system `py -3.11` launcher was unusable on this machine; the current `.venv` was created from the installed uv-managed CPython 3.11.9 runtime.

The next safe work is using the Training Studio to collect representative takes, complete browser
labels, run CUDA fine-tuning, evaluate held-out sessions, and approve a release. 3D HMR, Jetson,
and learned temporal modeling remain parked by decision.

## 13. React dashboard continuation

The active UI is now a React dashboard served at `http://127.0.0.1:5767`. `web/` contains the Vite source and production bundle. `bas_har/web/server.py` serves the bundle and exposes plan, status, event, frame, start, stop, and silence endpoints. Capture, perception, and the procedure engine run in a background session, with the annotated latest frame available at `/api/frame.jpg`.

The PyInstaller React bundle was built and smoke-checked as `dist/bas-har-web.exe`; its packaged root page and health endpoint respond correctly on a temporary port.

`startup.bat` builds the web bundle when needed, runs pytest, Ruff, plan validation, and the web smoke test, then starts the dashboard. The default and `web`/`video-gui` modes use `%USERPROFILE%\Downloads\on cell.mp4` when present. `live` accepts a webcam index, MP4 path, or RTSP URL. The current verified screenshot is `output/screenshots/bas_har_react_on_cell.png`.

The old PySide6 UI was removed. The compatibility names `run-gui`, `run-web`, and `smoke_gui.py` now point to the React dashboard server or its smoke check. PySide6 is not a project dependency.

## 14. Training Studio continuation plan

The approved plan for the next major work is saved in `docs/training_studio_plan.md`. The
cross-session implementation checkpoint and progress rules are saved in `docs/progress_log.md`.

The target is a local-first React Training Studio inside the existing port-5767 dashboard. It
supports generic activity packages for experiments, maintenance, training, and exercise. Users
create a validated YAML procedure with a guided builder, drag in videos, import timestamped Excel
or CSV ground truth, review AI-assisted visual labels, train on the laptop RTX 5050, evaluate on
unseen session-level test videos, and manually approve a release before Operations can use it.

Schema-first activity/package contracts, registry plumbing, browser import, annotation, background
training/evaluation, and the manual release gate are implemented and covered in
`docs/progress_log.md` Checkpoints 1–6. Package verification and approved activity selection are now
also implemented. The next implementation is offline/replay hardening and generic package evidence
adapters. The red/blue tracker remains a regression adapter only. `object_state` must be implemented
before activities depending on it can be approved. 3D HMR, Jetson, and the learned temporal head
remain parked.

The user-provided activity package has since been recreated through Training Studio and staged for
annotation. Its procedure and eight-row timeline are saved, the take is uploaded, the dataset is
prepared, and the full-video keyframe reviewer is open. The next action is drawing detector boxes;
training remains blocked until labels and independent recording sessions satisfy the quality gate.

During this intake, a stale-file race in the background training and evaluation job listings was
fixed: durable queued records can no longer overwrite a newer in-memory running or failed state.
The full `startup.bat test` gate and React production build pass after the fix.

The STEP 05 annotation keyframe strip was replaced with a compact frame dropdown. Each option shows
its timestamp and saved-label count, and selecting a frame loads it without horizontal scrolling.
The default sampling interval is 30 frames so the current 103-second take remains fully selectable
after refresh. The current package remains staged for annotation; the next exact action is drawing
and saving detector boxes for the visible classes.

Saving a STEP 05 box now automatically loads the next frame. When a draft box is present, pressing
`Enter` performs the same save-and-advance action; the annotation image takes focus when drawing so
the shortcut works immediately after choosing a label. The button and status text show this shortcut.
Frame dropdown navigation now normalizes backend numeric IDs against HTML select string values and
keeps frame zero visibly selected, so moving forward or backward no longer clears the annotation
editor.

This fix was live-verified by navigating from 0.00s to 1.20s and back to 0.00s. Existing saved
annotations were not changed.

STEP 05 frame options now use a high-contrast dark color scheme with readable text and a distinct
selected state to prevent the native dropdown from appearing washed out.

The current concrete-hardening take has been audited and its dataset regenerated: 87/87 sampled
keyframes have valid, non-duplicate boxes and all six planned classes are represented. The quality
gate is FIX only because there is one recording session, so all 517 images are in train and val/test
are empty. Add at least two independent sessions, annotate them, regenerate `dataset_v1`, and rerun
the quality gate before treating training or evaluation as reliable.

The current training result is not a model: two CUDA-resolved laptop-safe attempts stopped at 5%
because no validation images existed. No weights or evaluation report were produced. Do not report
this as successful training. If a one-video prototype is desired, it requires an explicit frame-level
split mode and its metrics must be labeled as leakage-prone.

The prior visual annotations were intentionally cleared on 2026-09-06 at the user's request. The
activity plan, uploaded video, recording session, and all eight ground-truth timeline rows were
verified as preserved. The Training Studio view was reset and is ready to annotate from frame one.

## 15. Current MELFI activity intake

This section supersedes the concrete-hardening intake details above when resuming the latest user
task.

- Activity: `cold_stowage_melfi` — `Cold Stowage and MELFI Operations`.
- Package path: `activities/cold_stowage_melfi/`.
- Procedure: `Cold Stowage and MELFI Overview`, eight validated steps.
- Objects/classes: `interviewee`, `melfi_freezer`, `dewar_compartment`, `sample_container`,
  `control_panel`, `astronaut`, `computer`, `nasa_logo`, `esa_logo`, and `title_card`.
- Take: `studying_cells_in_space-c2dce8af89` from `studying cells in space.mp4`.
- Recording session: `cold_stowage_melfi_session_001`.
- Studio-probed metadata: 153.04 seconds, 25.0065 FPS, 768x432.
- Activity camera profile: 25 FPS, 768x432, aligned to the verified take.
- Ground truth: eight imported records, covering 0.0–153.04 seconds.
- Visual annotations: zero; the package is waiting for manual boxes in STEP 05.
- Dataset: not prepared for this activity; training and evaluation have not started.

The analyser supplied 153.0 seconds, 29.97 FPS, and 1920x1080, but the Studio probe is the source
of truth for the uploaded file. The final interval was inspected from the video before the two
additional records were added. The surrounding ISS hardware is not identified as MELFI without
direct evidence.

The next exact action is to select this activity in the React Studio and draw and save boxes for the
chosen detector classes. After labels are complete, add independent recording sessions before
preparing the dataset and starting CUDA training. The current plan includes logo/title classes;
either label them consistently or remove them from the detector plan before running the quality gate.

## 16. Documentation state

`docs/architecture.md`, `docs/validation_matrix.md`, `docs/risk_register.md`, and
`docs/progress_log.md` must be read together with this handover. The historical sections are kept
for traceability, while the latest checkpoint and unresolved risks are recorded in the final
sections of each document.

## 17. Collaborator handoff

The repository is prepared for a second person to annotate the MELFI activity. Start with
training_guide.md for setup and exact Studio actions, then use dataset_progress.md for the
current data inventory and the remaining annotation and training work. The collaborator's first
task is to box the take studying_cells_in_space-c2dce8af89 in STEP 05. There are currently zero
MELFI annotations, no MELFI dataset, and no MELFI training result. After annotation, the quality
gate must pass with independent recording-session splits before a baseline can be evaluated.
