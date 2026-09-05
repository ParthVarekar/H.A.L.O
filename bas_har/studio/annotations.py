"""Keyframe access and local visual-annotation persistence."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import cv2

from bas_har.schema.activity_schema import ActivityId, RecordId, TakeRecord, VisualAnnotation
from bas_har.studio.registry import ActivityRegistry
from bas_har.studio.takes import list_takes

_WRITE_LOCK = threading.RLock()


def annotation_path(registry: ActivityRegistry, activity_id: ActivityId | str) -> Path:
    manifest = registry.load(activity_id)
    return registry.package_dir(manifest.activity_id) / "annotations.jsonl"


def list_annotations(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    take_id: RecordId | str | None = None,
) -> list[VisualAnnotation]:
    path = annotation_path(registry, activity_id)
    if not path.is_file():
        return []
    latest: dict[str, VisualAnnotation] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            annotation = VisualAnnotation.model_validate(json.loads(line))
            latest[annotation.annotation_id] = annotation
    annotations = list(latest.values())
    if take_id is not None:
        annotations = [annotation for annotation in annotations if annotation.take_id == take_id]
    return sorted(annotations, key=lambda annotation: (annotation.take_id, annotation.frame_id))


def save_annotation(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    payload: dict[str, Any],
) -> VisualAnnotation:
    manifest = registry.load(activity_id)
    annotation = VisualAnnotation.model_validate(payload)
    if not any(
        take.take_id == annotation.take_id for take in list_takes(registry, manifest.activity_id)
    ):
        raise ValueError(f"annotation references unknown take: {annotation.take_id}")
    take = _take(registry, manifest.activity_id, annotation.take_id)
    if take.width is not None and take.height is not None and annotation.bbox is not None:
        bbox = annotation.bbox
        if bbox.x2 > take.width or bbox.y2 > take.height:
            raise ValueError("annotation bounding box exceeds the take dimensions")
    path = annotation_path(registry, manifest.activity_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _WRITE_LOCK, path.open("a", encoding="utf-8") as handle:
        handle.write(annotation.model_dump_json(by_alias=True) + "\n")
    return annotation


def list_keyframes(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    take_id: RecordId | str,
    every_frames: int = 30,
    limit: int = 120,
) -> list[dict[str, int | float]]:
    if every_frames < 1:
        raise ValueError("every_frames must be at least 1")
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    take = _take(registry, activity_id, take_id)
    if take.fps is None or take.width is None or take.height is None:
        raise ValueError(f"take metadata is incomplete: {take.take_id}")
    frame_count = max(1, round(take.duration_s * take.fps)) if take.duration_s is not None else 1
    return [
        {
            "frame_id": frame_id,
            "time_s": round(frame_id / take.fps, 6),
            "width": take.width,
            "height": take.height,
        }
        for frame_id in range(0, frame_count, every_frames)[:limit]
    ]


def read_take_frame(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    take_id: RecordId | str,
    frame_id: int,
) -> bytes:
    if frame_id < 0:
        raise ValueError("frame_id must be non-negative")
    take = _take(registry, activity_id, take_id)
    video_path = registry.package_dir(activity_id) / take.filename
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        capture.release()
        raise ValueError(f"could not open take video: {take.filename}")
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ok, frame = capture.read()
    finally:
        capture.release()
    if not ok:
        raise ValueError(f"frame not found: {frame_id}")
    encoded, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not encoded:
        raise ValueError(f"could not encode frame: {frame_id}")
    return buffer.tobytes()


def _take(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    take_id: RecordId | str,
) -> TakeRecord:
    for take in list_takes(registry, activity_id):
        if take.take_id == take_id:
            return take
    raise FileNotFoundError(f"take not found: {take_id}")


__all__ = [
    "annotation_path",
    "list_annotations",
    "list_keyframes",
    "read_take_frame",
    "save_annotation",
]
