# SIH26174 requirement traceability

Each requirement of problem statement SIH26174 (AI Human Activity Recognition for on-board BAS
experiments) mapped to where it lives in the code, the tests that hold it in place, and the moment in
the jury demo that shows it working. All 276 tests pass on every start: `startup.bat` refuses to
launch the dashboard unless pytest, Ruff, the plan check, the build and the smoke test all pass.

**Reproduce the headline result on any machine:** `python -m bas_har verify` (see
[VERIFICATION.md](VERIFICATION.md)).

| # | Requirement | Status | Where it lives | Tests | See it live |
|---|---|---|---|---|---|
| 1 | Continuously process video locally and track the experiment's sequence | **Met** | `bas_har/web/server.py` `SessionRunner` (capture, presentation and recording threads); `bas_har/perception/`; `bas_har/procedure/engine.py` | `test_procedure_engine.py`, `test_web_streaming.py`, `test_engine.py` | [Jury demo, 0:30](JURY_DEMO.md#030--the-judge-picks-the-video) |
| 2 | Suggest the next step at the start and after each step | **Met** | `instruction` per step in the plan YAML (`plan_schema.StepSpec`); `web/src/speech.js`; the Now bar shows the current and the next instruction | `test_plan_schema.py::test_experiment_plan_accepts_spoken_text_in_english_and_hindi`, `test_web.py::test_plan_summary_carries_spoken_instructions` | Spoken: "Step 2 done. Next: pull tray 2 out of dewar 1." |
| 3 | Voice alert when a step is skipped or done out of sequence | **Met** | `ProcedureEngine` raises `SKIP_DETECTED`, `OUT_OF_ORDER`, `PAUSE_EXCEEDED` and `STEP_OVERDUE`; `web/src/voice.js` puts alerts ahead of every other announcement | `test_skip_detection_fires_alert`, `test_skipped_step_seen_later_completes_out_of_order`, `test_step_overdue_fires_once_after_timeout` | [Jury demo, 2:00](JURY_DEMO.md#200--skip-a-step) |
| 4 | Timestamped, structured, lightweight text record of the steps and their outcomes | **Met, signed** | `bas_har/io/signed_log.py`: one JSON line per event, SHA-256 hash-chained and Ed25519-signed, plus a signed ~1 KB downlink report that seals the chain | `test_signed_log.py` (edit, delete, reorder, truncate and forged-signature cases), `test_evidence_schema.py` | [Jury demo, 3:15](JURY_DEMO.md#315--prove-the-record) |
| 5 | Stream video to a specific IP address and store it locally | **Met** | `bas_har/io/stream_out.py` sends MPEG-TS over UDP to any IP (H.264 on the GPU with NVENC, with software fallbacks); `bas_har/io/circular_buffer.py` keeps a rolling MP4 recording per session | `test_stream_out.py`, `test_stream_schema.py`, `test_web.py::test_stream_out_api_merges_settings_and_streams_frames`, `test_io.py` | [Jury demo, 2:45](JURY_DEMO.md#245--the-ground-sees-it-too) |
| 6 | A graphical monitoring interface | **Met** | `web/src/` React dashboard: live annotated video, step timeline, metrics, session log, model answers, stream control, signed report; light and dark themes | `test_web.py`, `scripts/smoke_web.py` | Whole demo |
| 7 | Deliver a trained AI model running on an offline, standalone system | **Met** | `activities/cold_stowage_melfi/models/detector.pt`: YOLO11n trained on 55 labelled frames of real ISS footage (839 annotations), held-out mAP50 0.79. Everything runs locally; the vision-language model loads from the local cache first | `test_training_pipeline.py`, `test_zero_shot.py::test_model_loads_from_cache_without_network` | [Jury demo, 0:00](JURY_DEMO.md#000--wi-fi-off) |
| – | Build a focused local dataset for the experiment | **Met** | Training Studio (`bas_har/studio/`): takes, timelines, box labelling, dataset versions with session-level splits, quality gate, training, evaluation, checksummed release. `experiments/red_blue_box/` implements the reference red/blue-box procedure | `test_datasets.py`, `test_annotations.py`, `test_quality.py`, `test_releases.py` | Training Studio tab |
| – | Optional: orientation-agnostic 3D human mesh recovery | Not in this release | Steps are recognised from object states and procedure evidence rather than body pose | – | – |

## Beyond the checklist

- **Train-free mode.** A step can be written as a plain-English yes/no question and monitored
  straight away by a local Qwen3-VL model. There's also a hybrid mode that mixes questions with a
  trained detector.
- **Recognises the experiment by itself.** It compares a new video's scenes with every procedure in the library.
- **English and Hindi voice**, using the computer's own offline voices.
- **Real footage, not a simulation.** The reference result is ESA's Ignis mission footage of the
  MELFI −80 °C freezer, and the footage, labels and trained detector are all in this repository.
