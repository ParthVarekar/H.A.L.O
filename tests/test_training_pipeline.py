"""Tests for the video-to-YOLO training workflow."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from scripts.prepare_dataset import build_parser, prepare, split_grouped_videos, split_videos


def _write_video(path: Path, frames: int = 4) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 8.0, (128, 96))
    for _ in range(frames):
        image = np.zeros((96, 128, 3), dtype=np.uint8)
        cv2.rectangle(image, (10, 20), (55, 75), (0, 0, 255), -1)
        cv2.rectangle(image, (72, 20), (117, 75), (255, 0, 0), -1)
        writer.write(image)
    writer.release()


def test_prepare_parser_defaults() -> None:
    args = build_parser().parse_args([])

    assert args.sample_every == 5
    assert args.auto_color


def test_split_videos_keeps_small_sources_in_train() -> None:
    videos = [Path("one.mp4"), Path("two.mp4")]

    assert set(split_videos(videos, 0.2, 0.1, 26174).values()) == {"train"}


def test_grouped_split_keeps_recording_sessions_together() -> None:
    videos = [Path("one_a.mp4"), Path("one_b.mp4"), Path("two_a.mp4"), Path("three.mp4")]
    groups = {
        videos[0]: "session-one",
        videos[1]: "session-one",
        videos[2]: "session-two",
        videos[3]: "session-three",
    }

    assignments = split_grouped_videos(videos, groups, 0.2, 0.1, 26174)

    assert assignments[videos[0]] == assignments[videos[1]]


def test_prepare_extracts_frames_and_auto_labels(tmp_path: Path) -> None:
    source = tmp_path / "videos"
    dataset = tmp_path / "dataset"
    source.mkdir()
    dataset.mkdir()
    for name in ("take_a.mp4", "take_b.mp4", "take_c.mp4"):
        _write_video(source / name)
    (dataset / "data.yaml").write_text(
        "path: .\ntrain: images/train\nval: images/val\ntest: images/test\n"
        "names:\n  0: big_box\n  1: small_red_box\n  2: small_blue_box\n",
        encoding="utf-8",
    )

    result = prepare(source, dataset, 1, 0.2, 0.1, 26174, True, 100, None)

    assert result == 0
    assert len(list((dataset / "images" / "train").glob("*.jpg"))) == 4
    assert len(list((dataset / "images" / "val").glob("*.jpg"))) == 4
    assert len(list((dataset / "images" / "test").glob("*.jpg"))) == 4
    label_files = list((dataset / "labels").rglob("*.txt"))
    assert label_files
    assert all(len(path.read_text(encoding="utf-8").splitlines()) == 2 for path in label_files)
    assert (
        len((dataset / "manifests" / "frames.jsonl").read_text(encoding="utf-8").splitlines()) == 12
    )
