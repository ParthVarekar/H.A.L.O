"""Tests for object states, the inside_of rule, and state-aware datasets and annotations."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from bas_har.perception.types import BBox, Detection, PerceptionResult
from bas_har.procedure import EngineState, build_engine
from bas_har.procedure.evidence import EvidenceAccumulator
from bas_har.schema.activity_schema import ActivityKind, ActivityManifest
from bas_har.schema.plan_schema import EvidenceRule, ExperimentPlan, ObjectSpec, StepSpec
from bas_har.studio.annotations import delete_annotation, list_annotations, save_annotation
from bas_har.studio.datasets import annotation_class
from bas_har.studio.plans import save_activity_plan
from bas_har.studio.registry import ActivityRegistry
from bas_har.studio.takes import register_take


def _plan(steps: list[dict]) -> ExperimentPlan:
    return ExperimentPlan.model_validate(
        {
            "id": "state_test",
            "name": "state test",
            "camera": {"fps": 4},
            "objects": [
                {"id": "hatch", "classes": ["hatch"], "states": ["open", "closed"]},
                {"id": "dewar", "classes": ["dewar"]},
                {"id": "sample", "classes": ["sample"]},
            ],
            "steps": steps,
        }
    )


def _chain(*evidence: dict) -> list[dict]:
    return [
        {
            "id": f"s{index}",
            "description": f"step {index}",
            "evidence": [rule],
            "next": [f"s{index + 1}"] if index + 1 < len(evidence) else [],
        }
        for index, rule in enumerate(evidence)
    ]


def _frame(*detections: Detection) -> PerceptionResult:
    return PerceptionResult(frame_id=0, ts_ms=0, width=200, height=200, detections=list(detections))


def test_detector_classes_expand_states() -> None:
    plan = _plan(_chain({"kind": "object_visible", "object": "sample"}))
    assert plan.detector_classes() == ["hatch__open", "hatch__closed", "dewar", "sample"]
    assert plan.class_states() == {"hatch": ["open", "closed"]}


def test_object_state_rule_requires_a_declared_state() -> None:
    with pytest.raises(ValidationError, match="not one of"):
        _plan(_chain({"kind": "object_state", "object": "hatch", "state": "ajar"}))


def test_inside_of_must_reference_a_known_object() -> None:
    with pytest.raises(ValidationError, match="inside_of"):
        _plan(_chain({"kind": "object_visible", "object": "sample", "inside_of": "nope"}))


def test_classes_and_states_reject_the_state_separator() -> None:
    with pytest.raises(ValidationError):
        ObjectSpec(id="bad", classes=["a__b"])
    with pytest.raises(ValidationError):
        ObjectSpec(id="bad", classes=["a"], states=["x__y"])


def _accumulator() -> EvidenceAccumulator:
    plan = _plan(_chain({"kind": "object_visible", "object": "sample"}))
    return EvidenceAccumulator(objects_by_id=plan.objects_dict)


def _step(rule: EvidenceRule) -> StepSpec:
    return StepSpec(id="check", description="check", evidence=[rule], next=[])


def test_object_state_matches_only_the_requested_state() -> None:
    accumulator = _accumulator()
    rule = EvidenceRule(kind="object_state", object="hatch", state="open")
    matched, verdicts = accumulator.evaluate_step(
        _step(rule), _frame(Detection("hatch__closed", 0.9, BBox(0, 0, 50, 50)))
    )
    assert not matched
    assert verdicts[0].reason == "object in another state"
    matched, verdicts = accumulator.evaluate_step(
        _step(rule), _frame(Detection("hatch__open", 0.8, BBox(0, 0, 50, 50)))
    )
    assert matched
    assert verdicts[0].conf == 0.8


def test_object_visible_matches_any_state_of_the_class() -> None:
    accumulator = _accumulator()
    rule = EvidenceRule(kind="object_visible", object="hatch")
    matched, _ = accumulator.evaluate_step(
        _step(rule), _frame(Detection("hatch__open", 0.7, BBox(0, 0, 50, 50)))
    )
    assert matched


def test_inside_of_requires_most_of_the_box_inside_the_container() -> None:
    accumulator = _accumulator()
    rule = EvidenceRule(kind="object_visible", object="sample", inside_of="dewar")
    container = Detection("dewar", 0.9, BBox(0, 0, 100, 100))
    mostly_inside = Detection("sample", 0.9, BBox(80, 10, 105, 40))
    mostly_outside = Detection("sample", 0.9, BBox(90, 10, 140, 40))
    matched, _ = accumulator.evaluate_step(_step(rule), _frame(container, mostly_inside))
    assert matched
    matched, _ = accumulator.evaluate_step(_step(rule), _frame(container, mostly_outside))
    assert not matched
    matched, _ = accumulator.evaluate_step(_step(rule), _frame(mostly_inside))
    assert not matched


def test_object_state_honours_inside_of() -> None:
    accumulator = _accumulator()
    rule = EvidenceRule(kind="object_state", object="hatch", state="closed", inside_of="dewar")
    hatch = Detection("hatch__closed", 0.9, BBox(10, 10, 90, 90))
    matched, _ = accumulator.evaluate_step(
        _step(rule), _frame(hatch, Detection("dewar", 0.9, BBox(0, 0, 100, 100)))
    )
    assert matched
    matched, _ = accumulator.evaluate_step(
        _step(rule), _frame(hatch, Detection("dewar", 0.9, BBox(120, 120, 200, 200)))
    )
    assert not matched


def test_overlapping_state_boxes_keep_only_the_more_confident_state() -> None:
    accumulator = _accumulator()
    open_rule = EvidenceRule(kind="object_state", object="hatch", state="open")
    closed_rule = EvidenceRule(kind="object_state", object="hatch", state="closed")
    frame = _frame(
        Detection("hatch__open", 0.75, BBox(0, 0, 50, 50)),
        Detection("hatch__closed", 0.3, BBox(2, 2, 50, 52)),
    )
    assert accumulator.evaluate_step(_step(open_rule), frame)[0]
    matched, verdicts = accumulator.evaluate_step(_step(closed_rule), frame)
    assert not matched
    assert verdicts[0].reason == "object in another state"


def test_step_completion_tolerates_one_dropped_frame_in_the_window() -> None:
    accumulator = _accumulator()
    rule = EvidenceRule(kind="object_state", object="hatch", state="open", min_frames=5)
    seen = _frame(Detection("hatch__open", 0.9, BBox(0, 0, 50, 50)))
    missed = _frame()
    pattern = [seen, seen, missed, seen, seen]
    outcomes = [accumulator.evaluate_step(_step(rule), frame)[0] for frame in pattern]
    assert outcomes == [False, False, False, False, True]


def test_step_completion_rejects_a_mostly_missing_window() -> None:
    accumulator = _accumulator()
    rule = EvidenceRule(kind="object_state", object="hatch", state="open", min_frames=5)
    seen = _frame(Detection("hatch__open", 0.9, BBox(0, 0, 50, 50)))
    missed = _frame()
    pattern = [seen, missed, seen, missed, seen]
    outcomes = [accumulator.evaluate_step(_step(rule), frame)[0] for frame in pattern]
    assert outcomes == [False, False, False, False, False]


def test_separate_objects_in_different_states_are_both_kept() -> None:
    accumulator = _accumulator()
    closed_rule = EvidenceRule(kind="object_state", object="hatch", state="closed")
    frame = _frame(
        Detection("hatch__open", 0.9, BBox(0, 0, 50, 50)),
        Detection("hatch__closed", 0.4, BBox(120, 120, 170, 170)),
    )
    assert accumulator.evaluate_step(_step(closed_rule), frame)[0]


def test_final_state_matching_the_start_does_not_count_as_a_skip() -> None:
    plan = _plan(
        _chain(
            {"kind": "object_state", "object": "hatch", "state": "open", "min_frames": 1},
            {"kind": "object_visible", "object": "sample", "min_frames": 1},
            {"kind": "object_state", "object": "hatch", "state": "closed", "min_frames": 1},
        )
    )
    engine = build_engine(plan)
    closed = Detection("hatch__closed", 0.9, BBox(0, 0, 50, 50))
    for _ in range(12):
        out = engine.step(_frame(closed))
    assert out.current_step_id == "s0"
    assert engine.skipped_step_ids == []
    engine.step(_frame(Detection("hatch__open", 0.9, BBox(0, 0, 50, 50))))
    assert engine.current_step.id == "s1"
    for _ in range(10):
        engine.step(_frame(closed))
    assert engine.skipped_step_ids == ["s1"]
    assert engine.state == EngineState.COMPLETED


def test_annotation_class_maps_states() -> None:
    states = {"hatch": ["open", "closed"]}
    assert annotation_class("hatch", "open", states) == "hatch__open"
    assert annotation_class("sample", None, states) == "sample"
    with pytest.raises(ValueError, match="needs a state"):
        annotation_class("hatch", None, states)
    with pytest.raises(ValueError, match="has no states"):
        annotation_class("sample", "open", states)


def _registry_with_take(tmp_path: Path) -> tuple[ActivityRegistry, str]:
    registry = ActivityRegistry(tmp_path / "activities")
    registry.create(
        ActivityManifest(id="state_test", name="State Test", kind=ActivityKind.EXPERIMENT)
    )
    save_activity_plan(
        registry,
        "state_test",
        _plan(_chain({"kind": "object_state", "object": "hatch", "state": "open"})),
    )
    source = tmp_path / "take.mp4"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (80, 60))
    for index in range(5):
        writer.write(np.full((60, 80, 3), index * 25, dtype=np.uint8))
    writer.release()
    take = register_take(registry, "state_test", source, source.name, "session-a")
    return registry, take.take_id


def _box(take_id: str, annotation_id: str, label: str, state: str | None = None) -> dict:
    payload = {
        "id": annotation_id,
        "take_id": take_id,
        "frame_id": 1,
        "time_s": 0.2,
        "kind": "object_box",
        "label": label,
        "bbox": {"x1": 5, "y1": 5, "x2": 30, "y2": 30},
    }
    if state is not None:
        payload["state"] = state
    return payload


def test_save_annotation_rejects_a_stateful_box_without_state(tmp_path: Path) -> None:
    registry, take_id = _registry_with_take(tmp_path)
    with pytest.raises(ValueError, match="needs a state"):
        save_annotation(registry, "state_test", _box(take_id, "box-a", "hatch"))
    saved = save_annotation(registry, "state_test", _box(take_id, "box-a", "hatch", "open"))
    assert saved.state == "open"


def test_delete_annotation_removes_only_that_box(tmp_path: Path) -> None:
    registry, take_id = _registry_with_take(tmp_path)
    save_annotation(registry, "state_test", _box(take_id, "box-a", "sample"))
    save_annotation(registry, "state_test", _box(take_id, "box-b", "dewar"))
    delete_annotation(registry, "state_test", "box-a")
    assert [item.annotation_id for item in list_annotations(registry, "state_test")] == ["box-b"]
    with pytest.raises(FileNotFoundError):
        delete_annotation(registry, "state_test", "box-a")
