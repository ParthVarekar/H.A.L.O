<p align="center">
  <img src="web/public/favicon.svg" width="72" alt="H.A.L.O. logo" />
</p>

<h1 align="center">Why H.A.L.O.</h1>

<p align="center"><i>An on-board second pair of eyes for every experiment on the Bharatiya Antariksh Station.</i></p>

---

## The one-line pitch

**H.A.L.O. watches an astronaut carry out a science procedure and knows, step by step and in real
time, whether it is being done right, and it says so out loud, with no internet, on a laptop.**

---

## 1. Every SIH26174 requirement, met and verifiable

All seven requirements of the problem statement are implemented, and each one is traced to its code,
its tests and a moment in the live demo in [docs/SIH_REQUIREMENTS.md](docs/SIH_REQUIREMENTS.md). The
headline result is not a claim you have to take on trust: `python -m halo verify` replays the ISS
footage that ships in the repository and checks every step, every alert and every signature in about
a minute. It also replays the same footage with a step cut out and confirms the skip is caught.

## 2. It is proven on real space-station footage, not a lab mock-up

H.A.L.O. was built and demonstrated on genuine International Space Station video of the MELFI
−80 °C freezer sample-stowage procedure, performed by an ESA astronaut during the Ignis mission.
On that procedure it recognises **all 8 steps, in order, each within about one second of the
moment it happens on screen, with zero false alerts**, at full real-time speed.

Most activity-recognition projects stop at "person detected" or "hand moving". H.A.L.O. tracks
whether a specific dewar hatch is open, which tray has been pulled out, whether a compartment lid is
up, and whether the sample is actually *inside* that compartment.

## 3. It understands procedures, not just pictures

At its core is a deterministic procedure engine that knows the whole step graph:

- It catches **skipped steps**, **out-of-order steps** and **stalled steps**.
- It knows that a hatch which starts closed has not already "been closed", because an earlier step
  has to open it first.
- It confirms each step over a sliding window, so a single bad frame never raises a false alarm.

Every alert can be traced back to a written rule and a logged piece of evidence. That is the kind
of AI you can put in front of a flight-safety reviewer.

## 4. Teach it a new experiment in plain English: no training required

This is the headline capability. Describe the objects in words, write each step as a yes/no question
("Is a long cylindrical tray pulled out of the freezer?"), and H.A.L.O. monitors the procedure
immediately. A local vision-language model answers the questions several times a second, and an
open-vocabulary detector finds objects from their descriptions alone.

- **Minutes, not weeks**, from a written procedure to live monitoring.
- Works on **camera angles and astronauts it has never seen**.
- Uses a calibrated confidence reading with an explicit **"unsure" zone**, so an uncertain model
  never ticks a box by guessing.

## 5. Three modes, one engine

| Mode | When to use it |
|---|---|
| **Described** | A new experiment, no footage, no labels: write it down and run it. |
| **Trained** | Pixel-precise tracking of fine parts and their states, from a few dozen labelled frames. |
| **Hybrid** | Plain-English questions for most steps, a trained detector for the finest details. |

The same plan format, the same engine and the same dashboard serve all three. Teams can start
described on day one and sharpen individual steps later, without ever rewriting anything.

## 6. Zero code per experiment

Every experiment is a YAML file. The engine contains no step names, no object names and no
experiment logic. A new payload means a new plan, validated automatically before it can run: unknown
fields, missing objects, unreachable steps and dangling states are all rejected. **The procedure
library scales to hundreds of experiments without touching the software.**

## 7. It talks, and it never talks over itself

Built for a crew member whose eyes and hands are busy:

- It says what to do next, at the start and after every step: "Step 2 done. Next: pull tray 2 out
  of dewar 1."
- Alerts jump the queue: "Alert. Step 4 skipped." A step running past its planned time is flagged
  too.
- English or Hindi, using the computer's own offline voices.
- Distinct tones for progress and for deviations.
- A spoken summary at the end of every session.
- Open the dashboard on three screens and exactly one speaks. Never an echo, never a repeat.

## 8. Real time, on a laptop, fully offline

- **1.00× real time at 25 fps** on an 8 GB laptop GPU.
- Object detection in about **10 ms** per frame; nine AI questions answered in about **0.6 s** on
  a background thread, so the video never waits for them.
- A three-thread architecture guarantees that the browser, the disk and image encoding can never
  slow down detection.
- **No cloud, no network, no telemetry.** Models, fonts and assets all ship with the system, exactly
  what an orbiting station with limited downlink needs.

## 9. It recognises the experiment by itself

Drop in a video and H.A.L.O. works out which procedure it shows by comparing its scenes with every
procedure in its library, then starts monitoring the right plan automatically. There is no menu
hunting and no manual configuration.

## 10. A mission-console interface

- Live annotated video with a one-click switch for the detection overlay.
- A step timeline stamped with the exact video time of every completion.
- Summary cards for progress, current step, alerts and video time.
- A live panel showing what the AI believes it sees, with a confidence reading for each question.
- Filterable session log, one-click silence, drag-and-drop start.
- Responsive from phone to wall display, with an original identity and offline typography.

## 11. A complete training factory in the browser

From raw footage to a released model without leaving the Training Studio:

upload video → import a timeline → build the procedure → label frames with states and nested
objects → prepare a dataset → pass a quality gate → train on the GPU → evaluate on held-out data →
release and verify.

It also includes a labelling guide written for non-programmers, so scientists and crew trainers can
contribute directly.

## 12. A record nobody can quietly edit, and a downlink measured in bytes

- Every event is **SHA-256 hash-chained and Ed25519-signed** with the station's own key. Edit,
  delete or reorder a line and verification names the exact line that broke.
- Each session is sealed in a **signed downlink report of about 1 KB**, nearly **10,000× smaller**
  than the video it summarises. It holds every step with its time, every alert, and the log's final
  hash, so even a truncated log is caught. That's what a station with limited bandwidth sends to
  the ground.
- UTC and video timestamps, and the confidence and evidence behind every decision.

This mirrors how the space community already handles anomalies: timestamped, reviewable,
immutable.

## 13. The ground sees what the crew sees

The annotated video streams live to any IP address as H.264 over UDP, encoded on the GPU. It opens
in VLC on any computer on the network, while the station keeps its own rolling recording for review.

## 14. Engineered like flight software, not a hackathon demo

- **276 automated tests**, enforced linting, schema-first design.
- Strict schema validation of plans, labels, activity packages and display settings.
- A living validation matrix, risk register and decision log.
- Designed for the path from laptop to station: offline, deterministic, explainable, and
  hardware-light.

---

## Built for the BAS timeline

India's first station module is planned for 2028, with a full station by 2035. Every experiment on
it will run on procedures, and every procedure can become a H.A.L.O. plan. The system is proven
today on ISS-class footage and is ready to grow its procedure library as BAS payloads are defined.

<p align="center"><b>Describe it. Watch it. Trust it.</b></p>
