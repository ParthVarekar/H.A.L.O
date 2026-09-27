"""Local video ingestion and take metadata persistence."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

from bas_har.schema.activity_schema import ActivityId, RecordId, TakeRecord
from bas_har.studio.registry import ActivityRegistry

VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def register_take(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    source: Path,
    original_filename: str,
    recording_session_id: RecordId | str,
    actor_id: str | None = None,
) -> TakeRecord:
    manifest = registry.load(activity_id)
    if not source.is_file():
        raise FileNotFoundError(f"uploaded take not found: {source}")
    suffix = Path(original_filename).suffix.lower()
    if suffix not in VIDEO_SUFFIXES:
        raise ValueError(f"unsupported video type: {suffix or 'none'}")
    digest = _sha256(source)
    records_path = registry.package_dir(manifest.activity_id) / "takes.jsonl"
    existing = list_takes(registry, manifest.activity_id)
    if any(record.source_sha256 == digest for record in existing):
        raise FileExistsError(f"take with the same content already exists: {original_filename}")
    metadata = _probe_video(source)
    stem = _safe_stem(Path(original_filename).stem)
    take_id = f"{stem}-{digest[:10]}"
    destination = registry.package_dir(manifest.activity_id) / "takes" / f"{take_id}{suffix}"
    shutil.move(str(source), str(destination))
    record = TakeRecord(
        id=take_id,
        filename=str(destination.relative_to(registry.package_dir(manifest.activity_id))),
        recording_session_id=recording_session_id,
        actor_id=actor_id,
        camera_profile=manifest.camera_profile,
        source_sha256=digest,
        **metadata,
    )
    with records_path.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json(by_alias=True) + "\n")
    return record


def list_takes(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
) -> list[TakeRecord]:
    manifest = registry.load(activity_id)
    records_path = registry.package_dir(manifest.activity_id) / "takes.jsonl"
    if not records_path.is_file():
        return []
    records: list[TakeRecord] = []
    for line in records_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(TakeRecord.model_validate(json.loads(line)))
    return records


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_stem(stem: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._-")
    return value[:96] or "take"


def _probe_video(path: Path) -> dict[str, float | int]:
    import cv2

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        raise ValueError(f"could not open uploaded video: {path.name}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    capture.release()
    if fps <= 0 or frames <= 0 or width <= 0 or height <= 0:
        raise ValueError(f"uploaded video has incomplete metadata: {path.name}")
    return {
        "duration_s": frames / fps,
        "fps": fps,
        "width": width,
        "height": height,
    }


__all__ = ["VIDEO_SUFFIXES", "list_takes", "register_take"]
