# Training Studio Guide

Last updated: 2026-09-15

This guide covers using the Training Studio to box a video, train a detector, and check it
against the video.

The Training Studio is a local React application backed by the Python service. It is not a cloud
labelling service.

## What the system does

The project turns an approved procedure into a dataset and detector workflow:

1. A procedure plan defines steps, object classes, and (optionally) per-object states.
2. A video is imported as a take with a recording-session ID.
3. The ground-truth timeline records the expected step at each time range.
4. Keyframes are generated from the take.
5. The annotator draws object boxes — including boxes nested inside other boxes, and a state for
   any class that has one (open/closed, in/out, and so on).
6. The system builds a YOLO-style dataset, checks it, trains a detector, and evaluates it.
7. Only a passed quality gate and passed evaluation are eligible for release.

The procedure FSM remains the primary sequence engine. A learned temporal head, 3D HMR, Jetson
deployment, and microgravity simulation are not part of this workstream.

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

## Start and stop the Studio

From the repository root:

```powershell
startup_training_studio.bat
```

Open [http://127.0.0.1:5767/?workspace=studio](http://127.0.0.1:5767/?workspace=studio). The launcher builds the React frontend when needed and starts (or reuses) the local service. Existing activities are loaded from `activities/`.

To close the server this launcher started:

```powershell
close_training_studio.bat
```

`startup.bat` (the Operations dashboard launcher, and its own checks/training/analyze commands) has its own matching `close_startup.bat`. Each close script only stops the processes its matching launcher started; add `--list` to either close script to see what it would stop without stopping anything.

To run the full verification suite instead of the Studio:

```powershell
cmd /c startup.bat test
```

Expected result: all tests pass, Ruff passes, formatting is clean, the demo plan validates, and the React smoke check passes.

## Studio workflow

### STEP 01 — Approved procedure

Choose an activity from the registry. Review the step titles, evidence rules, and object classes.
Steps can use `object_visible`, `object_state`, `hand_object_interaction`, `actor_visible`, or
`object_location` evidence; `object_state` and `inside_of` need the object's `states` list (or the
container object) to already be entered in the objects table above. Keep each step to one
observable change — bundling several actions ("opens the hatch, pulls the tray, opens the
compartment") into one step makes the checker unable to tell which action actually happened.

### STEP 02 — Training videos

Upload the take and give it a recording-session ID. Do not create a duplicate take when the video
is already listed. Use a new unique recording-session ID for every additional video, even for the
same activity.

### STEP 03 — Ground truth timeline

Import a CSV with these columns:

```text
id,take_id,start_s,end_s,expected_step_id,observed_action,result,object_ids,region_ids,notes
```

Valid result values are `completed`, `incomplete`, `incorrect`, `skipped`, `out_of_order`, and `uncertain`. For a plan whose steps are single state changes, the most reliable way to fill in the times is to box first, then look at when each state's boxes change from one value to the other and use those times.

### STEP 04 — Prepare and train

Do not press training before annotation and the quality gate are complete. Dataset preparation creates `activities/<activity>/datasets/dataset_v1/` and the training job stores its artifacts under the activity's job/output directories.

The available presets are:

| Preset | Epochs | Image size | Batch | Workers | Use |
|---|---:|---:|---:|---:|---|
| `laptop_safe` | 50 | 512 | 4 | 0 | First run on the RTX 5050 |
| `balanced` | 100 | 640 | 8 | 2 | After a stable baseline |
| `quality` | 150 | 640 | 8 | 2 | Later tuning with enough data |

Use `auto` device selection. It resolves to CUDA when PyTorch can see the GPU. `nvidia-smi` is useful for checking that the process is using the RTX 5050. A GPU name shown in the UI is not, by itself, proof that training is actively using CUDA.

**The Studio's "Start laptop-safe training" button mirrors images left-right by default (Ultralytics' `fliplr` default).** This is fine for symmetric activities, but wrong for any plan with quadrant-numbered objects (dewar/tray 1-4) or left/right states (a latch), because a flipped image teaches the model the wrong side. For such a plan, train from a script instead, passing `fliplr=0` (and, if the state also depends on up/down orientation, `flipud=0`) to `ultralytics.YOLO(...).train(...)`. This has not yet been wired into the Studio button itself.

### STEP 05 — Assist frame annotation

1. Select the take.
2. Set "Sample every frames" (it resets to 30 on page reload; lower it for more frames).
3. Choose a class from the Label dropdown. If it has states, a State dropdown appears — a box
   won't save without a state when its class needs one.
4. Drag a box around each visible instance. Dragging inside a box already on the frame starts a
   new box, so nested objects (a sample inside an open compartment, inside a tray, inside a
   dewar) can all be boxed on the same frame.
5. Save with `Enter` (stay on this frame) or `Shift+Enter` / "Save & next frame" (advance).
6. Use "Copy boxes from previous frame" to carry over boxes for parts that haven't moved, then
   redraw or delete only the ones that changed.
7. The per-frame box list lets you change a box's state, redraw it, or delete it without leaving
   the frame. Each class gets its own colour; "Show box labels" can be turned off when labels
   cover small parts.
8. If a frame has no instance of a class, do not draw a guessed box. Move to the next frame.

### STEP 06 — Quality gate and evaluation

Run the quality gate after saving annotations. It should confirm:

- every required class (each class+state pair, for stateful objects) has coverage;
- annotations are valid and within image bounds;
- train, validation, and test splits are non-empty;
- splits are separated by recording session;
- there are no malformed or duplicate annotation rows.

If the gate fails because only one session exists, that is expected. Do not treat a one-video training run as a general detector result. Add independent sessions before making claims about robustness.

## What good data looks like

The goal is not to draw a box on every frame of the source video. The goal is representative, consistent boxes across camera views, sizes, partial occlusions, motion, lighting, and backgrounds. For a complex space experiment, collect multiple independent sessions and include both normal examples and difficult cases. Keep labels conservative: an uncertain object or state should be left unlabeled and recorded as an uncertainty rather than guessed.

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

If `torch.cuda.is_available()` is false, the installed PyTorch build or NVIDIA driver is the issue; do not hide the fallback. Use `laptop_safe` and verify the resolved device in the job log. The Operations dashboard now also shows a red banner if it ever resolves to CPU while an NVIDIA GPU is present.

### The quality gate fails

Read the report rather than bypassing it. Common causes are missing classes (or missing states for a class), empty validation/test splits, invalid boxes, duplicate rows, or only one recording session. Fix the data or plan, then regenerate the dataset.

### The Operations dashboard looked slow or laggy

This was a real bug (Checkpoint 31): uploaded video used to run far slower than real time because
decoding, detection, drawing, JPEG encoding, and the browser stream all shared one thread. It's now
split into separate analysis, presenter, and recorder threads, uploaded video is paced to its own
frame rate, and the stream pushes frames instead of polling. If it looks slow again, check the
dashboard's own speed readout (real-time factor, device, per-stage milliseconds) before assuming
it's the same issue.

### The browser looks stale

Restart `startup_training_studio.bat`, reload the page, and verify that the backend is reachable at `http://127.0.0.1:5767/api/health`.

## AI coding-tool instructions

Before changing code, read `AGENTS.md`, `docs/architecture.md`, `docs/validation_matrix.md`, `docs/risk_register.md`, `halo/schema/plan_schema.py`, `halo/procedure/engine.py`, `halo/procedure/evidence.py`, and the React Studio files. Follow the schema-first design. Do not change the demo, edge target, or parked phases without asking the project owner. Do not add code comments. Run `cmd /c startup.bat test` before handoff and leave both tests and Ruff clean.

## Current handoff

The MELFI activity (`cold_stowage_melfi`) is boxed (775 boxes, 55 frames), trained, and verified:
all 8 steps complete in order on the source video with no false alerts, at real playback speed.
The next real work is a second independent MELFI recording session before any generalisation claim,
and the ice-vapour/fabric issue alerts, which the owner will ask for when ready. The Concrete
Hardening and Studying Cells in Space (formerly the MELFI activity's placeholder take) activities
are reference data only, not evidence of production accuracy for those experiments.
