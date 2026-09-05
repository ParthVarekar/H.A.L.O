"""Tests for activity dataset setup."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from bas_har.schema.activity_schema import ActivityKind, ActivityManifest
from bas_har.schema.plan_schema import ExperimentPlan
from bas_har.studio.annotations import save_annotation
from bas_har.studio.datasets import ensure_dataset_config, prepare_activity_dataset
from bas_har.studio.plans import save_activity_plan
from bas_har.studio.registry import ActivityRegistry
from bas_har.studio.takes import register_take


def test_ensure_dataset_config_uses_plan_classes(tmp_path: Path) -> None:
    registry = ActivityRegistry(tmp_path)
    registry.create(
        ActivityManifest(id="sample_handling", name="Sample Handling", kind=ActivityKind.EXPERIMENT)
    )
    plan = ExperimentPlan(
        id="sample_handling",
        name="Sample Handling",
        objects=[{"id": "sample", "classes": ["sample_container"]}],
        steps=[
            {
                "id": "observe",
                "description": "Observe the sample",
                "evidence": [{"kind": "object_visible", "object": "sample"}],
            }
        ],
    )
    save_activity_plan(registry, "sample_handling", plan)

    data_path = ensure_dataset_config(registry, "sample_handling")

    assert data_path.is_file()
    assert "sample_container" in data_path.read_text(encoding="utf-8")


def test_ensure_dataset_config_requires_plan_objects(tmp_path: Path) -> None:
    registry = ActivityRegistry(tmp_path)
    registry.create(ActivityManifest(id="exercise", name="Exercise", kind=ActivityKind.EXERCISE))
    plan = ExperimentPlan(
        id="exercise",
        name="Exercise",
        steps=[
            {
                "id": "visible",
                "description": "The astronaut is visible",
                "evidence": [{"kind": "actor_visible"}],
            }
        ],
    )
    save_activity_plan(registry, "exercise", plan)

    with pytest.raises(ValueError, match="detector class"):
        ensure_dataset_config(registry, "exercise")


def test_manual_annotation_is_added_to_prepared_dataset(tmp_path: Path) -> None:
    registry = ActivityRegistry(tmp_path / "activities")
    registry.create(
        ActivityManifest(id="sample_handling", name="Sample Handling", kind=ActivityKind.EXPERIMENT)
    )
    save_activity_plan(
        registry,
        "sample_handling",
        ExperimentPlan(
            id="sample_handling",
            name="Sample Handling",
            objects=[{"id": "block", "classes": ["red_block"]}],
            steps=[
                {
                    "id": "observe",
                    "description": "Observe the block",
                    "evidence": [{"kind": "object_visible", "object": "block"}],
                }
            ],
        ),
    )
    source = tmp_path / "take.mp4"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (80, 60))
    for index in range(3):
        writer.write(np.full((60, 80, 3), index * 20, dtype=np.uint8))
    writer.release()
    take = register_take(registry, "sample_handling", source, source.name, "session-a")
    save_annotation(
        registry,
        "sample_handling",
        {
            "id": "manual-frame-1",
            "take_id": take.take_id,
            "frame_id": 1,
            "time_s": 0.2,
            "kind": "object_box",
            "label": "red_block",
            "bbox": {"x1": 8, "y1": 6, "x2": 32, "y2": 30},
        },
    )

    dataset = prepare_activity_dataset(registry, "sample_handling", sample_every=5)

    dataset_dir = registry.package_dir("sample_handling") / "datasets" / dataset.dataset_id
    manual_label = next((dataset_dir / "labels" / "train").glob("manual_*.txt"))
    assert manual_label.read_text(encoding="utf-8").startswith("0 0.250000 0.300000")
    assert dataset.split_sessions == {"train": ["session-a"], "val": [], "test": []}
