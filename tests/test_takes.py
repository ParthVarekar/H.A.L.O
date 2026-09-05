"""Tests for local take ingestion."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from bas_har.schema.activity_schema import ActivityKind, ActivityManifest
from bas_har.studio.registry import ActivityRegistry
from bas_har.studio.takes import list_takes, register_take


def _write_video(path: Path) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 8.0, (64, 48))
    for _ in range(4):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()


def _registry(tmp_path: Path) -> ActivityRegistry:
    registry = ActivityRegistry(tmp_path / "activities")
    registry.create(
        ActivityManifest(id="sample_handling", name="Sample Handling", kind=ActivityKind.EXPERIMENT)
    )
    return registry


def test_register_take_probes_and_persists_metadata(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    source = tmp_path / "take one.mp4"
    _write_video(source)

    record = register_take(registry, "sample_handling", source, source.name, "session-1")

    assert record.duration_s == pytest.approx(0.5)
    assert record.width == 64
    assert len(list_takes(registry, "sample_handling")) == 1
    assert (registry.package_dir("sample_handling") / record.filename).is_file()


def test_register_take_rejects_duplicate_content(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    source = tmp_path / "take.mp4"
    _write_video(source)
    register_take(registry, "sample_handling", source, source.name, "session-1")
    duplicate = tmp_path / "duplicate.mp4"
    _write_video(duplicate)

    with pytest.raises(FileExistsError):
        register_take(registry, "sample_handling", duplicate, duplicate.name, "session-2")
