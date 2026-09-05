"""Perception data structures.

Plain dataclasses, Pydantic-free (we want this layer to be importable without
pydantic for unit tests / quick scripts). JSON-serialisable.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class BBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    def center(self) -> tuple[float, float]:
        return (self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0

    def area(self) -> float:
        return self.width() * self.height()


@dataclass(slots=True)
class Detection:
    cls: str
    conf: float
    bbox: BBox
    color: str | None = None


@dataclass(slots=True)
class PoseKeypoints:
    """33 COCO-style keypoints, each (x, y, conf) in image pixels + score."""

    keypoints: list[tuple[float, float, float]]
    score: float

    def by_name(self, name: str) -> tuple[float, float, float]:
        from bas_har.perception.pose import MEDIAPIPE_POSE_LANDMARK_NAMES

        if name not in MEDIAPIPE_POSE_LANDMARK_NAMES:
            raise KeyError(f"unknown pose landmark: {name}")
        idx = MEDIAPIPE_POSE_LANDMARK_NAMES.index(name)
        return self.keypoints[idx]


@dataclass(slots=True)
class HandKeypoints:
    """21 MediaPipe hand keypoints per detected hand."""

    handedness: str
    score: float
    keypoints: list[tuple[float, float, float]]

    def wrist(self) -> tuple[float, float, float]:
        return self.keypoints[0]

    def index_tip(self) -> tuple[float, float, float]:
        return self.keypoints[8]

    def middle_mcp(self) -> tuple[float, float, float]:
        return self.keypoints[9]


@dataclass(slots=True)
class HandObjectInteraction:
    """Heuristic HOI tag: which hand is on which object class, plus a score."""

    hand: str
    object_cls: str
    label: str
    score: float


@dataclass(slots=True)
class PerceptionResult:
    """One frame of perception. Produced by `PerceptionPipeline` per frame."""

    frame_id: int
    ts_ms: int
    width: int
    height: int
    detections: list[Detection] = field(default_factory=list)
    pose: PoseKeypoints | None = None
    hands: list[HandKeypoints] = field(default_factory=list)
    hoi: list[HandObjectInteraction] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))
