"""Tests for background Training Studio jobs."""

from __future__ import annotations

import time
from pathlib import Path

from bas_har.schema.activity_schema import ActivityKind, ActivityManifest, JobStatus
from bas_har.studio.jobs import DatasetJobManager, TrainingJobManager
from bas_har.studio.registry import ActivityRegistry


def _registry(tmp_path: Path) -> ActivityRegistry:
    registry = ActivityRegistry(tmp_path)
    registry.create(
        ActivityManifest(id="sample_handling", name="Sample Handling", kind=ActivityKind.EXPERIMENT)
    )
    return registry


def _wait_for_status(
    manager: DatasetJobManager | TrainingJobManager,
    activity_id: str,
    expected: JobStatus,
) -> bool:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        jobs = manager.list(activity_id)
        if jobs and jobs[-1].status is expected:
            return True
        time.sleep(0.02)
    return False


def test_dataset_job_records_missing_video_failure(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    manager = DatasetJobManager(registry)
    manager.start("sample_handling")

    assert _wait_for_status(manager, "sample_handling", JobStatus.FAILED)
    restored = DatasetJobManager(registry)
    assert restored.list("sample_handling")[0].status is JobStatus.FAILED


def test_training_job_records_missing_dataset_failure(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    manager = TrainingJobManager(registry)
    manager.start("sample_handling", "dataset_v1")

    assert _wait_for_status(manager, "sample_handling", JobStatus.FAILED)
    restored = TrainingJobManager(registry)
    assert restored.list("sample_handling")[0].status is JobStatus.FAILED
