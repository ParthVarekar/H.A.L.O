# Training Studio Guide

This guide is for a collaborator who will clone the repository, annotate the second video, and run a reproducible baseline training job.

The Training Studio is a local React application backed by the Python service. It is not a cloud labeling service.

## What the system does

The project turns an approved procedure into a dataset and detector workflow:

1. A procedure plan defines steps and object classes.
2. A video is imported as a take with a recording-session ID.
3. The ground-truth timeline records the expected step at each time range.
4. Keyframes are generated from the take.
5. The annotator draws object boxes on selected frames.
6. The system builds a YOLO-style dataset, checks it, trains a detector, and evaluates it.
7. Only a passed quality gate and passed evaluation are eligible for release.

The procedure FSM remains the primary sequence engine. A learned temporal head, 3D HMR, Jetson deployment, and microgravity simulation are not part of this workstream.

## Locked project decisions

- Use the React Studio on port `5767`; do not restore the old PySide6 GUI.
- The red/blue box demo is the current simple reference, not the final experiment scope.
- The edge target is a laptop with an RTX 5050 8 GB GPU.
- Use the terminology `orientation-diverse augmentation`.
- Do not add HMR 2.0, SMPLer-X, smplfitter, Jetson support, or a learned temporal head without an explicit architecture decision.
- Keep the YAML schema authoritative and avoid inventing parallel contracts.
- Keep Python compatible with `<3.14` and keep Ruff clean.

## Windows setup

From PowerShell:

```powershell
git clone https://github.com/ParthVarekar/HAR_for_BAS.git
cd HAR_for_BAS
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[perception,streaming,voice,studio,dev]"
```

The `voice` extra installs `pyttsx3`. The application can still operate without speech if the local voice backend is unavailable.

## Start the Studio

From the repository root:

```powershell
startup_training_studio.bat
```

Open [http://127.0.0.1:5767/?workspace=studio](http://127.0.0.1:5767/?workspace=studio). The launcher builds the React frontend when needed and starts the local service. Existing activities are loaded from `activities/`.

To run the full verification suite instead:

```powershell
cmd /c startup.bat test
```

Expected result: all tests pass, Ruff passes, formatting is clean, the demo plan validates, and the React smoke check passes.

## MELFI activity to use

Open activity `cold_stowage_melfi`, then select take `studying_cells_in_space-c2dce8af89`. It is already stored in the repository and has these exact properties:

- 153.04 seconds
- approximately 25.0065 FPS
- 768 x 432 pixels
- recording session `cold_stowage_melfi_session_001`
- 8 timeline records covering the full video
- 10 plan object classes
- 0 annotations at handoff

## Studio workflow

### STEP 01 — Approved procedure

Confirm that the selected activity is `cold_stowage_melfi`. Review the step titles, time ranges, and object classes. Do not change the schema or remove classes just to make annotation faster. If a class is genuinely not visible anywhere, record that as a plan-quality issue for review.

### STEP 02 — Training videos

Confirm the selected take and recording session. Do not create a duplicate take when the existing MELFI take is already listed. For future videos, use a new unique recording-session ID even when the experiment is the same.

### STEP 03 — Ground truth timeline

The MELFI timeline is already filled with eight contiguous records. Verify that the times align with the video. Timeline CSV imports use:

```text
id,take_id,start_s,end_s,expected_step_id,observed_action,result,object_ids,region_ids,notes
```

Valid result values are `completed`, `incomplete`, `incorrect`, `skipped`, `out_of_order`, and `uncertain`.

### STEP 04 — Prepare and train

Do not press training before annotation and the quality gate are complete. Dataset preparation creates `activities/<activity>/datasets/dataset_v1/` and the training job stores its artifacts under the activity's job/output directories.

The available presets are:

| Preset | Epochs | Image size | Batch | Workers | Use |
|---|---:|---:|---:|---:|---|
| `laptop_safe` | 50 | 512 | 4 | 0 | First run on the RTX 5050 |
| `balanced` | 100 | 640 | 8 | 2 | After a stable baseline |
| `quality` | 150 | 640 | 8 | 2 | Later tuning with enough data |

Use `auto` device selection. It resolves to CUDA when PyTorch can see the GPU. `nvidia-smi` is useful for checking that the process is using the RTX 5050. A GPU name shown in the UI is not, by itself, proof that training is actively using CUDA.

### STEP 05 — Assist frame annotation

1. Select the MELFI take.
2. Set the sampling interval to `40` frames. This gives approximately 1.6-second spacing and covers the 153-second video within the current 120-keyframe limit.
3. Generate or load the keyframes.
4. Choose a class from the object selector.
5. Drag a tight box around each visible instance of that class.
6. Add additional boxes on the same frame when multiple instances are visible.
7. Press `Enter` or click `Save & next frame`. The next frame is brought forward automatically.
8. Use the frame dropdown to revisit a frame. The dropdown is intentionally dark/high-contrast and does not require horizontal scrolling.
9. If a frame has no instance of a selected class, do not draw a guessed box. Move to the next frame.

The exact visible class names for MELFI are:

```text
interviewee
melfi_freezer
dewar_compartment
sample_container
control_panel
astronaut
computer
nasa_logo
esa_logo
title_card
```

Box `melfi_freezer` only when the freezer is visually identifiable. Box `dewar_compartment`, `sample_container`, and `control_panel` only when the corresponding object is visible. Do not label generic ISS equipment as MELFI. Box the interviewee or astronaut when visible, even if the action is an interview or maintenance-like manipulation. Do not label text captions as physical objects.

### STEP 06 — Quality gate and evaluation

Run the quality gate after saving annotations. It should confirm:

- every required class has coverage;
- annotations are valid and within image bounds;
- train, validation, and test splits are non-empty;
- splits are separated by recording session;
- there are no malformed or duplicate annotation rows.

If the gate fails because only one session exists, that is expected. Do not treat a one-video training run as a general detector result. Add independent sessions before making claims about robustness.

## What good data looks like

The goal is not to draw a box on every frame of the source video. The goal is representative, consistent boxes across camera views, sizes, partial occlusions, motion, lighting, and backgrounds. For a complex space experiment, collect multiple independent sessions and include both normal examples and difficult cases. Keep labels conservative: an uncertain object should be left unlabeled and recorded as an uncertainty rather than guessed.

## Files written by annotation and training

- `activities/<activity>/annotations.jsonl`: one JSON object per saved annotation row
- `activities/<activity>/datasets/dataset_v1/`: generated images, labels, and split metadata
- activity job/output folders: training logs, metrics, and model artifacts
- `activities/<activity>/timeline.jsonl`: expected procedure events

Do not manually edit generated labels while the Studio is running. If a correction is needed, correct it in the Studio and regenerate the dataset.

## Troubleshooting

### The video is missing

Confirm the file is tracked under `activities/<activity>/takes/` and that the take metadata points to that relative file. Do not rely on a personal Downloads path after cloning.

### CUDA is not used

Run:

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
nvidia-smi
```

If `torch.cuda.is_available()` is false, the installed PyTorch build or NVIDIA driver is the issue; do not hide the fallback. Use `laptop_safe` and verify the resolved device in the job log.

### The quality gate fails

Read the report rather than bypassing it. Common causes are missing classes, empty validation/test splits, invalid boxes, duplicate rows, or only one recording session. Fix the data or plan, then regenerate the dataset.

### The browser looks stale

Restart `startup_training_studio.bat`, reload the page, and verify that the backend is reachable at `http://127.0.0.1:5767/health`.

## AI coding-tool instructions

Before changing code, read `HANDOVER.md`, `AGENTS.md`, `docs/architecture.md`, `docs/validation_matrix.md`, `docs/risk_register.md`, `bas_har/schema/plan_schema.py`, `bas_har/procedure/engine.py`, and the React Studio files. Follow the schema-first design. Do not change the demo, edge target, or parked phases without asking the project owner. Do not add code comments. Run `cmd /c startup.bat test` before handoff and leave both tests and Ruff clean.

## Current handoff

The collaborator's immediate job is to box the MELFI video. No MELFI annotations or model training have been completed yet. After annotation, the next engineering checkpoint is a quality-gate report, followed by a `laptop_safe` CUDA baseline and an evaluation report. The existing Concrete Hardening activity is a reference dataset, not evidence of production accuracy.
