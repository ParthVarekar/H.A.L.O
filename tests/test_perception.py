"""Tests for the perception layer.

These tests are pure-Python where possible (dataclass round-trip, HOI
heuristic). The actual model-load test is skipped if ultralytics/mediapipe
is not installed (e.g. a docs-only environment).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bas_har.perception.hoi import HandObjectInteractionTagger, bbox_within
from bas_har.perception.types import (
    BBox,
    Detection,
    HandKeypoints,
    PerceptionResult,
    PoseKeypoints,
)


def test_bbox_geometry() -> None:
    b = BBox(10, 20, 30, 60)
    assert b.width() == 20
    assert b.height() == 40
    assert b.area() == 800
    cx, cy = b.center()
    assert (cx, cy) == (20.0, 40.0)


def test_bbox_width_floored_at_zero() -> None:
    b = BBox(30, 20, 10, 60)
    assert b.width() == 0.0
    assert b.area() == 0.0


def test_perception_result_json_round_trip() -> None:
    r = PerceptionResult(
        frame_id=0,
        ts_ms=0,
        width=640,
        height=480,
        detections=[Detection(cls="box", conf=0.9, bbox=BBox(1, 2, 3, 4))],
    )
    s = r.to_json()
    parsed = json.loads(s)
    assert parsed["frame_id"] == 0
    assert parsed["detections"][0]["cls"] == "box"
    assert parsed["detections"][0]["bbox"]["x1"] == 1


def test_hoi_tagger_assigns_nearest_object() -> None:
    tagger = HandObjectInteractionTagger(proximity_px=100.0, grasping_speed_px=1.0)
    hand = HandKeypoints(
        handedness="right",
        score=0.9,
        keypoints=[(0, 0, 0)] * 21,
    )
    hand.keypoints[8] = (50.0, 50.0, 0.9)
    dets = [
        Detection(cls="box", conf=0.9, bbox=BBox(0, 0, 100, 100)),
        Detection(cls="bottle", conf=0.9, bbox=BBox(200, 200, 300, 300)),
    ]
    out = tagger.tag([hand], dets)
    assert len(out) == 1
    assert out[0].object_cls == "box"
    assert out[0].hand == "right"


def test_hoi_tagger_respects_proximity() -> None:
    tagger = HandObjectInteractionTagger(proximity_px=20.0, grasping_speed_px=1.0)
    hand = HandKeypoints(handedness="right", score=0.9, keypoints=[(0, 0, 0)] * 21)
    hand.keypoints[8] = (500.0, 500.0, 0.9)
    dets = [Detection(cls="box", conf=0.9, bbox=BBox(0, 0, 100, 100))]
    assert tagger.tag([hand], dets) == []


def test_hoi_tagger_grasping_vs_placing() -> None:
    tagger = HandObjectInteractionTagger(proximity_px=200.0, grasping_speed_px=5.0)
    dets = [Detection(cls="box", conf=0.9, bbox=BBox(0, 0, 100, 100))]

    stationary = HandKeypoints(handedness="right", score=0.9, keypoints=[(0, 0, 0)] * 21)
    stationary.keypoints[8] = (50.0, 50.0, 0.9)
    for _ in range(3):
        out = tagger.tag([stationary], dets)
    assert out and out[0].label == "grasping"

    moving = HandKeypoints(handedness="right", score=0.9, keypoints=[(0, 0, 0)] * 21)
    moving.keypoints[8] = (50.0, 50.0, 0.9)
    tagger.tag([moving], dets)
    moving.keypoints[8] = (90.0, 90.0, 0.9)
    tagger.tag([moving], dets)
    moving.keypoints[8] = (95.0, 95.0, 0.9)
    out = tagger.tag([moving], dets)
    assert out and out[0].label == "placing"


def test_bbox_within() -> None:
    b = BBox(0, 0, 100, 100)
    assert bbox_within(b, (50, 50))
    assert not bbox_within(b, (150, 50))


def test_pose_keypoints_by_name_unknown() -> None:
    kp = PoseKeypoints(keypoints=[(0, 0, 0)] * 33, score=0.5)
    with pytest.raises(KeyError):
        kp.by_name("does_not_exist")


@pytest.mark.skipif(
    not Path("models/yolo11n.pt").exists(),
    reason="models/yolo11n.pt not present (run smoke_perception.py once to download)",
)
def test_object_detector_loads() -> None:
    from bas_har.perception import ObjectDetector

    det = ObjectDetector(model_path="models/yolo11n.pt")
    names = det.class_names
    assert 0 in names
