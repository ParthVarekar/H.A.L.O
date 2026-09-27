# Handover — bas-har

**Repo**: `C:\Users\Parth\Desktop\HAR_for_BAS`
**Authoritative spec**: `docs/SIH26174_AI_HAR_BAS_TechnicalDoc_v1.0_2026-08-27.docx` (in `C:\Users\Parth\Downloads`)
**Mission**: SIH26174 — AI HAR for on-board BAS experiments (ISRO, Gaganyaan/BAS-01 2028).
**Branch you'll be picked up from**: main.
**Last verified state (2026-09-15, see Section 18)**: 193 pytest passing, `ruff check` and formatting clean, React dashboard build and smoke pass. The `cold_stowage_melfi` activity holds the real MELFI video, is boxed (775 boxes/55 frames), has a trained detector installed, and completes all 8 steps in order on the source video through the real dashboard. The section below (7) predates that work and is retained for historical/phase context only.

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
| 6 — SIH idea submission docs | done | `docs/` |
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

`startup.bat` builds the web bundle when needed, runs pytest, Ruff, plan validation, and the web smoke test, then starts the dashboard. The default and `web`/`video-gui` modes use `%USERPROFILE%\Downloads\on cell.mp4` when present. `live` accepts a webcam index, MP4 path, or RTSP URL.

The old PySide6 UI was removed. The compatibility names `run-gui`, `run-web`, and `smoke_gui.py` now point to the React dashboard server or its smoke check. PySide6 is not a project dependency.

## 14. Training Studio continuation plan

The cross-session implementation checkpoint and progress rules are saved in
`docs/progress_log.md`. (The original planning document, `docs/training_studio_plan.md`, was
retired on 2026-09-16 once every item in it had been implemented or superseded; its history is
still visible in `docs/progress_log.md` and in git history.)

The target is a local-first React Training Studio inside the existing port-5767 dashboard. It
supports generic activity packages for experiments, maintenance, training, and exercise. Users
create a validated YAML procedure with a guided builder, drag in videos, import timestamped Excel
or CSV ground truth, review AI-assisted visual labels, train on the laptop RTX 5050, evaluate on
unseen session-level test videos, and manually approve a release before Operations can use it.

Schema-first activity/package contracts, registry plumbing, browser import, annotation, background
training/evaluation, and the manual release gate are implemented and covered in
`docs/progress_log.md` Checkpoints 1–6. Package verification and approved activity selection are now
also implemented. The next implementation is offline/replay hardening and generic package evidence
adapters. The red/blue tracker remains a regression adapter only. `object_state` (and the
`inside_of` containment rule) is now implemented — see Section 18 — and used by the MELFI plan.
3D HMR, Jetson, and the learned temporal head remain parked.

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

For a complete dated continuation brief, read `CLAUDE_CODE_HANDOVER.md`. It consolidates the
repository state, exact MELFI and Concrete Hardening inventories, command surface, architecture,
risks, parked work, and the required progress-log format.

## 18. Current state — 2026-09-15 (supersedes Sections 15-17 for MELFI)

Sections 15-17 above describe the MELFI activity as it stood before 2026-09-13; that take was the
wrong video (Life Sciences Glovebox footage, not MELFI) and has been moved intact to its own
activity, `studying_cells_lsg`, as a reference. `cold_stowage_melfi` now holds the real MELFI
video and is boxed, trained, and verified. Full detail is in `docs/progress_log.md` Checkpoints
27-32; the summary:

- **New MELFI video and plan.** `activities/cold_stowage_melfi/takes/slawosz_using_melfi-8821822197.mp4`
  (67.16 s, 25 fps, 768x432): ESA astronaut Slawosz stores a sample in MELFI during the Ignis
  mission. Plan v1.1.0 has 20 objects (including four numbered dewars, four numbered trays, a
  latch, a hatch, two compartments) and 8 steps, each one observable state change.
- **Object states and containment are now schema features**, added at the owner's request:
  `ObjectSpec.states` (e.g. `open`/`closed`, `in`/`out`, `left`/`right`) expand into per-state
  detector classes (`ClassName__state`), and `EvidenceRule.inside_of` mirrors the existing
  `outside_of` so a step can require one box mostly inside another (e.g. "sample inside the open
  compartment"). See `bas_har/schema/plan_schema.py` (`state_class`, `base_class`,
  `ObjectSpec.detector_classes`, `ExperimentPlan.detector_classes/class_states`) and
  `bas_har/procedure/evidence.py`.
- **Owner boxed 775 boxes on 55 frames themselves** through the Studio (Claude Code does not box
  MELFI — that was an explicit instruction). The Studio gained a state picker, a per-frame box
  list (redraw/delete/change state), per-class colours, a show/hide-labels toggle, and "copy boxes
  from previous frame"; `DELETE /api/activities/<id>/annotations/<annotation_id>` was added.
- **Checker fixes found by testing on the real video**: overlapping same-object boxes in different
  states now keep only the higher-confidence state (`resolve_state_conflicts`); step completion
  and skip/late-completion confirmation both need the evidence in >=80% of a short sliding window
  of frames rather than every frame in a row, so brief detector flicker or a single false positive
  no longer flips a result; a later step is confirmed only once it has persisted, and a step
  already satisfied at the very start (e.g. a closed hatch) is never mistaken for a completed step.
- **A detector was trained** (yolo11n, image size 768, **no horizontal flip** — flipping would
  swap dewar/tray quadrant numbers and left/right latch state) and installed at
  `activities/cold_stowage_melfi/models/detector.pt`. Held-out mAP50 0.79 on 11 frames the model
  never trained on; the installed model is trained on all 55 boxed frames, so its own numbers are
  not a fair held-out score — only the step-by-step behavior on the full video is evidence of
  real behavior.
- **Verified result**: running the full video through the real `ProcedureEngine` (via the
  dashboard, both by picking the activity manually and via automatic scene recognition) completes
  all 8 steps in order with zero alerts, each within about a second of the state-change time
  visible in the owner's own boxes.
- **Dashboard playback was slow (about 0.2x real time) and has been fixed.** `SessionRunner` is
  now three threads (analysis / presenter / recorder) so browser or disk work can never slow
  detection; uploaded video is paced to its own frame rate (`PlaybackClock`); the MJPEG stream is
  push-based (`WebState.wait_for_frame`) instead of polling; JPEG encoding uses nvjpeg on the GPU
  with an OpenCV fallback (`bas_har/web/frame_encoder.py`); the detector warms up before playback.
  Verified: 1.00x real-time factor, 25 fps delivered smoothly to a real browser client, unchanged
  step results. The dashboard shows a live speed readout and a red banner if it ever falls back to
  CPU with an NVIDIA GPU present.
- **Voice alerts were re-tuned twice** after the owner reported them lagging, then found silent
  (a leftover test mock had replaced the browser's speech engine — since removed), then asked for
  faster: step completions now use short merge-if-crowded phrases at 1.5x speed, alerts interrupt
  routine speech, and the dashboard also plays its own tones (a beep per step, a double tone for
  alerts) so audio doesn't depend on the server's own `winsound` beep being audible.
- **A manual "Experiment" picker** was added to the Operations dashboard: choosing an activity
  skips scene recognition and monitors it directly (`X-Activity-Id` header, `GET
  /api/analyze/activities`).
- **`close_startup.bat` and `close_training_studio.bat`** were added to stop exactly what each
  launcher started, without touching unrelated processes; each supports `--list` to preview.
- **Not yet done**: a second independent MELFI recording session (needed before any
  generalisation claim); the ice-vapour and fabric issue alerts (the owner said to build these
  after training, and will say when); wiring `fliplr=0` into the Studio's own training button for
  orientation-sensitive plans.

The test suite is at 193 passing (`pytest -q`), Ruff and formatting clean, React build clean, as
of this section.

## 19. Described-not-trained recognition — 2026-09-22

New capability, added on the owner's instruction to find a way around per-video training. It does
not replace anything: an activity with a trained detector behaves exactly as before.

- **How an activity enters zero-shot mode.** `_analyze_video` in `bas_har/web/server.py` checks
  for `activities/<id>/models/detector.pt`. Missing, but the plan's objects have `prompts` ->
  `SessionRunner(zero_shot=True)`. Missing and no prompts -> the old refusal message.
- **Open-vocabulary detection** (`bas_har/perception/open_vocab.py`): YOLOE with the MobileCLIP
  text encoder, given the plan's prompts via `ExperimentPlan.prompt_classes()`, which maps each
  prompt back to a plan class so evidence rules are unchanged. Needs `models/yoloe-11s-seg.pt` and
  `models/mobileclip_blt.ts` (the 600 MB encoder is gitignored; the loader chdirs to `models/` so
  Ultralytics can find it by its bare filename).
- **Frame questions** (`bas_har/perception/vlm.py`): `VisualQuestionAnswerer` wraps
  Qwen3-VL-2B-Instruct (Apache-2.0) and answers every active question about one frame in a single
  call. `AsyncVisualQuestioner` runs it on a background thread with a newest-frame slot and a
  latest-answers dict, so the analysis thread never waits; answers arrive as
  `PerceptionResult.questions` and persist until replaced. `_active_questions` narrows the list to
  the current and next steps each frame.
- **Schema**: `ObjectSpec.prompts`, evidence `kind: visual_question` with `question` and
  `expect: yes|no`. `expect` is not decoration — the model answers "is it open?" well and "is it
  closed?" close to randomly, so closing steps ask the same positive question and expect "no".
- **Engine**: `_state_change_pending` now keys on `visual_question` + `expect` as well as
  `object_state` (`_change_key`), otherwise a final step whose expected answer is already true at
  t=0 makes the engine declare everything skipped in the first seconds.
- **Two traps, both hit once and both in the risk register (26, 27)**: absence-phrased questions,
  and closing steps being satisfied by footage that contains none of the equipment. The second one
  produced a fake "8 of 8" before the equipment-visible guard was added.
- **Where it stands honestly.** On an unseen MELFI video: 5 of 8 steps, at the right times, with
  no false alerts and no spurious completions, at 1.0x real time on cuda:0 (detect 35.4 ms/frame,
  36 answers over 153 s). The trained detector scores 0 on the same video. Fine states are the
  weak part; steps 2 and 3 complete 0.12 s apart, which is not a real reading of two actions.
- **Next things worth trying** (not done): vote-smoothing across consecutive answers; Qwen3-VL-4B;
  restricting a zero-shot run to the video segment where the equipment is present; letting the
  Studio generate a first draft of prompts and questions from a step description.

Test suite 204 passing, Ruff and formatting clean, React build clean as of this section.

## 20. Described mode, second pass — 2026-09-23 (corrects Section 19)

Section 19 overstated two things: the new video (`studying cells in space.mp4`) holds **two** MELFI
cycles, not one, and the "equipment visible" guard never worked. Full detail and numbers are in
`docs/progress_log.md` Checkpoint 34.

- **Answers are probabilities now.** `VisualQuestionAnswerer.ask` pre-fills the JSON answer ("yes"
  in every slot, then "no" in every slot) and reads the yes-vs-no probability at each slot in one
  forward pass: ~0.4 s for a plan's 3-5 questions instead of 3-4 s of text generation, with the
  same calibration. Keep all of a plan's questions in one call; alone, each question is biased to
  "yes".
- **Dead band.** `question_verdict`: yes at >= 0.6, no at <= 0.4, unsure in between (matches
  nothing). The constants are `QUESTION_YES_MIN` / `QUESTION_NO_MAX` in `bas_har/procedure/evidence.py`.
- **No narrowing, no smoothing.** The questioner always asks the full set; smoothing was measured
  to delay short events and was removed.
- **Detector skipped when unused.** Zero-shot plans with only `visual_question` rules run no
  detector (`detections_needed`), which keeps analysis at 25 fps.
- **Hybrid mode** (`mode: hybrid`) = trained detector + questions. Verified live on the Slawosz
  video (8/8, no alerts, ~0.6 s later than trained-only). Cost: the detector slows to ~70-100
  ms/frame while the VLM runs; real time is kept by skipping frames.
- **`melfi_zeroshot` plan v0.4.0**: five visible-only steps, three questions, 0.4 s hold. Live on the
  new video: 5/5 during cycle 1, 1.4-2.3 s behind, no alerts, nothing during the glovebox footage.
- **Studio fix**: the procedure builder now keeps `expect` ("done when: yes/no"); before, re-saving
  a plan inverted any step whose first rule expected "no".
- **Blocked / not done**: Qwen3-VL-4B needs 4-bit quantisation to fit live in 8 GB, and installing
  `bitsandbytes` was refused by the permission system. Measured with CPU offload instead, it is
  better on Slawosz frames but worse on the new video's camera angle, so it is not a clear win.
- **Deployed v0.4.0 honestly**: new video 4/4 checkable steps; Slawosz 2/5 within 2.5 s, every miss
  early rather than random. Answers shift with the question set, so test plans exactly as deployed.

Test suite 207 passing, Ruff and formatting clean, React build clean as of this section.
