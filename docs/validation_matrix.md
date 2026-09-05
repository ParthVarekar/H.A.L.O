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
| Live capture worker | frame delivery and clean stop | `bas_har/web/server.py` session runner | pass |
| Voice worker shutdown | no blocked TTS thread | `tests/test_voice.py` | pass |
| Circular MP4 buffer | bounded rotating segments | `tests/test_io.py` | pass |
| CRC JSONL | tampering detected | `tests/test_io.py` | pass |
| Plan-driven color sequence tracker | red/blue pick-return-close state transitions | `tests/test_sequence.py` | pass |
| Supplied MP4 acceptance | six ordered events and complete state | `scripts/analyze_sequence.py` | pass |

## Current Training Studio intake checks

| Check | Target | Evidence | Status |
|---|---|---|---|
| Separate MELFI activity package | `cold_stowage_melfi` exists without changing the red/blue regression activity | React Studio activity registry and `/api/activities` | pass |
| MELFI procedure validation | six reachable steps with valid object references | `activities/cold_stowage_melfi/plan.yaml` | pass |
| MELFI video ingestion | uploaded take is readable and metadata is probed by the Studio | take `studying_cells_in_space-c2dce8af89`, 153.04s, 25.0065 FPS, 768x432 | pass |
| MELFI timeline import | six records reference the generated take ID and valid step IDs | activity timeline endpoint | pass |
| MELFI timeline coverage | records cover the complete 153.04-second take | supplied records stop at 105.0s | review required |
| MELFI visual annotations | human boxes exist for every intended detector class | STEP 05 annotation count is 0 | pending |
| MELFI dataset preparation | labels and session-level splits are ready | no dataset prepared yet | pending |
| MELFI training/evaluation | CUDA training and held-out evaluation produce reports | no training job or evaluation report yet | pending |

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
