# H.A.L.O. deployment roadmap

How H.A.L.O. goes from a verified laptop prototype to a system running on board the Bharatiya
Antariksh Station (BAS). Stage 0 is done and measured. Everything after it is a plan: the targets
are goals to be proven, not results.

## Where we are today (Stage 0, done)

| What | Measured on the current prototype |
|---|---|
| Runs fully offline | No cloud calls; models, voices and the dashboard all run locally |
| Real-time on real station footage | 1.00× real time on the ESA Ignis MELFI video, RTX 5050 laptop GPU |
| Detection cost | About 9 ms per frame for the trained YOLO11 detector (GPU, FP32) |
| Detector accuracy | 0.80 mAP@0.5 on held-out frames |
| Procedure result | 8 of 8 steps recognised in order, 0 false alerts |
| Skip detection | A removed step is caught 1.48 s into the clip |
| Record | SHA-256 hash-chained, Ed25519-signed log; a signed ~1 KB downlink report |
| Proof | `python -m halo verify` passes 8/8 checks; 276 automated tests |
| Portability | ONNX export (`export-onnx`) and a PyInstaller build (`packaging/halo_gui.spec`) |

## Stage 1: ground-ready package

Goal: anyone at a ground facility can install and run H.A.L.O. without a developer.

- One signed installer for the station laptop class of machine, with models, voices and the
  dashboard bundled; no internet needed at install or run time.
- The ONNX Runtime CPU path as the default, and CUDA only when a GPU is present.
- Station signing keys generated at install; the public key exported for ground verification.
- Configuration by YAML only: camera source, stream target, language, alert thresholds.
- Exit check: `python -m halo verify` passes on a clean machine with no developer tools.

## Stage 2: edge hardware

Goal: run on a small, low-power computer mounted next to the experiment rack.

- Target board: NVIDIA Jetson Orin Nano or NX class, as a stand-in for flight compute.
- Convert the detector from ONNX to TensorRT; evaluate FP16 and INT8 quantisation against the
  FP32 accuracy baseline, and accept a precision only if mAP and the 8/8 procedure result hold.
- Measure, don't assume: frames per second, per-frame latency, power draw and memory on the
  board, for the trained and the described (vision-language) modes.
- If the vision-language model does not fit, run described mode at a lower question rate or
  keep it ground-side for authoring only.
- Exit check: the reference run reaches 8/8 steps at real time on the board, within its power
  budget.

## Stage 3: more experiments, more crew

Goal: prove the "one file per experiment" claim across the BAS science programme.

- Add procedures for more rack experiments using the Training Studio (a few labelled frames per
  object) or described mode (plain-English step questions, no training).
- Record takes with several operators, camera angles and lighting, and use session-level splits
  so no test footage leaks into training.
- Orientation-diverse augmentation, so the detector handles crew working at any orientation
  in microgravity.
- Track per-experiment accuracy, false-alert rate and time-to-detect a skip in
  `docs/validation_matrix.md`.

## Stage 4: integrated ground trials

Goal: run H.A.L.O. alongside real crew training, with ISRO's procedures and cameras.

- Integrate with the station's camera feeds (RTSP or the onboard video standard) and its
  crew-alert audio.
- Downlink path: send only the signed ~1 KB session reports routinely, and the full log or
  video on request, to fit a limited downlink budget.
- Uplink path: deliver new or corrected procedure files as signed YAML packages, validated by
  `validate-plan` before they can be loaded.
- Operator review: crew and trainers rate every alert as correct, missed or false; these
  ratings set the go/no-go thresholds for flight.
- Exit check: agreed accuracy and false-alert targets met over a full training campaign.

## Stage 5: flight qualification

Goal: meet the requirements for software and hardware flying on the station.

- Software assurance: requirements traceability (started in `docs/SIH_REQUIREMENTS.md`),
  code review, test coverage and configuration control to the space agency's standards.
- Hardware: qualify the compute board or move to a qualified equivalent, covering radiation
  tolerance, thermal limits, vibration at launch, and power.
- Safety: H.A.L.O. advises and records; it never controls experiment hardware. Alerts can be
  silenced by the crew, and a failure of H.A.L.O. must never stop an experiment.
- Fallback: if the camera or model fails, the crew continues from the written procedure and
  the log records the gap.

## Stage 6: on-orbit operations

Goal: routine use on BAS experiments.

- Start with one experiment rack under close ground monitoring, then widen.
- Per-session signed reports downlinked for every experiment run.
- Model and procedure updates uplinked as signed packages, with a rollback to the last good
  version.
- Feed flight footage back (where permitted) into training to improve accuracy over time.

## Open risks

| Risk | Plan |
|---|---|
| Edge latency is assumed, not yet measured | Stage 2 benchmarks on real hardware before any claims |
| Small datasets can overfit | Session-level splits; more operators and angles in Stage 3 |
| Vision-language model size on edge hardware | Lower question rate, a smaller model, or ground-only authoring |
| Flight hardware may differ from Jetson | Keep the ONNX path portable; re-benchmark on the qualified board |

See `docs/risk_register.md` for the full risk list.
