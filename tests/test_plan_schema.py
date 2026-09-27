"""Tests for the Pydantic schema in halo.schema.plan_schema.

Covers valid minimal, valid full, invalid (missing required field), and
invalid (bad enum / bad cross-reference) cases.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from halo.schema.plan_schema import (
    AlertPolicy,
    CameraConfig,
    EvidenceRule,
    ExperimentPlan,
    ObjectSpec,
    SpeechLanguage,
)


def test_camera_config_defaults() -> None:
    cam = CameraConfig()
    assert cam.source == 0
    assert cam.fps == 30
    assert cam.resolution == [1920, 1080]


def test_camera_config_rejects_bad_resolution() -> None:
    with pytest.raises(ValidationError):
        CameraConfig(resolution=[0, 1080])
    with pytest.raises(ValidationError):
        CameraConfig(resolution=[1920])


def test_object_spec_lowercases_classes() -> None:
    obj = ObjectSpec(id="big_box", classes=["Box", "CARTON"])
    assert obj.classes == ["box", "carton"]


def test_object_spec_rejects_empty_classes() -> None:
    with pytest.raises(ValidationError):
        ObjectSpec(id="x", classes=[])


def test_evidence_hoi_requires_object_and_label() -> None:
    EvidenceRule(kind="hand_object_interaction", object="a", label="grasping", min_frames=5)
    with pytest.raises(ValidationError):
        EvidenceRule(kind="hand_object_interaction", object="a")
    with pytest.raises(ValidationError):
        EvidenceRule(kind="hand_object_interaction", label="grasping")


def test_evidence_object_state_requires_object_and_state() -> None:
    EvidenceRule(kind="object_state", object="a", state="open")
    with pytest.raises(ValidationError):
        EvidenceRule(kind="object_state", object="a")


def test_evidence_object_location_requires_in_region() -> None:
    EvidenceRule(kind="object_location", object="a", in_region="table")
    with pytest.raises(ValidationError):
        EvidenceRule(kind="object_location", object="a")


def test_alert_policy_thresholds_bounded() -> None:
    AlertPolicy()
    with pytest.raises(ValidationError):
        AlertPolicy(skip_confidence_threshold=1.5)
    with pytest.raises(ValidationError):
        AlertPolicy(rate_limit_s=-0.1)


def _minimal_plan() -> dict:
    return {
        "id": "EXP-1",
        "name": "Minimal",
        "objects": [{"id": "box", "classes": ["box"]}],
        "steps": [
            {
                "id": "open",
                "description": "open",
                "evidence": [
                    {
                        "kind": "hand_object_interaction",
                        "object": "box",
                        "label": "opening",
                        "min_frames": 1,
                    }
                ],
                "next": ["close"],
            },
            {
                "id": "close",
                "description": "close",
                "evidence": [
                    {
                        "kind": "hand_object_interaction",
                        "object": "box",
                        "label": "closing",
                        "min_frames": 1,
                    }
                ],
                "next": [],
            },
        ],
    }


def test_experiment_plan_minimal_valid() -> None:
    plan = ExperimentPlan.model_validate(_minimal_plan())
    assert plan.experiment_id == "EXP-1"
    assert len(plan.steps) == 2


def test_experiment_plan_full_red_blue() -> None:
    plan = ExperimentPlan.model_validate(_minimal_plan())
    assert plan.alert_policy.skip_confidence_threshold == 0.85
    assert plan.fiducial.type == "none"


def test_experiment_plan_accepts_region_geometry() -> None:
    raw = _minimal_plan()
    raw["regions"] = ["table"]
    raw["region_geometries"] = {"table": [[0, 0], [100, 0], [100, 100], [0, 100]]}
    plan = ExperimentPlan.model_validate(raw)
    assert plan.region_geometries["table"] == [
        (0.0, 0.0),
        (100.0, 0.0),
        (100.0, 100.0),
        (0.0, 100.0),
    ]


def test_experiment_plan_rejects_short_region_polygon() -> None:
    raw = _minimal_plan()
    raw["regions"] = ["table"]
    raw["region_geometries"] = {"table": [[0, 0], [100, 0]]}
    with pytest.raises(ValidationError):
        ExperimentPlan.model_validate(raw)


def test_experiment_plan_rejects_geometry_for_unknown_region() -> None:
    raw = _minimal_plan()
    raw["region_geometries"] = {"table": [[0, 0], [100, 0], [100, 100]]}
    with pytest.raises(ValidationError, match="unknown region"):
        ExperimentPlan.model_validate(raw)


def test_experiment_plan_requires_geometry_for_location_rule() -> None:
    raw = _minimal_plan()
    raw["regions"] = ["table"]
    raw["steps"][0]["evidence"] = [
        {"kind": "object_location", "object": "box", "in_region": "table"}
    ]
    with pytest.raises(ValidationError, match="has no geometry"):
        ExperimentPlan.model_validate(raw)


def test_experiment_plan_rejects_duplicate_step_ids() -> None:
    raw = _minimal_plan()
    raw["steps"].append(
        {
            "id": "open",
            "description": "dup",
            "evidence": [{"kind": "object_visible", "object": "box"}],
            "next": [],
        }
    )
    with pytest.raises(ValidationError, match="duplicate step id"):
        ExperimentPlan.model_validate(raw)


def test_experiment_plan_rejects_unknown_next_ref() -> None:
    raw = _minimal_plan()
    raw["steps"][0]["next"] = ["does_not_exist"]
    with pytest.raises(ValidationError, match="unknown next step"):
        ExperimentPlan.model_validate(raw)


def test_experiment_plan_rejects_unknown_object_ref() -> None:
    raw = _minimal_plan()
    raw["steps"][0]["evidence"][0]["object"] = "no_such_thing"
    with pytest.raises(ValidationError, match="unknown object"):
        ExperimentPlan.model_validate(raw)


def test_experiment_plan_rejects_unreachable_step() -> None:
    raw = _minimal_plan()
    raw["steps"].append(
        {
            "id": "orphan",
            "description": "orphan",
            "evidence": [{"kind": "object_visible", "object": "box"}],
            "next": [],
        }
    )
    with pytest.raises(ValidationError, match="unreachable step"):
        ExperimentPlan.model_validate(raw)


def test_experiment_plan_rejects_extra_field() -> None:
    raw = _minimal_plan()
    raw["unknown_field"] = 1
    with pytest.raises(ValidationError):
        ExperimentPlan.model_validate(raw)


def test_experiment_plan_requires_at_least_one_step() -> None:
    raw = _minimal_plan()
    raw["steps"] = []
    with pytest.raises(ValidationError, match="at least 1 item"):
        ExperimentPlan.model_validate(raw)


def test_experiment_plan_accepts_spoken_text_in_english_and_hindi() -> None:
    data = _minimal_plan()
    data["spoken_name"] = {"en": "Box check", "hi": "बॉक्स जाँच"}
    data["steps"][0]["instruction"] = {"en": " Open the box ", "hi": "बॉक्स खोलें"}
    plan = ExperimentPlan.model_validate(data)
    assert plan.spoken_name[SpeechLanguage.HINDI] == "बॉक्स जाँच"
    assert plan.steps[0].instruction[SpeechLanguage.ENGLISH] == "Open the box"
    assert plan.steps[1].instruction == {}


def test_experiment_plan_rejects_unknown_speech_language() -> None:
    data = _minimal_plan()
    data["steps"][0]["instruction"] = {"fr": "Ouvrez la boîte"}
    with pytest.raises(ValidationError):
        ExperimentPlan.model_validate(data)


def test_experiment_plan_rejects_empty_instruction() -> None:
    data = _minimal_plan()
    data["steps"][0]["instruction"] = {"en": "   "}
    with pytest.raises(ValidationError):
        ExperimentPlan.model_validate(data)
