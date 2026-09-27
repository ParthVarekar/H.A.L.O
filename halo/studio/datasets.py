"""Dataset configuration and preparation for local activity packages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from halo.schema.activity_schema import ActivityId, AnnotationKind, DatasetVersion
from halo.schema.plan_schema import state_class
from halo.studio.annotations import list_annotations
from halo.studio.registry import ActivityRegistry
from halo.studio.takes import list_takes


def activity_dataset_dir(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
) -> Path:
    manifest = registry.load(activity_id)
    return registry.package_dir(manifest.activity_id) / "datasets" / "dataset_v1"


def ensure_dataset_config(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
) -> Path:
    manifest = registry.load(activity_id)
    plan_path = registry.package_dir(manifest.activity_id) / manifest.plan_path
    if not plan_path.is_file():
        raise FileNotFoundError(f"activity plan not found: {plan_path}")
    from halo.studio.plans import load_activity_plan

    plan = load_activity_plan(registry, manifest.activity_id)
    class_names = plan.detector_classes()
    if not class_names:
        raise ValueError("activity plan must define at least one detector class")
    dataset_dir = activity_dataset_dir(registry, manifest.activity_id)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    data_path = dataset_dir / "data.yaml"
    expected = {index: name for index, name in enumerate(class_names)}
    if not data_path.is_file() or _class_names(data_path) != {
        name: index for index, name in expected.items()
    }:
        payload = {
            "path": ".",
            "train": "images/train",
            "val": "images/val",
            "test": "images/test",
            "names": expected,
        }
        data_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return data_path


def prepare_activity_dataset(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    sample_every: int = 5,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    seed: int = 26174,
) -> DatasetVersion:
    manifest = registry.load(activity_id)
    takes = list_takes(registry, manifest.activity_id)
    if not takes:
        raise ValueError("upload at least one training video before preparing a dataset")
    data_path = ensure_dataset_config(registry, manifest.activity_id)
    from scripts.prepare_dataset import prepare

    dataset_dir = data_path.parent
    split_groups = {
        registry.package_dir(manifest.activity_id) / take.filename: take.recording_session_id
        for take in takes
    }
    prepare(
        registry.package_dir(manifest.activity_id) / "takes",
        dataset_dir,
        sample_every,
        val_ratio,
        test_ratio,
        seed,
        True,
        400.0,
        None,
        split_groups,
    )
    _apply_visual_annotations(registry, manifest.activity_id, dataset_dir)
    split_sessions = _split_sessions(registry, manifest.activity_id, dataset_dir)
    dataset = DatasetVersion(
        id="dataset_v1",
        activity_id=manifest.activity_id,
        take_ids=[take.take_id for take in takes],
        session_ids=sorted({take.recording_session_id for take in takes}),
        train_ratio=1.0 - val_ratio - test_ratio,
        validation_ratio=val_ratio,
        test_ratio=test_ratio,
        split_sessions=split_sessions,
    )
    metadata_path = dataset_dir / "dataset.json"
    metadata_path.write_text(dataset.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
    return dataset


def _split_sessions(
    registry: ActivityRegistry,
    activity_id: ActivityId,
    dataset_dir: Path,
) -> dict[str, list[str]]:
    manifest_path = dataset_dir / "manifests" / "frames.jsonl"
    rows = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    takes = list_takes(registry, activity_id)
    paths = {
        (registry.package_dir(activity_id) / take.filename).resolve(): take.recording_session_id
        for take in takes
    }
    sessions: dict[str, set[str]] = {split: set() for split in ("train", "val", "test")}
    for row in rows:
        session_id = paths.get(Path(row["source"]).resolve())
        if session_id is not None and row["split"] in sessions:
            sessions[row["split"]].add(session_id)
    return {split: sorted(values) for split, values in sessions.items()}


def _apply_visual_annotations(
    registry: ActivityRegistry,
    activity_id: ActivityId,
    dataset_dir: Path,
) -> None:
    annotations = [
        annotation
        for annotation in list_annotations(registry, activity_id)
        if annotation.kind is AnnotationKind.OBJECT_BOX
    ]
    if not annotations:
        return
    manifest = registry.load(activity_id)
    from halo.studio.plans import load_activity_plan

    class_states = load_activity_plan(registry, manifest.activity_id).class_states()
    takes = {take.take_id: take for take in list_takes(registry, activity_id)}
    data_path = dataset_dir / "data.yaml"
    class_names = _class_names(data_path)
    frame_manifest_path = dataset_dir / "manifests" / "frames.jsonl"
    rows = [
        json.loads(line)
        for line in frame_manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    grouped: dict[tuple[str, int], list[Any]] = {}
    for annotation in annotations:
        grouped.setdefault((annotation.take_id, annotation.frame_id), []).append(annotation)
    for (take_id, frame_id), frame_annotations in grouped.items():
        take = takes.get(take_id)
        if take is None or take.width is None or take.height is None:
            raise ValueError(f"annotation references take with incomplete metadata: {take_id}")
        for annotation in frame_annotations:
            key = annotation_class(annotation.label, annotation.state, class_states)
            if key not in class_names:
                raise ValueError(f"annotation label is not in the activity classes: {key}")
        source = registry.package_dir(manifest.activity_id) / take.filename
        row = _find_frame_row(rows, source, frame_id)
        if row is None:
            split = _source_split(rows, source)
            image_path, row = _extract_manual_frame(
                dataset_dir, source, split, take_id, frame_id, take.fps
            )
            rows.append(row)
        else:
            image_path = dataset_dir / row["image"]
        label_path = dataset_dir / row["label"]
        label_path.parent.mkdir(parents=True, exist_ok=True)
        label_path.write_text(
            "".join(
                _yolo_row(
                    annotation,
                    class_names[annotation_class(annotation.label, annotation.state, class_states)],
                    take.width,
                    take.height,
                )
                for annotation in frame_annotations
            ),
            encoding="utf-8",
        )
        if not image_path.is_file():
            raise FileNotFoundError(f"annotation image not found: {image_path}")
    frame_manifest_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )


def _class_names(data_path: Path) -> dict[str, int]:
    data = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    names = data.get("names")
    if isinstance(names, list):
        return {str(name): index for index, name in enumerate(names)}
    if isinstance(names, dict):
        return {str(name): int(index) for index, name in names.items()}
    raise ValueError("dataset YAML must contain names as a list or mapping")


def _find_frame_row(
    rows: list[dict[str, Any]], source: Path, frame_id: int
) -> dict[str, Any] | None:
    target = source.resolve()
    for row in rows:
        if int(row.get("frame_id", -1)) != frame_id:
            continue
        if Path(row["source"]).resolve() == target:
            return row
    return None


def _source_split(rows: list[dict[str, Any]], source: Path) -> str:
    target = source.resolve()
    for row in rows:
        if Path(row["source"]).resolve() == target:
            return str(row["split"])
    return "train"


def _extract_manual_frame(
    dataset_dir: Path,
    source: Path,
    split: str,
    take_id: str,
    frame_id: int,
    fps: float | None,
) -> tuple[Path, dict[str, Any]]:
    import cv2

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        capture.release()
        raise ValueError(f"could not open annotated take: {source}")
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ok, frame = capture.read()
    finally:
        capture.release()
    if not ok:
        raise ValueError(f"annotated frame not found: {frame_id}")
    filename = f"manual_{take_id}_f{frame_id:06d}.jpg"
    image_path = dataset_dir / "images" / split / filename
    image_path.parent.mkdir(parents=True, exist_ok=True)
    if not image_path.is_file() and not cv2.imwrite(str(image_path), frame):
        raise RuntimeError(f"could not write annotated frame: {image_path}")
    fps_value = fps or 30.0
    return image_path, {
        "image": str(image_path.relative_to(dataset_dir)),
        "label": str(
            (dataset_dir / "labels" / split / f"{image_path.stem}.txt").relative_to(dataset_dir)
        ),
        "source": str(source),
        "split": split,
        "frame_id": frame_id,
        "video_time_s": round(frame_id / fps_value, 6),
        "fps": fps_value,
    }


def annotation_class(label: str, state: str | None, class_states: dict[str, list[str]]) -> str:
    states = class_states.get(label)
    if not states:
        if state:
            raise ValueError(f"class {label!r} has no states but a box is tagged {state!r}")
        return label
    if state not in states:
        raise ValueError(f"box of class {label!r} needs a state from {states}, got {state!r}")
    return state_class(label, state)


def _yolo_row(annotation: Any, class_index: int, width: int, height: int) -> str:
    bbox = annotation.bbox
    if bbox is None:
        raise ValueError("object_box annotation is missing a bounding box")
    center_x = (bbox.x1 + bbox.x2) / 2 / width
    center_y = (bbox.y1 + bbox.y2) / 2 / height
    box_width = (bbox.x2 - bbox.x1) / width
    box_height = (bbox.y2 - bbox.y1) / height
    return f"{class_index} {center_x:.6f} {center_y:.6f} {box_width:.6f} {box_height:.6f}\n"


def load_dataset_version(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
) -> DatasetVersion:
    path = activity_dataset_dir(registry, activity_id) / "dataset.json"
    if not path.is_file():
        raise FileNotFoundError(f"dataset metadata not found: {path}")
    return DatasetVersion.model_validate_json(path.read_text(encoding="utf-8"))


__all__ = [
    "activity_dataset_dir",
    "annotation_class",
    "ensure_dataset_config",
    "load_dataset_version",
    "prepare_activity_dataset",
]
