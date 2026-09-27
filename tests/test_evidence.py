"""Tests for generic evidence evaluation."""

from __future__ import annotations

import pytest

from halo.perception.types import BBox, Detection, PerceptionResult
from halo.procedure.evidence import EvidenceAccumulator, perception_needs
from halo.schema.plan_schema import EvidenceRule, ExperimentPlan, ObjectSpec, StepSpec


def _result(*detections: Detection) -> PerceptionResult:
    return PerceptionResult(
        frame_id=0,
        ts_ms=0,
        width=640,
        height=480,
        detections=list(detections),
    )


def _step(rule: EvidenceRule) -> StepSpec:
    return StepSpec(id="place", description="place object", evidence=[rule], next=[])


def test_object_location_requires_all_bbox_corners_inside_region() -> None:
    accumulator = EvidenceAccumulator(
        objects_by_id={"box": ObjectSpec(id="box", classes=["box"])},
        regions={"table"},
        region_geometries={"table": [(0, 0), (100, 0), (100, 100), (0, 100)]},
    )
    rule = EvidenceRule(kind="object_location", object="box", in_region="table")

    matched, verdicts = accumulator.evaluate_step(
        _step(rule), _result(Detection("box", 0.9, BBox(20, 20, 80, 80)))
    )

    assert matched
    assert verdicts[0].conf == 0.9
    assert verdicts[0].reason == "ok"


def test_object_location_rejects_partially_outside_bbox() -> None:
    accumulator = EvidenceAccumulator(
        objects_by_id={"box": ObjectSpec(id="box", classes=["box"])},
        regions={"table"},
        region_geometries={"table": [(0, 0), (100, 0), (100, 100), (0, 100)]},
    )
    rule = EvidenceRule(kind="object_location", object="box", in_region="table")

    matched, verdicts = accumulator.evaluate_step(
        _step(rule), _result(Detection("box", 0.9, BBox(80, 20, 120, 60)))
    )

    assert not matched
    assert verdicts[0].reason == "object not visible"


def test_object_visible_outside_of_rejects_contained_detection() -> None:
    accumulator = EvidenceAccumulator(
        objects_by_id={
            "big_box": ObjectSpec(id="big_box", classes=["big_box"]),
            "small_box": ObjectSpec(id="small_box", classes=["small_box"]),
        }
    )
    rule = EvidenceRule(kind="object_visible", object="small_box", outside_of="big_box")
    container = Detection("big_box", 0.8, BBox(0, 0, 100, 100))
    contained = Detection("small_box", 0.9, BBox(20, 20, 80, 80))
    outside = Detection("small_box", 0.7, BBox(120, 20, 180, 80))

    contained_match, _ = accumulator.evaluate_step(_step(rule), _result(container, contained))
    accumulator.reset()
    outside_match, verdicts = accumulator.evaluate_step(_step(rule), _result(container, outside))

    assert not contained_match
    assert outside_match
    assert verdicts[0].conf == 0.7


def _plan_with_rules(*rules: dict) -> ExperimentPlan:
    return ExperimentPlan.model_validate(
        {
            "id": "needs",
            "name": "needs",
            "objects": [{"id": "box", "classes": ["box"]}],
            "steps": [{"id": "step_0", "description": "step", "evidence": list(rules)}],
        }
    )


@pytest.mark.parametrize(
    ("rules", "expected"),
    [
        ([{"kind": "object_visible", "object": "box"}], (False, False)),
        ([{"kind": "actor_visible"}, {"kind": "object_visible", "object": "box"}], (True, False)),
        (
            [{"kind": "hand_object_interaction", "object": "box", "label": "grasping"}],
            (False, True),
        ),
    ],
)
def test_perception_needs_follow_plan_evidence_kinds(
    rules: list[dict], expected: tuple[bool, bool]
) -> None:
    assert perception_needs(_plan_with_rules(*rules)) == expected
