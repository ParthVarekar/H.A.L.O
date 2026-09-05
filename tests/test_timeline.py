"""Tests for timeline parsing and import."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from bas_har.schema.activity_schema import ActivityKind, ActivityManifest
from bas_har.studio.registry import ActivityRegistry
from bas_har.studio.takes import register_take
from bas_har.studio.timeline import import_timeline, parse_time, read_timeline


def _write_video(path: Path) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 8.0, (64, 48))
    for _ in range(8):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()


def _registry(tmp_path: Path) -> ActivityRegistry:
    registry = ActivityRegistry(tmp_path / "activities")
    registry.create(ActivityManifest(id="sample_handling", name="Sample Handling", kind=ActivityKind.EXPERIMENT))
    source = tmp_path / "take.mp4"
    _write_video(source)
    register_take(registry, "sample_handling", source, source.name, "session-1")
    return registry


def test_parse_time_accepts_seconds_and_clock_format() -> None:
    assert parse_time(1.25) == pytest.approx(1.25)
    assert parse_time("00:01:02.500") == pytest.approx(62.5)


def test_parse_time_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        parse_time("1:90")


def test_import_timeline_validates_duration_and_persists(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    take_id = next(iter(registry.list_activities()))
    take_record = __import__("bas_har.studio.takes", fromlist=["list_takes"]).list_takes(
        registry, take_id.activity_id
    )[0]
    source = tmp_path / "timeline.csv"
    source.write_text(
        "id,take_id,start_s,end_s,expected_step_id,observed_action,result,object_ids,region_ids,notes\n"
        f"event-1,{take_record.take_id},00:00:00.100,0.5,prepare,places sample,completed,sample,work_area,ok\n",
        encoding="utf-8",
    )

    records = import_timeline(registry, "sample_handling", source)

    assert records[0].start_s == pytest.approx(0.1)
    assert records[0].object_ids == ["sample"]


def test_read_timeline_rejects_missing_column(tmp_path: Path) -> None:
    source = tmp_path / "timeline.csv"
    source.write_text("id,take_id\nevent-1,take-1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns"):
        read_timeline(source)
