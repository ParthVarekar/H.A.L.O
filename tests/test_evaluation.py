"""Tests for held-out evaluation metrics and job persistence."""

from __future__ import annotations

import time
from pathlib import Path

from halo.schema.activity_schema import ActivityKind, ActivityManifest, JobStatus
from halo.studio.evaluation import EvaluationJobManager, evaluate_boxes
from halo.studio.registry import ActivityRegistry


def test_evaluate_boxes_matches_class_and_iou() -> None:
    metrics = evaluate_boxes(
        [(0, 0.5, 0.5, 0.4, 0.4), (1, 0.2, 0.2, 0.2, 0.2)],
        [(0, 0.5, 0.5, 0.4, 0.4), (0, 0.2, 0.2, 0.2, 0.2)],
    )

    assert metrics["true_positive"] == 1
    assert metrics["false_positive"] == 1
    assert metrics["false_negative"] == 1
    assert metrics["f1"] == 0.5


def test_evaluation_job_records_missing_dataset_failure(tmp_path: Path) -> None:
    registry = ActivityRegistry(tmp_path)
    registry.create(
        ActivityManifest(id="sample_handling", name="Sample Handling", kind=ActivityKind.EXPERIMENT)
    )
    manager = EvaluationJobManager(registry)
    manager.start("sample_handling", "train-1", "missing.pt")
    deadline = time.monotonic() + 3

    while (
        time.monotonic() < deadline
        and manager.list("sample_handling")[0].status is not JobStatus.FAILED
    ):
        time.sleep(0.02)

    assert manager.list("sample_handling")[0].status is JobStatus.FAILED
    restored = EvaluationJobManager(registry)
    assert restored.list("sample_handling")[0].status is JobStatus.FAILED
