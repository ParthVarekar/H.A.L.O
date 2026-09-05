# BAS-HAR Activity Training Studio Plan

## Purpose

BAS-HAR will become a local-first React workspace for preparing, training, validating,
approving, and operating computer-vision activity packages. The supported activity types are
space experiments, maintenance, astronaut training, exercise, inspections, and future BAS
procedures. The red/blue box remains a regression demo and is not a special-case product model.

The user supplies the approved procedure, videos, and timestamped ground truth. The system turns
those inputs into versioned activity packages and compares model output with unseen labeled takes
before a package can be used in Operations.

## Locked product decisions

- UI: React dashboard at `http://127.0.0.1:5767` with Operations and Training Studio workspaces.
- Storage: local-first on the laptop; no cloud, accounts, or network service in the first release.
- Authoring: guided procedure builder that generates a validated YAML plan.
- Models: one package-specific model per activity initially.
- Camera: one fixed calibrated camera profile per activity package.
- Annotation: AI-assisted visual-label review; the user corrects proposals on selected keyframes.
- Evaluation: automatic session-level video split, default 70% train, 20% validation, 10% test.
- Release: human approval is always required; metrics never activate a package automatically.
- Runtime: advisory tone/TTS and UI guidance only; no autonomous physical control.
- Procedure: the model loads an approved procedure; it never invents mission steps from an activity
  name.
- Primary engine: YAML procedure FSM with perception evidence. A learned temporal head remains v2.
- Parked: 3D HMR, Jetson/TensorRT bring-up, multi-astronaut tracking, AR overlays, and federated
  learning.

## Ground-truth input

The Studio will accept an Excel workbook and CSV export. The downloadable workbook will contain:

- `Activity`: activity identity, category, version, camera profile, author, reviewer, and notes.
- `Takes`: video ID, filename, recording-session ID, actor pseudonym, camera profile, and notes.
- `Timeline`: video ID, start time, end time, expected step ID, observed action, result, object
  IDs, region IDs, and notes.
- `Deviations`: optional deliberate incorrect, incomplete, skipped, or out-of-order examples.

Accepted times are seconds or `HH:MM:SS.mmm`. Results are `completed`, `incomplete`, `incorrect`,
`skipped`, `out_of_order`, or `uncertain`. The workbook is a user-facing interchange format;
validated Pydantic records and append-only JSONL remain the machine source of truth.

Timestamp labels evaluate step timing and sequence. Object/state recognition also needs visual
labels, so the Studio will generate detector proposals and ask the user to review boxes, regions,
states, and keyframes where required.

## Activity lifecycle

```text
draft -> imported -> annotated -> trained -> evaluated -> approved -> active -> retired
```

Only `approved` or `active` releases can be selected by Operations. A release records its plan,
model, dataset, camera profile, evaluation report, configuration, and checksums.

## Package layout

```text
activities/<activity-id>/
  activity.yaml
  plan.yaml
  takes.jsonl
  annotations.jsonl
  camera_profiles/
  takes/
  datasets/
  reports/
  releases/
```

Existing `experiments/red_blue_box` remains supported for regression compatibility. The guided
builder writes generic plans; the existing `ExperimentPlan` remains the procedure contract until
an additive activity-package schema is introduced and validated.

## Planned schema and engine additions

Add schema-first models for activity metadata, lifecycle state, video/take records, timeline
ground truth, visual annotations, dataset versions, training jobs, evaluation reports, and model
releases. Extend event records with run ID, activity/package/model versions, frame ID, and
video-relative time while preserving old fields.

Extend the procedure contract and engine with:

- explicit incomplete, incorrect, out-of-order, and uncertain outcomes;
- configurable failure conditions in YAML;
- timeout and source-end handling;
- generic object-state evidence;
- configurable pose evidence for training and exercise;
- persistent evidence, confidence filtering, and advisory alerts;
- package-driven target classes and thresholds.

The current color sequence tracker remains a demo regression adapter. Generic activity packages
use the normal package-driven perception pipeline and FSM. No experiment-specific class names or
step lists will be hard-coded in Python.

## Training Studio workspaces

1. Activity registry and guided procedure builder.
2. Drag-and-drop video import and Excel/CSV timeline import.
3. Video preview, timeline editing, and AI-assisted keyframe annotation.
4. Object boxes, regions, object states, hand-object labels, and pose labels.
5. Dataset quality checks and session-level split preview.
6. Background GPU training with progress, logs, cancellation, and hardware telemetry.
7. Held-out evaluation with metrics, timing comparisons, failure gallery, and report export.
8. Manual release approval and package checksum verification.
9. Operations activity selection, next-step guidance, alerts, and audit export.

## Training and evaluation policy

Training jobs run on the RTX 5050 through CUDA when available. Laptop-safe presets use mixed
precision, conservative workers, adaptive batch sizing, and no RAM-heavy dataset caching. CPU is
available only as an explicit fallback.

Whole recording sessions, never individual frames, are assigned to splits. Fewer than three
independent sessions cannot produce an independent validation split. Fewer than ten sessions are
reported as insufficient for a robust release even though prototype training and evaluation may
run.

Reports include detector metrics, step precision/recall/F1, order accuracy, timestamp error,
missed deviations, false alerts, uncertainty, latency, FPS, GPU device, and VRAM. Existing
validation targets remain reference targets, but human release approval is mandatory.

## Runtime policy

After the astronaut or operator selects an approved activity, the service verifies the package,
loads its camera profile and models, displays the expected next step, and evaluates evidence as
the action begins. Runtime statuses are waiting, started, completed, incomplete, incorrect,
skipped, out-of-order, and uncertain.

Every event records UTC time, video-relative time, frame, activity and release identity, expected
step, observed status, confidence, evidence summary, alert code, and media reference. Events are
written to CRC-verified JSONL and exported to Excel/CSV for review.

Low confidence produces an unable-to-verify state rather than an invented failure. Confirmed
deviations may produce a short tone or offline TTS message with cooldown and persistence filters.

## Delivery order

1. Add schemas, activity registry, package storage, and compatibility tests.
2. Add Training Studio navigation, activity builder, and local video/timeline import.
3. Add assisted visual annotation and dataset-quality validation.
4. Run preparation/training scripts as background jobs with GPU telemetry.
5. Add held-out evaluation, reports, model release approval, and checksums.
6. Integrate approved packages into generic Operations and event exports.
7. Harden replay, offline behavior, packaging, and regression coverage.

## Acceptance criteria

- A new activity can be created without Python changes.
- Videos and the timestamp workbook can be imported through the browser.
- Invalid timestamps, missing steps, duplicate files, and malformed labels are rejected clearly.
- Visual proposals can be reviewed and corrected in the browser.
- Session-level leakage is impossible in the normal workflow.
- Training visibly reports CUDA device selection and resource use.
- Evaluation uses unseen videos and produces a human-readable report.
- Draft or failed packages cannot become active.
- Operations can select an approved activity and emit timestamped advisory events.
- The red/blue six-step regression remains passing.
- Complex activities can use package-defined objects, regions, states, hand actions, and pose evidence.
- Existing tests remain passing, new functionality receives schema/API/UI tests, React builds successfully, and both `pytest -q` and `ruff check .` remain clean.

## Explicit boundaries

- Local laptop only; no cloud or authentication in the first release.
- One fixed calibrated camera profile per activity package.
- One package-specific model per activity.
- Approved procedures are supplied by an expert; the model does not invent mission procedures.
- Deliberate error examples are supported and strongly recommended.
- 3D HMR, Jetson deployment, multi-astronaut tracking, AR overlays, and the learned temporal head remain parked.
