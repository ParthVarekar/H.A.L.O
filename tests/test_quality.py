"""Tests for dataset quality reports."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from bas_har.schema.activity_schema import ActivityKind, ActivityManifest, DatasetVersion
from bas_har.schema.plan_schema import ExperimentPlan
from bas_har.studio.datasets import ensure_dataset_config
from bas_har.studio.plans import save_activity_plan
from bas_har.studio.quality import inspect_dataset, load_quality_report
from bas_har.studio.registry import ActivityRegistry


def _image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(path), np.zeros((40, 40, 3), dtype=np.uint8))


def _dataset(tmp_path: Path) -> tuple[ActivityRegistry, Path]:
    registry = ActivityRegistry(tmp_path / "activities")
    registry.create(
        ActivityManifest(id="sample_handling", name="Sample Handling", kind=ActivityKind.EXPERIMENT)
    )
    save_activity_plan(
        registry,
        "sample_handling",
        ExperimentPlan.model_validate(
            {
                "id": "sample_handling",
                "name": "Sample Handling",
                "objects": [{"id": "block", "classes": ["red_block", "blue_block"]}],
                "steps": [
                    {
                        "id": "observe",
                        "description": "Observe the block",
                        "evidence": [{"kind": "object_visible", "object": "block"}],
                    }
                ],
            }
        ),
    )
    data_path = ensure_dataset_config(registry, "sample_handling")
    dataset_dir = data_path.parent
    labels = {
        "train": "0 0.5 0.5 0.4 0.4\n",
        "val": "1 0.5 0.5 0.4 0.4\n",
        "test": "1 0.5 0.5 0.4 0.4\n",
    }
    for split, label in labels.items():
        image = dataset_dir / "images" / split / f"{split}-1.jpg"
        _image(image)
        label_path = dataset_dir / "labels" / split / f"{image.stem}.txt"
        label_path.parent.mkdir(parents=True, exist_ok=True)
        label_path.write_text(label, encoding="utf-8")
    metadata = DatasetVersion(
        id="dataset_v1",
        activity_id="sample_handling",
        take_ids=["take-1"],
        session_ids=["session-1"],
    )
    (dataset_dir / "dataset.json").write_text(
        metadata.model_dump_json(by_alias=True), encoding="utf-8"
    )
    return registry, dataset_dir


def test_quality_report_passes_and_persists(tmp_path: Path) -> None:
    registry, _dataset_dir = _dataset(tmp_path)

    report = inspect_dataset(registry, "sample_handling")
    restored = load_quality_report(registry, "sample_handling")

    assert report.passed
    assert report.images_by_split == {"train": 1, "val": 1, "test": 1}
    assert report.class_counts == {"red_block": 1, "blue_block": 2}
    assert restored.report_id == report.report_id


def test_quality_report_rejects_missing_labels(tmp_path: Path) -> None:
    registry, dataset_dir = _dataset(tmp_path)
    (dataset_dir / "labels" / "val" / "val-1.txt").unlink()

    report = inspect_dataset(registry, "sample_handling")

    assert not report.passed
    assert "val-1.jpg" in report.missing_label_files[0]
