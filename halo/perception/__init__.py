"""Perception layer — YOLO detector, 2D pose, hand keypoints, hand-object interaction.

Each module exposes a small wrapper class that loads its model on construction
and returns a per-frame `PerceptionResult`. The procedure engine in Phase 3
consumes `PerceptionResult`; it never touches Ultralytics / MediaPipe APIs.
"""

from __future__ import annotations

from bas_har.perception.color_blocks import ColorBlockDetector
from bas_har.perception.detector import ObjectDetector
from bas_har.perception.pipeline import PerceptionPipeline
from bas_har.perception.types import (
    BBox,
    Detection,
    HandKeypoints,
    HandObjectInteraction,
    PerceptionResult,
    PoseKeypoints,
)

__all__ = [
    "BBox",
    "ColorBlockDetector",
    "Detection",
    "HandKeypoints",
    "HandObjectInteraction",
    "ObjectDetector",
    "PerceptionPipeline",
    "PerceptionResult",
    "PoseKeypoints",
]
