from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from halo.perception.color_blocks import ColorBlockDetector
from halo.perception.types import BBox, Detection, PerceptionResult
from halo.procedure.sequence import ColorSequenceTracker
from halo.schema.cli import load_plan


def _result(frame_id: int, *detections: Detection) -> PerceptionResult:
    return PerceptionResult(
        frame_id=frame_id,
        ts_ms=frame_id * 1000 // 24,
        width=1280,
        height=720,
        detections=list(detections),
    )


def _detection(color: str, inside: bool) -> Detection:
    bbox = BBox(450, 380, 600, 470) if inside else BBox(150, 120, 300, 270)
    if color == "blue":
        bbox = BBox(650, 380, 800, 470) if inside else BBox(900, 120, 1050, 270)
    return Detection(cls="box", conf=0.9, bbox=bbox, color=color)


def test_color_block_detector_finds_red_and_blue() -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.rectangle(frame, (450, 380), (600, 470), (0, 0, 255), -1)
    cv2.rectangle(frame, (650, 380), (800, 470), (255, 0, 0), -1)

    detections = ColorBlockDetector(["red", "blue"]).detect(frame)

    assert {detection.color for detection in detections} == {"red", "blue"}
    assert all(detection.cls == "box" for detection in detections)


def test_color_sequence_tracker_logs_the_observed_order() -> None:
    plan = load_plan(Path("experiments/red_blue_box/experiment_plan.yaml"))
    tracker = ColorSequenceTracker(plan, stable_frames=2)
    frame_id = 0

    def feed(*detections: Detection) -> list[str]:
        nonlocal frame_id
        events: list[str] = []
        for _ in range(2):
            observation = tracker.update(_result(frame_id, *detections))
            events.extend(event.step_id for event in observation.events)
            frame_id += 1
        return events

    event_ids = feed(_detection("red", True), _detection("blue", True))
    event_ids += feed(_detection("red", False), _detection("blue", True))
    event_ids += feed(_detection("red", True), _detection("blue", True))
    event_ids += feed(_detection("red", True), _detection("blue", False))
    event_ids += feed(_detection("red", True), _detection("blue", True))
    event_ids += feed()

    assert event_ids == [
        "open_big_box",
        "remove_red_box",
        "place_red_box",
        "remove_blue_box",
        "place_blue_box",
        "close_big_box",
    ]
    assert tracker.update(_result(frame_id)).state == "completed"
