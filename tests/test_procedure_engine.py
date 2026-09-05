"""Tests for the procedure engine.

Uses a tiny 3-step plan + mocked PerceptionResult frames so the FSM can be
exercised without any real perception models. Covers: golden path, skip
detection, out-of-order attempt, pause, silence, rate limit.
"""

from __future__ import annotations

from pathlib import Path

from bas_har.perception.types import (
    BBox,
    Detection,
    HandKeypoints,
    HandObjectInteraction,
    PerceptionResult,
    PoseKeypoints,
)
from bas_har.procedure import (
    EngineState,
    JsonlEventSink,
    build_engine,
)
from bas_har.schema.cli import load_plan
from bas_har.schema.event_schema import AlertCode, EventRecord, StepStatus
from bas_har.schema.plan_schema import ExperimentPlan

PLAN_YAML = """
id: TEST-3STEP
name: Three Step Test
objects:
  - id: a
    classes: [a]
  - id: b
    classes: [b]
  - id: c
    classes: [c]
steps:
  - id: do_a
    description: do a
    evidence:
      - kind: hand_object_interaction
        object: a
        label: grasping
        min_frames: 2
    next: [do_b]
  - id: do_b
    description: do b
    evidence:
      - kind: hand_object_interaction
        object: b
        label: grasping
        min_frames: 2
    next: [do_c]
  - id: do_c
    description: do c
    evidence:
      - kind: hand_object_interaction
        object: c
        label: grasping
        min_frames: 2
    next: []
alert_policy:
  skip_confidence_threshold: 0.5
  skip_persistence_frames: 2
  rate_limit_s: 0.0
  silence_window_s: 5.0
  pause_tolerance_s: 0.1
"""


def _plan() -> ExperimentPlan:
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(PLAN_YAML)
        path = Path(f.name)
    try:
        return load_plan(path)
    finally:
        path.unlink(missing_ok=True)


def _result_with_hoi(
    target_cls: str, label: str = "grasping", conf: float = 0.9
) -> PerceptionResult:
    hand = HandKeypoints(handedness="right", score=0.9, keypoints=[(0, 0, 0)] * 21)
    hand.keypoints[8] = (50.0, 50.0, 0.9)
    det = Detection(cls=target_cls, conf=conf, bbox=BBox(0, 0, 100, 100))
    hoi = HandObjectInteraction(hand="right", object_cls=target_cls, label=label, score=conf)
    return PerceptionResult(
        frame_id=0,
        ts_ms=0,
        width=100,
        height=100,
        detections=[det],
        pose=PoseKeypoints(keypoints=[(50, 50, 0.9)] * 33, score=0.9),
        hands=[hand],
        hoi=[hoi],
    )


def _empty_result(frame_id: int = 0) -> PerceptionResult:
    return PerceptionResult(frame_id=frame_id, ts_ms=0, width=100, height=100)


def test_golden_path_completes_all_steps(tmp_path: Path) -> None:
    plan = _plan()
    sink_path = tmp_path / "events.jsonl"
    engine = build_engine(plan, sink_path=sink_path)

    for _ in range(3):
        engine.step(_result_with_hoi("a"))
    assert engine.current_step.id == "do_b"
    for _ in range(3):
        engine.step(_result_with_hoi("b"))
    assert engine.current_step.id == "do_c"
    for _ in range(3):
        engine.step(_result_with_hoi("c"))
    assert engine.state == EngineState.COMPLETED
    assert engine.current_step is None
    engine.close()

    lines = sink_path.read_text(encoding="utf-8").splitlines()
    assert any('"step_id":"do_a"' in line and '"step_status":"completed"' in line for line in lines)
    assert any('"step_id":"do_c"' in line and '"step_status":"completed"' in line for line in lines)


def test_skip_detection_fires_alert() -> None:
    plan = _plan()
    engine = build_engine(plan)
    for _ in range(2):
        engine.step(_result_with_hoi("a"))
    assert engine.current_step.id == "do_b"
    for _ in range(5):
        out = engine.step(_result_with_hoi("c"))
    assert AlertCode.SKIP_DETECTED in out.fired_alerts


def test_pause_then_resume() -> None:
    plan = _plan()
    engine = build_engine(plan)
    out = engine.step(_result_with_hoi("a"))
    assert out.state == EngineState.IN_PROGRESS
    import time

    time.sleep(plan.alert_policy.pause_tolerance_s * 1.5)
    out = engine.step(_empty_result())
    assert out.pause_active or out.state == EngineState.PAUSED
    out = engine.step(_result_with_hoi("a"))
    assert out.state == EngineState.IN_PROGRESS


def test_silence_window_blocks_alerts() -> None:
    plan = _plan()
    engine = build_engine(plan)
    for _ in range(2):
        engine.step(_result_with_hoi("a"))
    engine.silence()
    assert engine.alerter.silence_active()
    for _ in range(5):
        out = engine.step(_result_with_hoi("c"))
    assert AlertCode.SKIP_DETECTED not in out.fired_alerts


def test_alerter_rate_limits() -> None:
    plan = _plan()
    plan.alert_policy.rate_limit_s = 100.0
    engine = build_engine(plan)
    for _ in range(2):
        engine.step(_result_with_hoi("a"))
    for _ in range(5):
        engine.step(_result_with_hoi("c"))
    first_count = len(engine.alerter.fired())
    for _ in range(5):
        engine.step(_result_with_hoi("c"))
    assert len(engine.alerter.fired()) == first_count


def test_jsonl_sink_writes_atomically(tmp_path: Path) -> None:
    sink_path = tmp_path / "sub" / "events.jsonl"
    with JsonlEventSink(sink_path) as sink:
        sink.write(
            EventRecord(
                ts_utc=EventRecord.now_utc(),
                exp_id="X",
                step_id="s1",
                step_status=StepStatus.IN_PROGRESS,
                confidence=0.5,
                evidence_summary="ok",
            )
        )
    assert sink_path.exists()
    assert sink_path.read_text(encoding="utf-8").count("\n") == 1


def test_engine_emits_to_optional_sink(tmp_path: Path) -> None:
    plan = _plan()
    sink_path = tmp_path / "events.jsonl"
    engine = build_engine(plan, sink_path=sink_path)
    for _ in range(3):
        engine.step(_result_with_hoi("a"))
    engine.close()
    body = sink_path.read_text(encoding="utf-8")
    assert '"step_id":"do_a"' in body
