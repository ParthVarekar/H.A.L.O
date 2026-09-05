"""Perception pipeline: composes detector + pose + hands + HOI per frame."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import numpy as np

from bas_har.perception.color_blocks import ColorBlockDetector
from bas_har.perception.detector import ObjectDetector
from bas_har.perception.hands import HandKeypointExtractor
from bas_har.perception.hoi import HandObjectInteractionTagger
from bas_har.perception.pose import PoseEstimator
from bas_har.perception.types import PerceptionResult


class PerceptionPipeline:
    def __init__(
        self,
        yolo_model: str | Path | None = None,
        target_classes: list[str] | None = None,
        run_pose: bool = True,
        run_hands: bool = True,
        device: str = "auto",
        color_names: Iterable[str] | None = None,
    ) -> None:
        self.detector = ObjectDetector(
            model_path=yolo_model,
            device=device,
            target_classes=target_classes,
        )
        self.run_pose = run_pose
        self.run_hands = run_hands
        self.color_detector = ColorBlockDetector(color_names or ()) if color_names else None
        self.pose = PoseEstimator() if run_pose else None
        self.hands = HandKeypointExtractor() if run_hands else None
        self.hoi = HandObjectInteractionTagger() if run_hands else None

    @property
    def device(self) -> str:
        return self.detector.device

    def process(self, frame_bgr: np.ndarray, frame_id: int, ts_ms: int) -> PerceptionResult:
        h, w = frame_bgr.shape[:2]
        detections = self.detector.detect(frame_bgr)
        if self.color_detector is not None:
            detections.extend(self.color_detector.detect(frame_bgr))
        pose = self.pose.estimate(frame_bgr) if self.pose else None
        hands = self.hands.extract(frame_bgr) if self.hands else []
        hoi = self.hoi.tag(hands, detections) if self.hoi and hands else []
        return PerceptionResult(
            frame_id=frame_id,
            ts_ms=ts_ms,
            width=w,
            height=h,
            detections=detections,
            pose=pose,
            hands=hands,
            hoi=hoi,
        )
