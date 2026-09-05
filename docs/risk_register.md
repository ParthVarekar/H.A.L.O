# Risk Register (Phase 0)

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Dataset too small (~20 takes) → overfitting | High | High | Session-level train/val/test split (not random frames). Augmentation 5-10×. Multiple actors if possible. |
| 2 | Jetson latency assumed, not measured | Medium | High | ONNX export from Phase 2 onwards. Benchmark on RTX 5050 with TensorRT engine for early read on inference cost. |
| 3 | PyInstaller packaging failures (JIT, dynamic CUDA) | Medium | Medium | Keep CUDA optional. CPU ONNX path is the default. Document Jetson re-bake as separate step in Phase 9. |
| 4 | Judges ask "what if the model is uncertain?" | High | Medium | `unknown` step state in FSM, visible to ground operator only. Per Technical Doc decision §11. |
| 5 | Demo hardware (webcam) fails on stage | Medium | High | Pre-recorded backup MP4 + replay harness (`scripts/replay.py`, Phase 6). |
| 6 | PyYAML auto-coerces unquoted `2026-09-03` to `datetime.date` | High | Low | `created` field validator normalises both forms to ISO string. |
| 7 | Python 3.14 ships on user's PATH; MediaPipe / PyTorch lag | Certain | Medium | `pyproject.toml` pins `<3.14`. README shows `py -3.11 -m venv .venv`. AGENTS.md documents the reason. |
| 8 | Hand-object interaction labels (`grasping`, `placing`, `opening`, `closing`) are ambiguous | High | Medium | Heuristic v1 = hand distance to object + hand velocity. Replace with learned head in v2 (Phase 9). |
| 11 | MediaPipe 1.x removed `mp.solutions` API | High | Medium | `pyproject.toml` pins `mediapipe==0.10.21`; opencv-python<5 + numpy<2 to keep wheels consistent on 3.11. |
| 12 | COCO `box` class doesn't match toy boxes / coloured cubes | High | High | Fine-tune YOLOv11-n on 3 classes (big_box, small_red_box, small_blue_box) once ≥20 takes recorded. Phase 1. |
| 13 | CPU inference at 6 fps is too slow for the live dashboard | High | Medium | Pipeline already GPU-aware (`device="0"` swap once Phase 1 tests pass). Real-time target is RTX 5050 GPU, not laptop CPU. |
| 14 | Region polygon geometry can be calibrated incorrectly | Medium | Medium | `region_geometries` is schema-validated and evidence requires every axis-aligned BBox corner to be inside the polygon. Calibrate polygons against the camera view before recording. |
| 15 | Skip detection fires on natural transition if later-step accumulator matches early | High | Medium | Resolved: only flag skip when current step is NOT satisfied and a later step IS. Transition path uses `_pick_next` which doesn't go through skip path. |
| 16 | YOLO's `cls` and the plan's `object_id` are different things | High | High | Resolved: YAML `objects[].id` is a logical name; YAML `objects[].classes` is the detector's class. Evidence checks the `cls` from the detector against the spec's `classes`. Replay DSL and tests use the correct mapping. |
| 9 | Region geometry is camera-view dependent | Medium | Low | Store polygons in the experiment plan for the selected camera resolution; add calibration tooling if camera placement changes. |
| 10 | 3D HMR is parked but docs call it the "innovation differentiator" | High | Low | Strategic Research doc reframes as "orientation-diverse augmentation" which we can ship in 2D first (Phase 9) without SMPL. |
