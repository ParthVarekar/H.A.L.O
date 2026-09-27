"""Extract sampled video frames into a trainable Ultralytics YOLO dataset."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, TypeVar

import cv2
import yaml

from halo.config import datasets_dir
from halo.perception import ColorBlockDetector

VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
SplitItem = TypeVar("SplitItem")


def discover_videos(source: Path) -> list[Path]:
    if source.is_file():
        if source.suffix.lower() not in VIDEO_SUFFIXES:
            raise ValueError(f"unsupported video type: {source.suffix}")
        return [source]
    if not source.is_dir():
        raise FileNotFoundError(f"video source not found: {source}")
    videos = sorted(
        path
        for path in source.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
    )
    if not videos:
        raise FileNotFoundError(f"no videos found under: {source}")
    return videos


def split_videos(
    videos: list[Path], val_ratio: float, test_ratio: float, seed: int
) -> dict[Path, str]:
    return _assign_splits(videos, val_ratio, test_ratio, seed)


def split_grouped_videos(
    videos: list[Path],
    group_by: dict[Path, str],
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> dict[Path, str]:
    if any(video not in group_by for video in videos):
        raise ValueError("every video must have a recording-session group")
    groups = sorted(set(group_by.values()))
    group_splits = _assign_splits(groups, val_ratio, test_ratio, seed)
    return {video: group_splits[group_by[video]] for video in videos}


def _assign_splits(
    items: list[SplitItem], val_ratio: float, test_ratio: float, seed: int
) -> dict[SplitItem, str]:
    if not 0 <= val_ratio < 1 or not 0 <= test_ratio < 1:
        raise ValueError("split ratios must be between 0 and 1")
    if val_ratio + test_ratio >= 1:
        raise ValueError("val_ratio + test_ratio must be less than 1")
    ordered = sorted(items)
    if len(ordered) < 3:
        return {video: "train" for video in ordered}
    shuffled = list(ordered)
    random.Random(seed).shuffle(shuffled)
    test_count = max(1, round(len(shuffled) * test_ratio)) if test_ratio else 0
    val_count = max(1, round(len(shuffled) * val_ratio)) if val_ratio else 0
    while test_count + val_count >= len(shuffled):
        if test_count >= val_count and test_count:
            test_count -= 1
        elif val_count:
            val_count -= 1
        else:
            break
    assignments: dict[Path, str] = {}
    for video in shuffled[: len(shuffled) - test_count - val_count]:
        assignments[video] = "train"
    for video in shuffled[len(shuffled) - test_count - val_count : len(shuffled) - test_count]:
        assignments[video] = "val"
    if test_count:
        for video in shuffled[len(shuffled) - test_count :]:
            assignments[video] = "test"
    return assignments


def load_class_names(data_path: Path) -> dict[int, str]:
    if not data_path.is_file():
        raise FileNotFoundError(f"dataset YAML not found: {data_path}")
    data = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    names: Any = data.get("names")
    if isinstance(names, list):
        return {index: str(name) for index, name in enumerate(names)}
    if isinstance(names, dict):
        return {int(index): str(name) for index, name in names.items()}
    raise ValueError("dataset YAML must contain names as a list or mapping")


def _color_class_ids(class_names: dict[int, str]) -> dict[str, int]:
    color_ids: dict[str, int] = {}
    for class_id, name in class_names.items():
        lowered = name.lower()
        for color in ("red", "blue"):
            if color in lowered:
                color_ids[color] = class_id
    return color_ids


def _write_yolo_labels(
    label_path: Path, detections: list[Any], color_ids: dict[str, int], width: int, height: int
) -> int:
    rows: list[str] = []
    for detection in detections:
        if detection.color not in color_ids:
            continue
        bbox = detection.bbox
        center_x, center_y = bbox.center()
        values = (
            color_ids[detection.color],
            center_x / width,
            center_y / height,
            bbox.width() / width,
            bbox.height() / height,
        )
        rows.append(f"{values[0]} {values[1]:.6f} {values[2]:.6f} {values[3]:.6f} {values[4]:.6f}")
    label_path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return len(rows)


def _image_name(video_index: int, video: Path, frame_id: int) -> str:
    stem = "".join(char if char.isalnum() or char in "-_" else "_" for char in video.stem)
    return f"v{video_index:03d}_{stem}_f{frame_id:06d}.jpg"


def prepare(
    source: Path,
    dataset: Path,
    sample_every: int,
    val_ratio: float,
    test_ratio: float,
    seed: int,
    auto_color: bool,
    min_color_area: float,
    max_frames_per_video: int | None,
    split_groups: dict[Path, str] | None = None,
) -> int:
    if sample_every < 1:
        raise ValueError("sample_every must be at least 1")
    videos = discover_videos(source)
    data_path = dataset / "data.yaml"
    class_names = load_class_names(data_path)
    color_ids = _color_class_ids(class_names)
    assignments = (
        split_grouped_videos(videos, split_groups, val_ratio, test_ratio, seed)
        if split_groups is not None
        else split_videos(videos, val_ratio, test_ratio, seed)
    )
    detector = ColorBlockDetector(color_ids, min_area=min_color_area) if auto_color else None
    manifest: list[dict[str, Any]] = []
    totals = {"train": 0, "val": 0, "test": 0}
    labeled = 0
    for split in totals:
        (dataset / "images" / split).mkdir(parents=True, exist_ok=True)
        (dataset / "labels" / split).mkdir(parents=True, exist_ok=True)
    for video_index, video in enumerate(videos, start=1):
        split = assignments[video]
        capture = cv2.VideoCapture(str(video))
        if not capture.isOpened():
            raise RuntimeError(f"could not open video: {video}")
        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        frame_id = 0
        extracted = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_id % sample_every == 0:
                    filename = _image_name(video_index, video, frame_id)
                    image_path = dataset / "images" / split / filename
                    label_path = dataset / "labels" / split / f"{image_path.stem}.txt"
                    if not image_path.is_file() and not cv2.imwrite(str(image_path), frame):
                        raise RuntimeError(f"could not write frame: {image_path}")
                    if not label_path.is_file():
                        detections = detector.detect(frame) if detector is not None else []
                        labeled += _write_yolo_labels(
                            label_path, detections, color_ids, frame.shape[1], frame.shape[0]
                        )
                    manifest.append(
                        {
                            "image": str(image_path.relative_to(dataset)),
                            "label": str(label_path.relative_to(dataset)),
                            "source": str(video),
                            "split": split,
                            "frame_id": frame_id,
                            "video_time_s": round(frame_id / fps, 6),
                            "fps": fps,
                        }
                    )
                    extracted += 1
                    if max_frames_per_video is not None and extracted >= max_frames_per_video:
                        break
                frame_id += 1
        finally:
            capture.release()
        totals[split] += extracted
        print(f"{split:5s} {video.name}: {extracted} frames")
    manifest_path = dataset / "manifests" / "frames.jsonl"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest), encoding="utf-8"
    )
    print(f"dataset={dataset}")
    print(f"videos={len(videos)} train={totals['train']} val={totals['val']} test={totals['test']}")
    print(f"auto_labels={labeled} classes={class_names}")
    if len(videos) < 3:
        print("warning=video-level validation splits require at least 3 source videos")
    if auto_color and color_ids:
        print("next=run annotate-yolo to add big_box labels and correct auto-colored boxes")
    return 0


def build_parser() -> argparse.ArgumentParser:
    default_dataset = datasets_dir() / "red_blue_box"
    parser = argparse.ArgumentParser(prog="prepare-yolo-dataset", description=__doc__)
    parser.add_argument(
        "source",
        type=Path,
        nargs="?",
        default=default_dataset / "raw" / "videos",
        help="Video file or folder of videos.",
    )
    parser.add_argument("--dataset", type=Path, default=default_dataset)
    parser.add_argument("--sample-every", type=int, default=5)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=26174)
    parser.add_argument("--min-color-area", type=float, default=400.0)
    parser.add_argument("--max-frames-per-video", type=int, default=None)
    parser.add_argument("--auto-color", action=argparse.BooleanOptionalAction, default=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return prepare(
        args.source,
        args.dataset,
        args.sample_every,
        args.val_ratio,
        args.test_ratio,
        args.seed,
        args.auto_color,
        args.min_color_area,
        args.max_frames_per_video,
    )


if __name__ == "__main__":
    raise SystemExit(main())
