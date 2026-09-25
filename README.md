<p align="center">
  <img src="web/public/favicon.svg" width="88" alt="BAS-HAR logo" />
</p>

<h1 align="center">BAS-HAR</h1>

<p align="center">
  <b>AI procedure monitoring for experiments aboard the Bharatiya Antariksh Station</b><br/>
  Watches an astronaut perform a science procedure, recognises every step as it happens,<br/>
  and speaks up the moment a step is skipped or done out of order. Fully offline, in real time, on a laptop GPU.
</p>

<p align="center">
  <code>Python 3.11</code> · <code>PyTorch + CUDA</code> · <code>YOLO11</code> · <code>Qwen3-VL</code> · <code>MediaPipe</code> · <code>React</code> · <code>Pydantic</code> · <code>213 automated tests</code>
</p>

---

## Contents

1. [What BAS-HAR does](#what-bas-har-does)
2. [A session, start to finish](#a-session-start-to-finish)
3. [Three ways to teach it a procedure](#three-ways-to-teach-it-a-procedure)
4. [How it works](#how-it-works)
5. [The procedure engine](#the-procedure-engine)
6. [Perception](#perception)
7. [The Operations dashboard](#the-operations-dashboard)
8. [Voice alerts](#voice-alerts)
9. [The Training Studio](#the-training-studio)
10. [Plans are data, not code](#plans-are-data-not-code)
11. [Audit trail and recording](#audit-trail-and-recording)
12. [Performance](#performance)
13. [Activity library](#activity-library)
14. [Getting started](#getting-started)
15. [Repository map](#repository-map)
16. [Engineering practice](#engineering-practice)
17. [Documentation](#documentation)

---

## What BAS-HAR does

Space-station science runs on written procedures: open this door, pull that tray, place the sample,
close everything in the right order, within the right time. Today a crew member follows the steps
from memory or a tablet while a ground team watches downlinked video. BAS-HAR puts that second pair
of eyes on board.

Point it at a camera (or drop in a recorded video) and it:

- **recognises which experiment is being performed**, automatically, from the video itself;
- **follows the procedure step by step**, using a trained object detector, a vision-language model
  that answers plain-English questions about each frame, or both at once;
- **announces each completed step** and **raises spoken and on-screen alerts** when a step is
  skipped, done out of order, or stalls;
- **shows everything live** on a mission-console dashboard: the annotated video, a step timeline
  with completion times, alerts, and what the AI currently believes it is seeing;
- **writes a tamper-evident log** of every event, with a checksum on every line;
- does all of this **with no network connection**, on a single laptop GPU, at the video's own frame
  rate.

The system was developed and demonstrated on real International Space Station footage of the
**MELFI** (Minus Eighty-Degree Laboratory Freezer for ISS) sample-stowage procedure, where it
follows all eight steps of the procedure in order, each within about a second of the moment it
happens on screen, with zero false alerts.

---

## A session, start to finish

1. **Open the dashboard** (`startup.bat`) and drop an experiment video anywhere on the page, or
   connect a live camera or RTSP stream.
2. **Recognition.** BAS-HAR compares the video's scenes with the reference recordings of every
   procedure in its library and picks the one being performed. You can also pick the procedure
   yourself from a list, which previews all of its steps before you start.
3. **Monitoring.** The video plays at real speed with detections drawn on it. The step timeline
   fills in as each step is observed, stamped with the exact video time it happened. A voice says
   "Step 3 done. Pulls tray 2 out of dewar 1."
4. **Deviations.** If the astronaut skips a step or does one out of order, a red banner appears,
   the Alerts counter turns red, the timeline marks the step, a double tone sounds and the voice
   says "Alert. Step 4 skipped." The operator can silence alerts for 60 seconds with one click.
5. **Summary.** When the video ends, the dashboard shows the verdict ("All steps completed in
   order", or exactly which steps were skipped, late or never reached) and the voice reads it out.
6. **Record.** Every event is in a checksummed JSONL log, and live sessions keep a rolling MP4
   recording for review.

---

## Three ways to teach it a procedure

BAS-HAR is built so that adding a new experiment never requires writing code. A procedure is
described in a YAML plan, and each step says what evidence proves it is done. That evidence can
come from three sources.

### 1. Described: no training at all

Write each object as a plain-English description and each step as a yes/no question about the
camera frame:

```yaml
objects:
  - id: tray
    classes: [tray]
    prompts: ["long white cylindrical tray", "metal cylinder pulled out of a freezer"]
steps:
  - id: step_02
    description: A tray is pulled out of the freezer.
    evidence:
      - kind: visual_question
        question: "Is a long cylindrical tray pulled out of the freezer, or held in the astronaut's hands?"
        expect: "yes"
```

A vision-language model running locally on the GPU answers every question several times per
second, and an open-vocabulary detector finds described objects without a single labelled image.
A new procedure can be monitoring video within minutes of being written down, including on camera
angles and astronauts it has never seen.

### 2. Trained: pixel-precise

For the highest precision, label a few dozen frames in the built-in Training Studio and train a
YOLO11 detector. Objects can have **states** (a hatch that is `open` or `closed`, a tray that is
`in` or `out`, a latch turned `left` or `right`) and **containment** ("the sample is inside
compartment 1"). The MELFI package was built this way: 775 boxes across 20 objects, including
per-object states and objects nested inside other objects.

### 3. Hybrid: the best of both

Mix both kinds of evidence in one plan. The trained detector handles fine, small, or partly hidden
details; plain-English questions cover everything else. The dashboard shows which mode is active.

---

## How it works

```
 ┌──────────────┐   ┌────────────────────────────── Perception ──────────────────────────────┐
 │ Camera / RTSP│   │  YOLO11 detector (trained)      YOLOE open-vocabulary detector          │
 │ Video file   ├──►│  MediaPipe pose + hands         Hand-object interaction tagger          │
 │ Upload       │   │  Colour-block detector          Qwen3-VL yes/no questioner (async)      │
 └──────────────┘   └──────────────────────────────────┬──────────────────────────────────────┘
                                                       │ PerceptionResult per frame
                                                       ▼
                    ┌──────────────── Procedure engine (deterministic FSM) ──────────────────┐
                    │  Evidence rules from YAML · sliding-window confirmation · skip-ahead    │
                    │  out-of-order detection · pause / stall tracking · alert policy         │
                    └──────────────┬───────────────────────────────┬──────────────────────────┘
                                   │ EventRecord                   │ state, confidence
                    ┌──────────────▼──────────┐   ┌────────────────▼────────────────────────┐
                    │ CRC-verified JSONL log  │   │ Dashboard server: MJPEG stream, status, │
                    │ MP4 circular buffer     │   │ events, voice announcer, Training Studio │
                    └─────────────────────────┘   └──────────────────────────────────────────┘
```

Five layers, each with one job:

| Layer | Package | Responsibility |
|---|---|---|
| Schema | `bas_har/schema` | Pydantic contracts for plans, events, activities, recognition and display settings. Every feature starts here. |
| Perception | `bas_har/perception` | Turns each frame into detections, pose, hands, hand-object interactions and question answers. |
| Procedure | `bas_har/procedure` | The step engine: evidence evaluation, transitions, alerts. Generic over the schema. |
| I/O | `bas_har/io` | Capture from files, webcams and RTSP; checksummed logs; rolling video recording. |
| Interface | `bas_har/web`, `web/` | Real-time server, the Operations dashboard and the Training Studio. |

---

## The procedure engine

The heart of BAS-HAR is a deterministic finite-state machine (`bas_har/procedure/engine.py`). It
does not guess what the next step is; it reads it from the plan and checks the evidence. That makes
every decision explainable and every alert traceable to a rule.

**Evidence rules.** Each step lists one or more rules, and all of them must hold:

| Rule | Meaning |
|---|---|
| `object_visible` | A detected object is present, optionally `inside_of` or `outside_of` another object. |
| `object_state` | An object is in a named state (`open`, `closed`, `in`, `out`, `left`, `right` ...). |
| `object_location` | An object lies fully inside a calibrated region polygon of the camera view. |
| `hand_object_interaction` | A hand is grasping, placing, opening or closing a given object. |
| `actor_visible` | A person is in view (pose detected). |
| `visual_question` | A yes/no question about the frame, answered by the vision-language model. |

**Robust confirmation.** A step completes when its evidence holds in at least 80% of a short sliding
window, not in every single frame. A dropped frame or a one-frame false detection cannot flip a
result, and a genuine change is confirmed within a fraction of a second.

**Understanding the whole procedure, not just the next step.**
- *Skip-ahead*: if a later step is clearly happening while an earlier one never was, the earlier
  step is marked skipped and an alert fires.
- *Out-of-order detection*: a step completed after a later one is flagged as out of order.
- *State-aware ordering*: a step whose end state is already true at the start (a hatch that begins
  closed, for example) is never mistaken for being done, because the engine knows an earlier step
  must change that state first.
- *Conflict resolution*: when the detector sees the same object in two states at once, the more
  confident state wins.
- *Stall tracking*: each step can declare an expected duration, and the engine notices when
  progress stops for too long.

**Alert discipline.** Alerts are rate-limited, can be silenced for a time window, and require a
minimum persistence before firing, so the crew hears what matters and nothing else.

---

## Perception

All models run locally. Nothing is sent to the cloud.

- **YOLO11 object detection** trained per activity in the Training Studio, predicting at the
  image size it was trained on, with per-state classes (`dewar_hatch__open`, `tray_2__out` ...).
- **YOLOE open-vocabulary detection** with a MobileCLIP text encoder: finds objects from written
  descriptions, no labelled data needed.
- **Qwen3-VL vision-language questions.** The engine's questions are answered by a local
  Qwen3-VL-2B model. Instead of generating text, BAS-HAR pre-fills the answer and reads the model's
  yes/no probability for every question in a single forward pass, about 0.4 seconds for a whole
  plan's question set. Answers between 40% and 60% count as "unsure" and never complete a step on
  their own. The questioner runs on its own thread, so video analysis never waits for it.
- **MediaPipe pose and hand landmarks**, loaded only when the plan actually needs them.
- **Hand-object interaction tagging** from hand keypoints and object boxes.
- **Colour-block detection** for simple bench demonstrations.
- **Automatic experiment recognition**: frames sampled from an uploaded video are compared with the
  reference recordings of every activity using detector-backbone features, and the best match above
  a similarity threshold is selected.

---

## The Operations dashboard

A mission-console interface (React, served by the same Python process) built for a quick read at
a glance.

- **Header** with the procedure name, a live status pill, how the procedure was recognised, and
  whether it is running trained, described or hybrid.
- **Four summary cards**: progress (with a bar), current step, alert count, and video time with
  real-time factor and frame rate.
- **Live video** streamed as MJPEG, with thin detection outlines and labels. A **Detection boxes**
  switch hides them when the view gets busy; the choice is remembered and even redraws the final
  frame after a session ends.
- **Step timeline**: every step with its state (in progress, done, skipped, out of order, not
  reached), the exact video time each was completed, and a live evidence meter on the current step.
  The rail fills in green as the procedure advances.
- **Alert banner** for the latest deviation, with *Silence for 60 s* and *Dismiss*.
- **Session log** with filters for all events, completed steps, alerts, and raw evidence updates.
- **What the model sees**: each plain-English question with its live probability and a yes / no /
  unsure verdict.
- **System details**: inference device, GPU, frame encoder, display rate, lag, per-stage timing in
  milliseconds, event log file and recording buffer.
- **Drag and drop** a video anywhere on the page to start.
- Responsive from a phone to a wall display, with offline-bundled Inter and JetBrains Mono type,
  and an original BAS-HAR mark.

---

## Voice alerts

Hands-free feedback, designed for a crew member whose eyes and hands are busy.

- Every completed step is announced individually and in order: "Step 5 done. Places the sample."
- Alerts ("Alert. Step 4 skipped.") jump ahead of routine announcements without cutting anything
  off.
- A short high tone confirms each step; a double low tone marks each alert.
- A spoken summary closes the session.
- If the dashboard is open in several windows, exactly one of them speaks: whichever the operator
  used last. There are never overlapping or repeated announcements.
- A watchdog keeps the speech queue moving even if the browser's speech engine stalls.

---

## The Training Studio

A complete, in-browser pipeline from raw footage to a released, verified activity package, at
`http://127.0.0.1:5767/?workspace=studio`.

1. **Create an activity** package with its own plan, takes, labels and models.
2. **Upload takes** (videos); metadata such as duration and frame rate is probed automatically.
3. **Import a timeline** of what happens when, from a spreadsheet template.
4. **Build the procedure** in a visual editor: objects, states, prompts, steps, evidence rules,
   questions and the "done when yes / no" choice, validated against the schema on save.
5. **Label frames**: draw boxes, assign states, nest boxes inside boxes, copy labels from the
   previous frame, recolour by class, and review every box on a frame in a side list.
6. **Prepare a dataset** from labelled frames with held-out splits.
7. **Run the quality gate**: per-class label counts, missing classes and session coverage are
   checked before training is allowed.
8. **Train** a detector on the local GPU as a tracked background job.
9. **Evaluate** against held-out data, with per-class metrics and a failure list.
10. **Release and verify** a model version so the Operations dashboard uses it.

A step-by-step labelling guide written for non-programmers is included
([BOXING_GUIDE.md](BOXING_GUIDE.md)), so domain experts can contribute without touching code.

---

## Plans are data, not code

Every experiment-specific detail lives in YAML. The Python engine contains no step names, no class
names and no experiment logic. Adding the fifth, fiftieth or five-hundredth procedure is a matter
of writing a plan.

```yaml
id: cold_stowage_melfi
name: MELFI Sample Stowage (Ignis)
objects:
  - id: dewar_hatch
    classes: [dewar_hatch]
    states: [open, closed]
  - id: sample
    classes: [sample]
steps:
  - id: step_05
    description: Slawosz places the sample inside the open compartment 1.
    evidence:
      - kind: object_visible
        object: sample
        inside_of: compartment_1
        min_frames: 15
      - kind: object_state
        object: compartment_1
        state: open
        min_frames: 15
    next: [step_06]
    expected_duration_s: 6
alert_policy:
  skip_confidence_threshold: 0.85
  rate_limit_s: 5.0
  silence_window_s: 60.0
```

Plans are validated by strict Pydantic models: unknown fields are rejected, every referenced
object and state must exist, every step must be reachable, and a terminal step must exist. A plan
that loads is a plan that runs.

---

## Audit trail and recording

- **Checksummed event log.** Every step change and alert is written as a JSON line with its own
  CRC32 checksum, the UTC time, the video time, the step, its confidence and the evidence behind
  it. A verifier re-checks every line, so any edit to the log is detectable.
- **Atomic writes.** Log files appear only once complete.
- **Rolling MP4 recording** of live camera sessions in fixed-length segments, keeping recent
  footage available for review without filling the disk.
- **Performance log** alongside each session with per-stage timings.

---

## Performance

Measured on a laptop with an NVIDIA RTX 5050 Laptop GPU (8 GB):

| Measure | Result |
|---|---|
| Playback | Uploaded video analysed at its own frame rate: **1.00× real time at 25 fps** |
| Trained detection | about **9-12 ms per frame** on the GPU |
| Vision-language answers | the full question set in about **0.4 s**, on a background thread |
| MELFI procedure (trained) | **8 of 8 steps**, in order, each within about **1 s** of the on-screen moment, **zero false alerts** |
| Frame drawing and encoding | about **0.1 ms** to draw, GPU JPEG encoding (nvjpeg) with CPU fallback |

The server splits work across three threads (analysis, presentation, recording) so the browser,
the disk and image encoding can never slow detection down. Uploaded files are paced to their own
frame rate, the stream is pushed to the browser the instant a frame is ready, and the detector is
warmed up before playback so there is no first-second stutter.

---

## Activity library

| Activity | What it is | Mode |
|---|---|---|
| `cold_stowage_melfi` | ESA astronaut Sławosz Uznański-Wiśniewski stores a sample in MELFI during the Ignis mission: 8 steps, 20 objects with states | Trained |
| `melfi_zeroshot` | The same MELFI procedure written entirely in plain English, no labels at all | Described |
| `studying_cells_lsg` | Cell-biology work in the Life Sciences Glovebox | Trained |
| `foaming_fluid_science` | The FOAM-C foam-coarsening experiment in the Fluid Science Laboratory | Trained |
| `concrete_hardening_msl` | Glovebag concrete-mixing experiment | Package |
| `experiments/red_blue_box` | A tabletop bench demonstration for testing without space footage | Colour detection |

---

## Getting started

**Requirements:** Windows 10/11, Python 3.11, Node.js 18+, and for GPU speed an NVIDIA GPU with a
recent driver. CPU-only machines work too.

```bash
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[perception,streaming,voice,studio,dev]"
cd web && npm install && npm run build && cd ..
```

Start the Operations dashboard and open http://127.0.0.1:5767:

```bash
startup.bat
```

Start the Training Studio instead:

```bash
startup_training_studio.bat
```

Run the full check suite (tests, lint and build):

```bash
cmd /c startup.bat test
```

Stop whatever a launcher started (each also accepts `--list` to preview):

```bash
close_startup.bat
```

Command-line tools for scripted work live in `scripts/`: dataset recording and preparation,
YOLO training, ONNX export, offline replay of a procedure through the engine, and smoke tests.

---

## Repository map

```
bas_har/
  schema/        Pydantic contracts: plans, events, activities, recognition, display
  procedure/     State machine, evidence rules, alerts, smoothing, event sinks
  perception/    YOLO11, YOLOE, Qwen3-VL questioner, pose, hands, HOI, colour blocks
  io/            Capture (file, webcam, RTSP), CRC JSONL logs, MP4 circular buffer
  studio/        Activity registry, takes, timelines, labels, datasets, quality gate,
                 training jobs, evaluation, releases, verification, recognition
  voice/         Text-to-speech and confirmation tones on the server side
  web/           Real-time server: MJPEG stream, REST API, three-thread session runner
web/             React dashboard and Training Studio (Vite)
activities/      Activity packages: plan, takes, labels, models
experiments/     Bench demonstration plans
scripts/         Training, export, replay and smoke-test tools
tests/           213 automated tests
docs/            Architecture, validation matrix, risk register, progress log
```

---

## Engineering practice

- **Schema first.** Every feature begins as a Pydantic model; logic follows.
- **Experiment knowledge in YAML only.** The engine is generic.
- **213 automated tests** covering the schema, engine, evidence rules, perception wiring, web API,
  streaming, display settings and the zero-shot questioner. Ruff lint and formatting are
  enforced, and the React build is part of the check.
- **Fully offline.** Models, fonts and assets all ship with the project.
- **Traceable decisions.** A living validation matrix, risk register and progress log record what
  was measured and why each design choice was made.

---

## Documentation

| Document | For |
|---|---|
| [BOXING_GUIDE.md](BOXING_GUIDE.md) | Anyone helping label video, no programming needed |
| [training_guide.md](training_guide.md) | Running the Training Studio end to end |
| [USP.md](USP.md) | What makes BAS-HAR different |
| [docs/architecture.md](docs/architecture.md) | System design in depth |
| [docs/validation_matrix.md](docs/validation_matrix.md) | What has been verified, and how |
| [HANDOVER.md](HANDOVER.md) | Engineering handover |

---

<p align="center">
  Built for SIH26174 · AI Human Activity Recognition for on-board BAS experiments
</p>
