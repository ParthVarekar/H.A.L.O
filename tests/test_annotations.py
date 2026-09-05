"""Tests for browser-assisted keyframes and visual annotation storage."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from bas_har.schema.activity_schema import ActivityKind, ActivityManifest
from bas_har.studio.annotations import (
    list_annotations,
    list_keyframes,
    read_take_frame,
    save_annotation,
)
from bas_har.studio.registry import ActivityRegistry
from bas_har.studio.takes import register_take


def _video(path: Path, frames: int = 6) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 6.0, (80, 60))
    for index in range(frames):
        writer.write(np.full((60, 80, 3), index * 20, dtype=np.uint8))
    writer.release()


def test_keyframes_and_annotations_round_trip(tmp_path: Path) -> None:
    registry = ActivityRegistry(tmp_path / "activities")
    registry.create(
        ActivityManifest(id="sample_handling", name="Sample Handling", kind=ActivityKind.EXPERIMENT)
    )
    source = tmp_path / "take.mp4"
    _video(source)
    take = register_take(registry, "sample_handling", source, source.name, "session-a")

    keyframes = list_keyframes(registry, "sample_handling", take.take_id, every_frames=2, limit=3)
    frame = read_take_frame(
        registry, "sample_handling", take.take_id, int(keyframes[1]["frame_id"])
    )
    saved = save_annotation(
        registry,
        "sample_handling",
        {
            "id": "box-frame-2",
            "take_id": take.take_id,
            "frame_id": 2,
            "time_s": 2 / 6,
            "kind": "object_box",
            "label": "red_block",
            "bbox": {"x1": 5, "y1": 6, "x2": 30, "y2": 35},
        },
    )

    assert len(frame) > 100
    assert saved.label == "red_block"
    assert (
        list_annotations(registry, "sample_handling", take.take_id)[0].annotation_id
        == "box-frame-2"
    )
