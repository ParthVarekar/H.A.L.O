"""Tests for the procedure engine.

Uses a tiny 3-step plan + mocked PerceptionResult frames so the FSM can be
exercised without any real perception models. Covers: golden path, skip
detection, out-of-order attempt, pause, silence, rate limit.
"""

from __future__ import annotations

from pathlib import Path

from halo.perception.types import (
    BBox,
    Detection,
    HandKeypoints,
    HandObjectInteraction,
    PerceptionResult,
    PoseKeypoints,
)
from halo.procedure import (
    EngineState,
    JsonlEventSink,
    build_engine,
)
from halo.schema.cli import load_plan
from halo.schema.event_schema import AlertCode, EventRecord, StepStatus
from halo.schema.plan_schema import ExperimentPlan

PLAN_YAML = """
id: TEST-3STEP
name: Three Step Test
camera:
  fps: 4
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
    for _ in range(8):
        out = engine.step(_result_with_hoi("c"))
    assert AlertCode.SKIP_DETECTED in out.fired_alerts


def test_persistent_later_step_skips_ahead() -> None:
    plan = _plan()
    engine = build_engine(plan)
    for _ in range(2):
        engine.step(_result_with_hoi("a"))
    events = []
    for _ in range(8):
        events.extend(engine.step(_result_with_hoi("c")).events)
    assert engine.state == EngineState.COMPLETED
    assert engine.skipped_step_ids == ["do_b"]
    statuses = [(event.step_id, event.step_status) for event in events]
    assert ("do_b", StepStatus.SKIPPED) in statuses
    assert ("do_c", StepStatus.COMPLETED) in statuses
    skipped_event = next(event for event in events if event.step_status == StepStatus.SKIPPED)
    assert skipped_event.alert_code == AlertCode.SKIP_DETECTED
    assert skipped_event.extra["detected_step_id"] == "do_c"


def test_single_frame_of_later_step_does_not_skip() -> None:
    plan = _plan()
    engine = build_engine(plan)
    for _ in range(2):
        engine.step(_result_with_hoi("a"))
    engine.step(_result_with_hoi("c"))
    engine.step(_result_with_hoi("c"))
    out = engine.step(_empty_result())
    assert out.current_step_id == "do_b"
    assert engine.skipped_step_ids == []
    assert AlertCode.SKIP_DETECTED not in out.fired_alerts


def test_skipped_step_seen_later_completes_out_of_order() -> None:
    plan = _plan()
    plan.steps.append(plan.steps[2].model_copy(update={"id": "do_d", "next": []}, deep=True))
    plan.steps[2].next = ["do_d"]
    plan.steps[3].evidence[0].object = "a"
    engine = build_engine(plan)
    for _ in range(2):
        engine.step(_result_with_hoi("a"))
    for _ in range(8):
        engine.step(_result_with_hoi("c"))
    assert engine.skipped_step_ids == ["do_b"]
    assert engine.current_step.id == "do_d"
    events = []
    for _ in range(8):
        events.extend(engine.step(_result_with_hoi("b")).events)
    late = [event for event in events if event.step_id == "do_b"]
    assert late[0].step_status == StepStatus.COMPLETED
    assert late[0].alert_code == AlertCode.OUT_OF_ORDER
    assert engine.skipped_step_ids == []
    assert engine.current_step.id == "do_d"


def test_flickering_later_step_still_skips_ahead() -> None:
    plan = _plan()
    engine = build_engine(plan)
    for _ in range(2):
        engine.step(_result_with_hoi("a"))
    for _ in range(4):
        engine.step(_result_with_hoi("c"))
        engine.step(_result_with_hoi("c"))
        engine.step(_empty_result())
    engine.step(_result_with_hoi("c"))
    assert engine.skipped_step_ids == ["do_b"]
    assert engine.state == EngineState.COMPLETED


def test_brief_burst_of_later_step_does_not_skip() -> None:
    plan = _plan()
    engine = build_engine(plan)
    for _ in range(2):
        engine.step(_result_with_hoi("a"))
    for _ in range(3):
        engine.step(_result_with_hoi("c"))
    for _ in range(6):
        out = engine.step(_empty_result())
    assert out.current_step_id == "do_b"
    assert engine.skipped_step_ids == []
    assert AlertCode.SKIP_DETECTED not in out.fired_alerts


def test_media_time_rate_limit_ignores_wall_clock() -> None:
    plan = _plan()
    plan.alert_policy.rate_limit_s = 5.0
    engine = build_engine(plan, use_media_time=True)
    assert engine.alerter.fire(_candidate(), now=0.0)
    assert not engine.alerter.fire(_candidate(), now=4.0)
    assert engine.alerter.fire(_candidate(), now=5.5)


def _candidate():
    from halo.procedure import AlertCandidate

    return AlertCandidate(
        code=AlertCode.SKIP_DETECTED,
        step_id="do_b",
        message="",
        confidence=0.9,
        persistence_frames=5,
        extra={},
    )


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
    for _ in range(8):
        out = engine.step(_result_with_hoi("c"))
    assert AlertCode.SKIP_DETECTED not in out.fired_alerts


def test_alerter_rate_limits() -> None:
    plan = _plan()
    plan.alert_policy.rate_limit_s = 100.0
    engine = build_engine(plan)
    for _ in range(2):
        engine.step(_result_with_hoi("a"))
    for _ in range(8):
        engine.step(_result_with_hoi("c"))
    first_count = len(engine.alerter.fired())
    for _ in range(8):
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


def _at(result: PerceptionResult, seconds: float) -> PerceptionResult:
    result.ts_ms = round(seconds * 1000)
    return result


def test_media_time_pause_ignores_wall_clock() -> None:
    plan = _plan()
    plan.alert_policy.pause_tolerance_s = 2.0
    engine = build_engine(plan, use_media_time=True)
    engine.step(_at(_result_with_hoi("a"), 0.0))
    out = engine.step(_at(_empty_result(), 1.0))
    assert not out.pause_active
    out = engine.step(_at(_empty_result(), 2.5))
    assert out.pause_active


def test_pause_tolerance_follows_completed_step_duration() -> None:
    plan = _plan()
    plan.alert_policy.pause_tolerance_s = 2.0
    plan.steps[0].expected_duration_s = 10.0
    engine = build_engine(plan, use_media_time=True)
    engine.step(_at(_result_with_hoi("a"), 0.0))
    out = engine.step(_at(_result_with_hoi("a"), 0.1))
    assert out.current_step_id == "do_b"
    assert engine.pause_watchdog.tolerance_s == 15.0
    out = engine.step(_at(_empty_result(), 10.0))
    assert not out.pause_active
    out = engine.step(_at(_empty_result(), 15.2))
    assert out.pause_active
    assert out.last_event is not None
    assert out.last_event.alert_code == AlertCode.PAUSE_EXCEEDED


def test_pause_tolerance_never_drops_below_policy() -> None:
    plan = _plan()
    plan.alert_policy.pause_tolerance_s = 2.0
    engine = build_engine(plan)
    assert engine.pause_tolerance_after(plan.steps[0]) == 2.0
    plan.steps[0].expected_duration_s = 1.0
    assert engine.pause_tolerance_after(plan.steps[0]) == 2.0
    plan.steps[0].expected_duration_s = 4.0
    assert engine.pause_tolerance_after(plan.steps[0]) == 6.0


def test_media_time_events_record_video_time() -> None:
    plan = _plan()
    engine = build_engine(plan, use_media_time=True)
    engine.step(_at(_result_with_hoi("a"), 3.0))
    out = engine.step(_at(_result_with_hoi("a"), 3.04))
    assert out.last_event is not None
    assert out.last_event.step_status == StepStatus.COMPLETED
    assert out.last_event.extra["video_time_s"] == 3.04


def test_wall_clock_mode_does_not_record_video_time() -> None:
    plan = _plan()
    engine = build_engine(plan)
    for _ in range(2):
        out = engine.step(_result_with_hoi("a"))
    assert out.last_event is not None
    assert "video_time_s" not in out.last_event.extra


def _overdue_events(engine_events: list[EventRecord]) -> list[EventRecord]:
    return [event for event in engine_events if event.alert_code == AlertCode.STEP_OVERDUE]


def test_step_overdue_fires_once_after_timeout() -> None:
    plan = _plan()
    plan.alert_policy.pause_tolerance_s = 100.0
    plan.steps[0].timeout_s = 3.0
    engine = build_engine(plan, use_media_time=True)
    seen: list[EventRecord] = []
    for second in (0.0, 1.0, 2.9):
        seen += engine.step(_at(_empty_result(), second)).events
    assert _overdue_events(seen) == []
    for second in (3.2, 4.0, 9.0):
        seen += engine.step(_at(_empty_result(), second)).events
    overdue = _overdue_events(seen)
    assert len(overdue) == 1
    assert overdue[0].step_id == "do_a"
    assert overdue[0].step_status == StepStatus.ANOMALOUS
    assert overdue[0].extra["timeout_s"] == 3.0


def test_step_overdue_clock_restarts_for_each_step() -> None:
    plan = _plan()
    plan.alert_policy.pause_tolerance_s = 100.0
    plan.steps[1].timeout_s = 3.0
    engine = build_engine(plan, use_media_time=True)
    engine.step(_at(_result_with_hoi("a"), 10.0))
    out = engine.step(_at(_result_with_hoi("a"), 10.1))
    assert out.current_step_id == "do_b"
    assert _overdue_events(engine.step(_at(_empty_result(), 12.0)).events) == []
    assert len(_overdue_events(engine.step(_at(_empty_result(), 13.5)).events)) == 1


def test_step_without_timeout_never_goes_overdue() -> None:
    plan = _plan()
    plan.alert_policy.pause_tolerance_s = 1000.0
    engine = build_engine(plan, use_media_time=True)
    seen: list[EventRecord] = []
    for second in (0.0, 100.0, 500.0):
        seen += engine.step(_at(_empty_result(), second)).events
    assert _overdue_events(seen) == []
