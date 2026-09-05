# Architecture (Phase 0)

## Current implementation status

The runnable MVP now spans the schema, perception, procedure, voice, React dashboard, and core I/O layers. The web service serves the React dashboard on port 5767 and runs live OpenCV capture, perception, and the procedure engine in a background session. Evidence evaluation supports polygon-backed `in_region` and `outside_of` rules. Phase 5 I/O provides RTSP/file/webcam capture, bounded MP4 segments retained by the web runner, and CRC-verified JSONL events.

The React Training Studio now adds local activity-package preparation around the same contracts. It
supports guided plan authoring, video and CSV/Excel ground truth import, browser keyframe labels,
manual-label application to YOLO datasets, session-level split metadata, dataset quality reports,
background training and held-out evaluation, and a checksummed human-approved release gate. The
red/blue package remains the regression demo; complex activities are configured through their own
validated package plans.

The plan-driven color sequence recognizer has been validated on the supplied red/blue sorting video, including ordered timestamped events and CUDA device selection. The React dashboard presents frames through a continuous MJPEG endpoint while polling telemetry separately, so display cadence is independent of inference. The training workflow now accepts a folder of videos, creates video-level YOLO splits, proposes red/blue labels, provides a local drag-box labeler, and validates the dataset before CUDA-aware fine-tuning. The remaining hardware-dependent work is recording representative red/blue experiment takes, labeling them, and fine-tuning the detector. ONNX export and PyInstaller packaging are deployment steps after a trained model is available. The learned temporal head, 3D HMR, and Jetson target remain parked.

## 5 layers + 2 cross-cutters

```
Layer 5: React dashboard + Python web service — Phase 6
Layer 4: Voice (pyttsx3) — Phase 4
Layer 3: Procedure engine (YAML FSM + confidence smoothing) — Phase 3
Layer 2: Temporal model (v0: rule-only; v1: learned head) — Phase 3 / 9
Layer 1: Perception (YOLOv11-n, pose, hands, HOI) — Phase 2
Layer 0: I/O (capture, RTSP, MP4, JSONL) — Phase 5
```

Cross-cutters:
- **Schema** (YAML step-graph, JSONL event schema) — both swappable without code.
- **Packaging** (ONNX export, PyInstaller) — Jetson-ready later.

## Phase 2 deliverable (this commit)

- `bas_har/procedure/evidence.py` — `EvidenceAccumulator`; per-rule consecutive-match counting.
- `bas_har/procedure/smoothing.py` — `StepSmoother` (EMA + transition cooldown), `PauseWatchdog`, `RateLimiter`, `SilenceWindow`, `RecentEvents`.
- `bas_har/procedure/alerts.py` — `Alerter` with two-stage filter (confidence + persistence), rate limit, silence window, listener hook.
- `bas_har/procedure/events.py` — `JsonlEventSink` (atomic-rename on close).
- `bas_har/procedure/engine.py` — `ProcedureEngine` FSM; consumes `PerceptionResult`, emits `EventRecord` via the sink. Has `silence()`, `close()`, and an `EngineOutput` summary.
- `scripts/replay_motor.py` — `replay-motor` CLI; DSL script (`grasp:obj x30`, `wait:5`, `silence`) feeds mocked `PerceptionResult`s through the engine.
- `scripts/run_engine.py` — `run-engine` CLI; real MP4/webcam + real `PerceptionPipeline` + real engine. Hot path.
- `scripts/samples/red_blue_box_golden.txt`, `scripts/samples/red_blue_box_skip.txt` — sample scripts.
- `tests/test_procedure_engine.py` — 8 tests: golden path, skip detection, pause/resume, silence, rate limit, sink atomicity.

## Phase 2 smoke results

- `replay-motor experiments/red_blue_box/experiment_plan.yaml scripts/samples/red_blue_box_golden.txt`
  → all 6 steps transition in order, no alerts.
- `replay-motor … scripts/samples/red_blue_box_skip.txt`
  → SKIP_DETECTED alert fires within 2 frames of the actor reaching the later step.
- `run-engine experiments/red_blue_box/experiment_plan.yaml Downloads/Man_sorting_blocks_in_box_202609030054.mp4 --max-frames 60`
  → 5.5 fps on CPU, 0 detections (COCO doesn't know "small_red_box"), 0 transitions (expected).

## Phase 1 deliverable (this commit)

- `bas_har/perception/types.py` — `PerceptionResult`, `Detection`, `PoseKeypoints`, `HandKeypoints`, `HandObjectInteraction`, `BBox` dataclasses; JSON-serialisable.
- `bas_har/perception/detector.py` — YOLOv11-n wrapper; auto-picks `models/yolo11n.pt` if present, else downloads.
- `bas_har/perception/pose.py` — MediaPipe Pose Landmarker (33 keypoints).
- `bas_har/perception/hands.py` — MediaPipe Hands (21 keypoints/hand).
- `bas_har/perception/hoi.py` — proximity + velocity heuristic for HOI labels.
- `bas_har/perception/pipeline.py` — composes the four above per frame.
- `scripts/record_dataset.py` — tiny recorder; webcam OR MP4 file input, auto-numbered takes, sidecar `session.json`. Replay-friendly.
- `scripts/prepare_dataset.py` — samples a folder of takes into video-level YOLO splits and a JSONL frame manifest, with optional color proposals.
- `scripts/annotate_dataset.py` — local OpenCV drag-box labeler for completing and correcting YOLO labels.
- `scripts/preview_perception.py` — annotated live preview with optional JSONL dump.
- `scripts/smoke_perception.py` — offline smoke test against an MP4 (e.g. `Man_sorting_blocks_in_box_202609030054.mp4`).
- `tests/test_perception.py` — 9 tests (dataclass round-trip, HOI heuristic, model load).

## Smoke result (Phase 1 sanity)

Running `smoke_perception.py` on the demo video (`Man_sorting_blocks_in_box_202609030054.mp4`,
240 frames, 24 fps, 1280×720):

- 6.4 fps on CPU. Will be ~10× on RTX 5050 GPU; fine for the skeleton.
- COCO `box`/`cup`/etc. find 0 boxes (close-up of hands; classes don't match).
  Confirms fine-tuning is required.
- Hands 2/2 every frame; pose intermittent (subject is mostly cropped).
- HOI = 0 (no detections means no nearest object).

Conclusion: pipeline wiring works end-to-end; next step is **recording real takes**
of the red/blue box experiment to fine-tune the detector.

- `bas_har/schema/plan_schema.py` — Pydantic models for `experiment_plan.yaml`.
- `bas_har/schema/event_schema.py` — Pydantic models for the JSONL event log.
- `bas_har/schema/cli.py` — `validate-plan` command. Loads, lints, summarises.
- `bas_har/config.py` — runtime paths and env.
- `experiments/red_blue_box/experiment_plan.yaml` — the demo plan.
- `experiments/red_blue_box/notes.md` — recording protocol.
- `tests/` — 32 tests covering valid + invalid cases for every Pydantic model and the CLI.

## Design rules baked into the schema

- **One step = one evidence signature bundle.** Each step has ≥1 evidence rule;
  transition fires only when *all* rules in the step have been satisfied for
  their `min_frames`. This is the v0 procedure engine's only transition rule.
- **Branching is explicit.** `step.next: [step_a, step_b]` declares valid
  successors. The validator fails on unreachable steps and on `next` refs to
  non-existent ids.
- **YAML is the only place experiment knowledge lives.** No string literals
  like `"open box"` in Python; if you find one, it belongs in the YAML
  evidence rules and a HOI label set.
- **`extra="forbid"` on every Pydantic model.** Typos in YAML fail loud.
- **StrEnum for status / alert codes.** Easy to serialise to JSON, easy to diff.

## What's deliberately deferred (Phase 9+)

- 3D HMR (HMR 2.0 / SMPL-X), rack-relative coordinates, orientation-diverse augmentation as a first-class feature.
- Learned temporal head on top of the rule engine.
- Jetson Orin Nano/NX bring-up, TensorRT, INT8 quantisation.
- Multi-astronaut tracking, federated learning, AR overlay.

## How to run the Phase 0 checkpoint

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\validate-plan experiments\red_blue_box\experiment_plan.yaml
```

All three should pass. The last command prints the full plan in human-readable
form so a non-programmer can confirm "yes, this is the experiment".

## Current activity intake

The latest user-provided MELFI video is staged as a separate local activity package at
`activities/cold_stowage_melfi/`. Its validated procedure contains eight overview steps and its
uploaded take is `studying_cells_in_space-c2dce8af89`. The Studio-probed video metadata is 153.04
seconds, 25.0065 FPS, and 768x432; the activity camera profile is aligned to 25 FPS and 768x432.
Eight ground-truth timeline records now cover the complete
0.0–153.04 seconds after inspection of the astronaut/computer segment and ESA end card. No visual
annotations, dataset, model, evaluation report, or release has been created for this activity.

The analyser's reported media metadata is not authoritative. The uploaded take probe is the source
of truth. The surrounding ISS hardware in the tail segment was not assigned a MELFI label without
direct evidence. Contextual classes such as logos and title cards are currently present in the
plan, so they must be labelled consistently or removed from the detector plan before the quality
gate.
