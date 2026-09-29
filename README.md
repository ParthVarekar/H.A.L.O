<a id="top"></a>

<p align="center">
  <img alt="H.A.L.O.: watches every step of an experiment in orbit and speaks up the moment one is missed." src="docs/assets/banner-light.png">
</p>

<p align="center">
  <img alt="Python 3.11" src="https://img.shields.io/badge/python-3.11-2f7bff?style=flat-square&labelColor=eef1f5&logo=python&logoColor=2f7bff">
  <img alt="PyTorch with CUDA" src="https://img.shields.io/badge/pytorch-CUDA-2f7bff?style=flat-square&labelColor=eef1f5&logo=pytorch&logoColor=2f7bff">
  <img alt="React 18" src="https://img.shields.io/badge/react-18-2f7bff?style=flat-square&labelColor=eef1f5&logo=react&logoColor=2f7bff">
  <img alt="276 tests passing" src="https://img.shields.io/badge/tests-276%20passing-12a26a?style=flat-square&labelColor=eef1f5">
  <img alt="Runs fully offline" src="https://img.shields.io/badge/runs-fully%20offline-12a26a?style=flat-square&labelColor=eef1f5">
  <img alt="SIH26174 requirements: 7 of 7" src="https://img.shields.io/badge/SIH26174-7%20of%207%20requirements-12a26a?style=flat-square&labelColor=eef1f5">
</p>

<p align="center">
  <b>An on-board AI that follows a science procedure the way a ground controller would.</b><br>
  It recognises every step as it happens and speaks up the moment one is skipped or done out of order,<br>
  in real time, on a single laptop GPU, with no network connection.
</p>

<p align="center">
  <a href="#quick-start"><b>Quick start</b></a> ·
  <a href="#how-it-works"><b>How it works</b></a> ·
  <a href="#verify-it-yourself"><b>Verify it yourself</b></a> ·
  <a href="USP.md"><b>Why H.A.L.O.</b></a> ·
  <a href="docs/assets/demo.mp4"><b>Watch the demo</b></a>
</p>

<br>

<p align="center">
  <img alt="H.A.L.O. intro: what it does, in under a minute" src="docs/assets/intro.webp" width="100%">
</p>
<p align="center">
  <sub>H.A.L.O. in under a minute.</sub>
</p>

<br>

<p align="center">
  <img alt="H.A.L.O. following the MELFI sample-stowage procedure on real ISS footage" src="docs/assets/demo.webp" width="100%">
</p>
<p align="center">
  <sub>Real ISS footage of the MELFI −80 °C freezer procedure. Recognised automatically, every step followed in order, zero alerts. Shown at 3× speed.</sub>
</p>

<details>
<summary><b>Table of contents</b></summary>

- [Why it matters](#why-it-matters)
- [Every requirement, met](#every-requirement-met)
- [Features](#features)
- [Gallery](#gallery)
- [Three ways to teach it](#three-ways-to-teach-it)
- [How it works](#how-it-works)
- [Quick start](#quick-start)
- [Verify it yourself](#verify-it-yourself)
- [Performance](#performance)
- [FAQ](#faq)
- [Documentation](#documentation)
- [Built with](#built-with)
- [Acknowledgements](#acknowledgements)

</details>

## Why it matters

Science on the space station runs to written procedures. A skipped step, such as a tray left
out of a −80 °C freezer, can cost a sample that took months to prepare. Crews have little time and
ground teams cannot watch every minute. **H.A.L.O.** watches the procedure for them, checks every
step against the plan and alerts the crew immediately, all on the station's own hardware.

## Every requirement, met

| SIH26174 asks for | H.A.L.O. delivers |
|---|---|
| Continuous local video processing that tracks the sequence | Live camera, RTSP or video file, 1.00× real time at 25 fps on a laptop GPU |
| The next step suggested at the start and after each step | Spoken and on screen: *"Step 2 done. Next: pull tray 2 out of dewar 1."* |
| Voice alerts for skipped or out-of-sequence steps | Alerts jump the speech queue, with a tone, in English or Hindi |
| A timestamped, structured, lightweight record | A signed, hash-chained JSONL log plus a signed ~1 KB downlink report |
| Video streamed to a specific IP and stored locally | H.264 over UDP to any IP address, plus a rolling local recording |
| A graphical monitoring interface | The dashboard shown above, in light and dark themes |
| A trained AI model on an offline, standalone system | YOLO11 trained on real ISS footage (held-out mAP50 0.79), all local |

Each row is traced to code, tests and a demo moment in [docs/SIH_REQUIREMENTS.md](docs/SIH_REQUIREMENTS.md).

## Features

<p align="center">
  <img alt="Every step time-stamped, train-free mode, voice alerts, real time and offline, tamper-evident log, no code per experiment" src="docs/assets/features.png" width="100%">
</p>

- **Proven on real space-station footage.** Follows all 8 steps of the MELFI sample-stowage
  procedure in order, each within about a second of the moment it happens, with zero false alerts.
- **Sees object states, not just objects.** Hatches open and closed, trays in and out, a sample
  *inside* a compartment.
- **Understands the whole procedure.** A deterministic engine catches skipped, out-of-order and
  stalled steps, so every alert traces back to a rule you can read.
- **Recognises the experiment by itself.** Drop in a video and H.A.L.O. matches its scenes against
  every procedure in the library.
- **Streams to the ground.** Send the annotated video to any IP address and open it in VLC, while
  the station keeps its own rolling recording.
- **A record nobody can quietly edit.** Every event is SHA-256 chained and Ed25519-signed. The whole
  session is sealed in a signed report of about a kilobyte, nearly 10,000× smaller than the video.

<p align="right"><a href="#top">Back to top ↑</a></p>

## Gallery

<table>
  <tr>
    <td width="50%"><img alt="Live monitoring view" src="docs/assets/dashboard-live.jpg"></td>
    <td width="50%"><img alt="All eight steps completed" src="docs/assets/dashboard-complete.jpg"></td>
  </tr>
  <tr>
    <td><sub><b>Live.</b> Detections, the step timeline with completion times, and evidence for the step in progress.</sub></td>
    <td><sub><b>Complete.</b> 8 of 8 steps, in order, zero alerts. Every step stamped with the moment it happened.</sub></td>
  </tr>
</table>

## Three ways to teach it

<p align="center">
  <img alt="Described, trained and hybrid recognition modes" src="docs/assets/modes.png" width="100%">
</p>

<img align="right" width="360" alt="Model answers panel" src="docs/assets/model-answers.png">

**Describe it, don't train it.** Objects are described in words and each step is a yes/no
question about the camera frame:

```yaml
- id: step_02
  description: A tray is pulled out of the freezer.
  evidence:
    - kind: visual_question
      question: "Is a long cylindrical tray pulled out of the freezer?"
      expect: "yes"
```

A Qwen3-VL model running locally reads the whole question set in one pass, in about 0.6 seconds,
and returns a calibrated probability for each answer. Anything between 40% and 60% counts as
*unsure* and never ticks a box by itself.

For pixel-precise work, label a few dozen frames in the built-in **Training Studio** and train a
YOLO11 detector, or combine both in one **hybrid** plan.

<br clear="right">

<p align="right"><a href="#top">Back to top ↑</a></p>

## How it works

<p align="center">
  <img alt="Input, perception, procedure engine and output" src="docs/assets/architecture-light.png" width="100%">
</p>

1. **Perception** turns each frame into evidence: trained detections with states, objects found
   from descriptions, answers to plain-English questions, and pose and hands when a plan needs them.
2. **The procedure engine** checks that evidence against the plan. A step completes when its
   evidence holds across a short sliding window, so a single bad frame never raises a false alarm.
3. **Output** is immediate: a live dashboard, spoken announcements with the next step, a signed
   event log with a kilobyte-scale downlink report, a live stream to any IP address and, for live
   cameras, a rolling recording.

## Quick start

```bash
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[perception,streaming,voice,studio,dev]"
cd web && npm install && npm run build && cd ..
```

```bash
startup.bat                     # Operations dashboard at http://127.0.0.1:5767
cmd /c startup.bat test         # tests, lint and build
startup.bat verify              # reproduce the ISS result and check its signatures
```

Drop an experiment video onto the page, or connect a camera or RTSP stream. Windows 10/11 with an
NVIDIA GPU is recommended; it also runs on CPU.

To stream to another computer, enter its IP address in the dashboard's **Stream to IP** card (or
`set HALO_STREAM_TO=udp://192.168.1.20:5000` before `startup.bat`), then open `udp://@:5000` in
VLC on that computer.

## Verify it yourself

The ISS footage, its labels and the trained detector ship with this repository, so the headline
result can be reproduced with one command and no network:

```bash
python -m halo verify
```

```text
  PASS  Experiment plans validate      6 of 6
  PASS  Reference take runs            cuda:0 · 37.3 s
  PASS  Every step recognised          8 of 8
  PASS  Steps in the planned order     no skips, none late
  PASS  No false alerts                0 alerts
  PASS  Signed event log verifies      42 lines · Ed25519 · key 443ab90de63c4fec
  PASS  Downlink report seals the log  1,002 bytes · 9,701x smaller than the video
  PASS  Removed step is caught         skip alert 1.48 s into the clip with step 1 cut out

  ALL CHECKS PASSED (8/8)
```

`python -m halo verify-log` checks any saved session line by line. Change one character and it
reports the exact line. See [docs/VERIFICATION.md](docs/VERIFICATION.md).

<p align="right"><a href="#top">Back to top ↑</a></p>

## Performance

<sub>Measured on an RTX 5050 Laptop GPU (8 GB).</sub>

| Measure | Result |
|---|---|
| Playback | **1.00×** real time at **25 fps** |
| Trained detection | **~10 ms** per frame |
| Vision-language answers | nine questions in **~0.6 s**, off the video path |
| MELFI procedure | **8 / 8** steps, in order, **0** false alerts |
| Skipped step | caught **1.5 s** into the clip |
| Downlink report | **1 KB**, **9,700×** smaller than the video |

## FAQ

<details>
<summary><b>Does it need an internet connection?</b></summary>
<br>
No. Every model runs locally, the dashboard fonts are bundled, and nothing leaves the machine.
</details>

<details>
<summary><b>How do I add a new experiment?</b></summary>
<br>
Write a YAML plan: the objects, the steps in order, and the evidence for each step. The plan is
validated before it can run. No Python changes are needed.
</details>

<details>
<summary><b>Do I have to label data?</b></summary>
<br>
Not to start. In described mode each step is a plain-English question. Label frames only when you
want pixel-precise object states from a trained detector.
</details>

<details>
<summary><b>What happens when a step is skipped?</b></summary>
<br>
The alert is spoken straight away, ahead of any queued announcement, shown on the dashboard and
written to the event log with the time it happened.
</details>

<details>
<summary><b>Can I check the results myself?</b></summary>
<br>
Yes. Run <code>python -m halo verify</code>. It replays the ISS footage that ships with the
repository, checks every step and alert, and verifies the signatures on the record it writes.
</details>

<details>
<summary><b>Can the ground see the video?</b></summary>
<br>
Yes. The dashboard streams the annotated video as H.264 over UDP to any IP address you enter. It
plays in VLC, and the station keeps its own rolling recording at the same time.
</details>

<details>
<summary><b>Can it watch a live camera?</b></summary>
<br>
Yes. Connect a webcam or an RTSP stream from the dashboard. Live sessions also keep a rolling
recording, so every alert can be reviewed afterwards.
</details>

## Documentation

| Document | What it covers |
|---|---|
| [docs/SIH_REQUIREMENTS.md](docs/SIH_REQUIREMENTS.md) | Each SIH26174 requirement traced to code, tests and a demo moment |
| [docs/VERIFICATION.md](docs/VERIFICATION.md) | Three commands to reproduce and check the results |
| [docs/DEPLOYMENT_ROADMAP.md](docs/DEPLOYMENT_ROADMAP.md) | From the laptop prototype to on-board BAS operations, stage by stage |
| [USP.md](USP.md) | What makes H.A.L.O. different |
| [docs/architecture.md](docs/architecture.md) | System design in depth |
| [docs/validation_matrix.md](docs/validation_matrix.md) | What has been verified, and how |

## Built with

<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-ffffff?style=for-the-badge&logo=python&logoColor=2f7bff">
  <img alt="PyTorch" src="https://img.shields.io/badge/PyTorch-ffffff?style=for-the-badge&logo=pytorch&logoColor=2f7bff">
  <img alt="Ultralytics YOLO11" src="https://img.shields.io/badge/YOLO11-ffffff?style=for-the-badge&logo=ultralytics&logoColor=2f7bff">
  <img alt="Qwen3-VL" src="https://img.shields.io/badge/Qwen3--VL-ffffff?style=for-the-badge&logo=alibabacloud&logoColor=2f7bff">
  <img alt="OpenCV" src="https://img.shields.io/badge/OpenCV-ffffff?style=for-the-badge&logo=opencv&logoColor=2f7bff">
  <img alt="Pydantic" src="https://img.shields.io/badge/Pydantic-ffffff?style=for-the-badge&logo=pydantic&logoColor=2f7bff">
  <img alt="React" src="https://img.shields.io/badge/React-ffffff?style=for-the-badge&logo=react&logoColor=2f7bff">
  <img alt="Vite" src="https://img.shields.io/badge/Vite-ffffff?style=for-the-badge&logo=vite&logoColor=2f7bff">
</p>

## Acknowledgements

Demonstration footage: ESA (European Space Agency), Ignis mission, used with credit for research
demonstration. Built on [Ultralytics YOLO11 and YOLOE](https://github.com/ultralytics/ultralytics),
[Qwen3-VL](https://github.com/QwenLM/Qwen3-VL), [MediaPipe](https://github.com/google-ai-edge/mediapipe),
[PyTorch](https://pytorch.org) and [React](https://react.dev). Typefaces: Inter, JetBrains Mono and
Space Grotesk (SIL Open Font License). README layout inspired by
[awesome-readme](https://github.com/matiassingers/awesome-readme).

<p align="center"><sub>Built for SIH26174 · AI Human Activity Recognition for on-board BAS experiments</sub></p>
<p align="right"><a href="#top">Back to top ↑</a></p>
