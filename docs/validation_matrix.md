# Validation Matrix (Phase 0)

| Test | Target | Where | Status |
|---|---|---|---|
| Pydantic schema accepts minimal plan | parses | `tests/test_plan_schema.py::test_experiment_plan_minimal_valid` | pass |
| Pydantic schema accepts full plan | parses | `tests/test_plan_schema.py::test_experiment_plan_full_red_blue` | pass |
| Duplicate step id rejected | error | `tests/test_plan_schema.py::test_experiment_plan_rejects_duplicate_step_ids` | pass |
| Unknown `next` reference rejected | error | `tests/test_plan_schema.py::test_experiment_plan_rejects_unknown_next_ref` | pass |
| Unknown object reference rejected | error | `tests/test_plan_schema.py::test_experiment_plan_rejects_unknown_object_ref` | pass |
| Unreachable step rejected | error | `tests/test_plan_schema.py::test_experiment_plan_rejects_unreachable_step` | pass |
| Extra fields rejected | error | `tests/test_plan_schema.py::test_experiment_plan_rejects_extra_field` | pass |
| `created` field accepts ISO date or string | parses | covered by `coerce_created` validator | pass |
| `validate-plan` CLI returns 0 for valid | exit 0 | `tests/test_cli.py::test_main_returns_0_for_valid` | pass |
| `validate-plan` CLI returns 1 for invalid | exit 1 | `tests/test_cli.py::test_main_returns_1_for_invalid` | pass |
| JSONL `EventRecord` round-trips | parses | `tests/test_event_schema.py::test_event_record_to_jsonl_round_trip` | pass |
| JSONL `EventRecord` rejects out-of-range confidence | error | `tests/test_event_schema.py::test_event_record_rejects_out_of_range_confidence` | pass |
| Ruff lint clean | 0 errors | `ruff check .` | pass |
| Ruff format clean | 0 diffs | `ruff format --check .` | pass |
| React production bundle | builds | `cd web && npm run build` | pass |
| Web dashboard smoke | static bundle + plan summary | `scripts/smoke_web.py` | pass |
| Web service health | HTTP 200 on port 5767 | `GET /api/health` | pass |
| MJPEG frame stream | continuous multipart JPEG payload | `GET /api/stream.mjpg` | pass |
| MP4 dashboard capture | encoded frame + engine status | `on cell.mp4` via `/api/start` | pass |
| Web capture buffer | bounded MP4 segment + CRC event log | `Man_sorting_blocks_in_box_202609030054.mp4` via web runner | pass |
| Red/blue sequence acceptance | six plan steps completed in order with timestamps | `scripts.analyze_sequence` against supplied sorting video | pass |
| CUDA device selection | inference reports `cuda:0` on RTX 5050 | `scripts.analyze_sequence --device auto` | pass |
| Video dataset preparation | sampled frames, video-level splits, manifest, automatic color proposals | `prepare-yolo-dataset` | pass |
| YOLO annotation workflow | local drag-box labels in YOLO format | `annotate-yolo` | pass |
| Training preflight | rejects missing images, validation data, or class labels | `train-yolo` | pass |

## Phase 0 acceptance (per Technical Doc §5)

> "A human reader can correctly predict the step sequence given only the plan
> and a verbal description of the experiment."

To check: hand `experiments/red_blue_box/experiment_plan.yaml` to someone who
has never seen the experiment, give them `notes.md` for context, and ask them
to describe the procedure in their own words. The description should be:

1. Open the big box lid.
2. Take the red block out.
3. Put the red block back inside the box.
4. Take the blue block out.
5. Put the blue block back inside the box.
6. Close the big box lid.

If their description matches in order, Phase 0 is done.

## Phase 2+ acceptance (parked)

| Test | Target |
|---|---|
| Object detection mAP@0.5 on held-out test | ≥ 0.85 |
| 2D pose OKS | ≥ 0.75 |
| Hand F1 | ≥ 0.85 |
| Step-transition accuracy on held-out takes | ≥ 80% (FSM v0) |
| Voice alert latency | ≤ 500ms |
| End-to-end pipeline latency on RTX 5050 | measure and report |
| JSONL parseable + CRC-verified | yes |
| RTSP sub-stream playable by VLC | yes |
| React dashboard update FPS | ≥ 15 |
| Replay determinism | same JSONL bytes for same MP4 |

## Current implementation checks

| Test | Target | Where | Status |
|---|---|---|---|
| Region geometry required for location rules | schema rejects missing or unknown geometry | `tests/test_plan_schema.py` | pass |
| BBox fully inside polygon | `in_region` evidence | `tests/test_evidence.py` | pass |
| BBox outside region | `outside_of` evidence | `tests/test_evidence.py` | pass |
| Live capture worker | frame delivery and clean stop | `halo/web/server.py` session runner | pass |
| Voice worker shutdown | no blocked TTS thread | `tests/test_voice.py` | pass |
| Circular MP4 buffer | bounded rotating segments | `tests/test_io.py` | pass |
| CRC JSONL | tampering detected | `tests/test_io.py` | pass |
| Plan-driven color sequence tracker | red/blue pick-return-close state transitions | `tests/test_sequence.py` | pass |
| Supplied MP4 acceptance | six ordered events and complete state | `scripts/analyze_sequence.py` | pass |

## Historical Training Studio intake checks (superseded — see below)

| Check | Target | Evidence | Status |
|---|---|---|---|
| Separate MELFI activity package | `cold_stowage_melfi` exists without changing the red/blue regression activity | React Studio activity registry and `/api/activities` | pass |
| MELFI procedure validation | eight reachable steps with valid object references | `activities/cold_stowage_melfi/plan.yaml` | pass |
| MELFI video ingestion | uploaded take is readable and metadata is probed by the Studio | take `studying_cells_in_space-c2dce8af89`, 153.04s, 25.0065 FPS, 768x432 | pass |
| MELFI timeline import | eight records reference the generated take ID and valid step IDs | activity timeline endpoint | pass |
| MELFI timeline coverage | records cover the complete 153.04-second take | records cover 0.0–153.04s after tail review | pass |
| MELFI visual annotations | human boxes exist for every intended detector class | STEP 05 annotation count is 0 | pending |
| MELFI dataset preparation | labels and session-level splits are ready | no dataset prepared yet | pending |
| MELFI training/evaluation | CUDA training and held-out evaluation produce reports | no training job or evaluation report yet | pending |

The rows above describe the wrong video (Life Sciences Glovebox footage, since moved to activity
`studying_cells_lsg`). The current MELFI activity is checked below.

## Current MELFI intake checks (2026-09-15)

| Check | Target | Evidence | Status |
|---|---|---|---|
| Real MELFI video ingestion | uploaded take is readable and metadata is probed by the Studio | take `slawosz_using_melfi-8821822197`, 67.16s, ~25.01 FPS, 768x432 | pass |
| MELFI procedure validation | eight single-action, reachable steps with valid object/state references | `activities/cold_stowage_melfi/plan.yaml` v1.1.0 | pass |
| Object states and `inside_of` schema | states expand to per-state detector classes; `inside_of` validated like `outside_of` | `tests/test_state_checker.py`, `tests/test_plan_schema.py` | pass |
| MELFI visual annotations | human boxes drawn by the owner, including nested boxes and states | 775 boxes across 55 frames | pass |
| MELFI dataset preparation | boxed-frame-only dataset with a held-out split | `build_melfi_dataset.py` (scratchpad), 44 train / 11 held-out frames | pass |
| MELFI detector training | CUDA training without horizontal flip (orientation-sensitive classes) | yolo11n, imgsz 768, `fliplr=0`; held-out mAP50 0.79 | pass |
| Checker state-conflict resolution | overlapping same-object states keep only the higher-confidence one | `tests/test_state_checker.py::test_overlapping_state_boxes_keep_only_the_more_confident_state` | pass |
| Checker flicker tolerance | completion/skip confirmation survive a dropped frame or a brief false positive | `tests/test_state_checker.py`, `tests/test_procedure_engine.py::test_flickering_later_step_still_skips_ahead` | pass |
| Full-video step sequence | all 8 steps complete in order with zero alerts | cached-perception replay and live dashboard run on the source video | pass |
| Real-time dashboard playback | uploaded video plays at its own frame rate, GPU-accelerated | `tests/test_web_streaming.py`, live run: 1.00x factor, 25.0 fps delivered | pass |
| GPU-accelerated JPEG encoding with fallback | nvjpeg used when available, OpenCV otherwise | `tests/test_frame_encoder.py` | pass |
| Second independent MELFI session | needed before any generalisation claim | not yet recorded | pending |
| Issue alerts (ice vapour, fabric) | deferred at the owner's request | classes boxed, alert logic not built | pending |

## Phase 2 (procedure engine) acceptance

| Test | Status |
|---|---|
| Golden path: all 6 red/blue steps complete in order | pass (`scripts/samples/red_blue_box_golden.txt`) |
| Skip detection: SKIP_DETECTED alert within 2 frames | pass (`scripts/samples/red_blue_box_skip.txt`) |
| Pause: pause_active flips True after tolerance_s of no progress | pass (`tests/test_procedure_engine.py::test_pause_then_resume`) |
| Silence: alerts suppressed while silence window active | pass (`tests/test_procedure_engine.py::test_silence_window_blocks_alerts`) |
| Rate limit: no new alerts within window_s of last | pass (`tests/test_procedure_engine.py::test_alerter_rate_limits`) |
| Sink atomic: JSONL file appears only after close() | pass (`tests/test_procedure_engine.py::test_jsonl_sink_writes_atomically`) |
| Engine emits to optional sink | pass (`tests/test_procedure_engine.py::test_engine_emits_to_optional_sink`) |

## Described-not-trained (zero-shot) recognition (2026-09-22)

Tested on `studying cells in space.mp4` (153.04 s, a different astronaut at the same MELFI
freezer; MELFI is on screen for roughly the first 22 s). No boxes, no training, no detector file
for this activity - the plan is `activities/melfi_zeroshot/plan.yaml` v0.3.0.

| Check | Target | Evidence | Status |
|---|---|---|---|
| Trained detector on an unseen video | baseline for comparison | misses freezer/dewars/tray/sample; labels the glovebox `melfi_freezer` on 63% of frames | fail (expected) |
| Text-prompted detection without training | generic objects found from descriptions | YOLOE + MobileCLIP finds person/gloves/tablet; MELFI-specific parts and states are not reliable from prompts alone | partial |
| VLM question on a coarse state | usable accuracy on a video nobody trained on | "is the tray pulled out" accuracy 0.87, recall 0.94 | pass |
| VLM question on a fine state | compartment lid, latch side | below 0.5 accuracy; not usable yet | fail |
| Absence-phrased questions | any usable accuracy | recall 0.00 for "pushed back in" and "all doors closed"; accuracy 0.24 for "compartment closed" | fail (design changed to `expect: no`) |
| Questions never block analysis | 25 fps analysis with the VLM running | `AsyncVisualQuestioner` on its own thread; run held 1.0x real time, 36 answers over 153 s | pass |
| Zero-shot mode selected automatically | activity without `models/detector.pt` but with prompts | dashboard run reported `mode: zero_shot`, cuda:0, detect 35.4 ms/frame | pass |
| Steps recognised on the unseen video | procedure followed from an English description only | steps 1-5 completed at 4.9, 8.5, 8.6, 13.7, 17.2 s, all inside the MELFI section, no alerts | partial (5 of 8) |
| Closing steps not satisfied by unrelated footage | no completion once MELFI leaves frame | v0.2.0 falsely completed steps 6-8 at 35.7/54.6/59.3 s; v0.3.0 equipment-visible guard leaves them open | pass after fix |
| Steps 2 and 3 distinguishable | separate completion times for separate actions | completed 0.12 s apart - too fast to be a real reading | fail |

## Described mode, second pass (2026-09-23)

Corrects the section above: the new video holds two MELFI cycles (cycle 1: door ~3.5 s, tray out
4.0, sample out 5.0, tray back 6.5, door closed ~7.5; cycle 2: 16-21 s), and the
"equipment visible" guard never worked. Question scores are on the owner's 55 boxed Slawosz
frames, which the VLM has never seen.

| Check | Target | Evidence | Status |
|---|---|---|---|
| Probabilities from one forward pass | as calibrated as generating, faster | tray out acc 0.98 at 0.5 (AUC 1.00); 0.61 s vs 2.85 s for 9 questions | pass |
| Each question asked alone | usable at a 0.5 cut | biased to "yes": tray acc 0.45 at 0.5; grey-image calibration does not fix it | fail (not used) |
| Zoom on the tray for the lid state | lid readable from a crop | oracle crop AUC 0.87 -> 0.91; the lid is under the glove | fail (not used) |
| Uncertain answers ignored | a dead question cannot complete a step | dead band 0.6/0.4; `test_answers_between_the_cut_offs_are_unsure_and_match_nothing`; Slawosz wrong completions 5 -> 1 on cached answers | pass |
| Questions-only plan skips the detector | full-rate analysis while the VLM runs | 25 fps analysis, detect 0.03 ms (was ~9 fps, 108 ms) | pass |
| Zero-shot on the new video (v0.4.0) | steps in order, in the right cycle, none on unrelated footage | 5/5 during cycle 1, 1.4-2.3 s behind the action; nothing during 130 s of glovebox footage; no alerts | pass |
| Hybrid mode (trained detector + questions) | runs live, same result as trained-only | Slawosz 8/8 in order, no alerts, each ~0.6 s later; `mode: hybrid` | pass |
| Detector speed in hybrid mode | unchanged | ~9-18 ms -> ~70-100 ms per frame; real time kept by skipping frames | known cost |
| Studio keeps `expect` | re-saving a plan does not invert a step | builder loads, edits and saves `expect` | pass (manual) |
| Qwen3-VL-4B vs 2B | better end to end | better per frame on Slawosz (door AUC 0.96 vs 0.86) but worse on the new video's fisheye view (misses the tray) | not adopted |
| Deployed v0.4.0 on Slawosz (unseen by the VLM) | steps within 2.5 s | 2/5; every miss early (2.7-5.7 s), none random | partial |
| Deployed v0.4.0 on the new video (replay) | steps within 2.5 s | 4/4 checkable steps | pass |

## Requirement closure: stream to IP, next-step voice, signed record (2026-09-26)

| Check | Target | Evidence | Status |
|---|---|---|---|
| One-command reproduction | ISS take end to end from a clean checkout | `python -m halo verify`: 8/8 steps in order, 0 alerts, 37 s on cuda:0 | pass |
| Skipped step on real footage | the same take with step 1 cut out raises a skip | `verification/step1_removed.mp4`: SKIP_DETECTED at 1.48 s, OUT_OF_ORDER at 3.0 s; same in the real-time dashboard | pass |
| Signed, hash-chained log | edits, deletions, reordering, forged signatures and other keys detected | `tests/test_signed_log.py`; one edited field in a real log reported at its line | pass |
| Downlink report | signed, kilobyte-scale, seals the log | MELFI: 1,002 bytes, 9,701x smaller than the 9.7 MB video; a truncated log fails the seal | pass |
| Stream to a specific IP | playable stream on another process | 508 H.264 frames decoded from `udp://127.0.0.1:5000` during a dashboard run (h264_nvenc); mpeg2video and libx264 fallbacks tested | pass |
| Next step spoken | at the start and after every step | MELFI dashboard run: "Monitoring MELFI sample stowage. First: ..." then "Step N done. Next: ..." for steps 1-7, "Step 8 done. Procedure complete." | pass |
| Step overdue alert | a step current longer than its `timeout_s` alerts once | `test_step_overdue_fires_once_after_timeout`; MELFI 60 s timeouts raise nothing on the 67 s take | pass |
| Hindi announcements | every phrase has a Hindi form; falls back to English without a Hindi voice | phrases checked in Node; dashboard shows the missing-voice notice on this machine (no Hindi voice installed) | pass (voice untested) |
| Offline model load | vision-language model never waits on the network when cached | `test_model_loads_from_cache_without_network` | pass |
| Live source with a custom detector | trained classes are not filtered out | MELFI started from the launch config: was stuck on step 1 (stock-class filter); after `uses_default_classes_only`, 8/8 | pass (fixed) |
