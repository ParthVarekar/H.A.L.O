"""Perception pipeline: composes detector + pose + hands + HOI per frame."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

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
        conf_threshold: float = 0.25,
        prompt_classes: dict[str, str] | None = None,
        questioner: Any | None = None,
        run_detector: bool = True,
    ) -> None:
        self.detector: Any | None = None
        if not run_detector:
            self._device = ObjectDetector.resolve_device(device)
        elif prompt_classes:
            from bas_har.perception.open_vocab import OpenVocabDetector

            self.detector = OpenVocabDetector(
                prompt_classes=prompt_classes,
                device=device,
                conf_threshold=conf_threshold,
            )
        else:
            self.detector = ObjectDetector(
                model_path=yolo_model,
                device=device,
                conf_threshold=conf_threshold,
                target_classes=target_classes,
            )
        self.questioner = questioner
        self.run_pose = run_pose
        self.run_hands = run_hands
        self.color_detector = ColorBlockDetector(color_names or ()) if color_names else None
        self.pose = PoseEstimator() if run_pose else None
        self.hands = HandKeypointExtractor() if run_hands else None
        self.hoi = HandObjectInteractionTagger() if run_hands else None

    @property
    def device(self) -> str:
        return self.detector.device if self.detector is not None else self._device

    def warmup(self, width: int, height: int) -> None:
        if self.detector is not None:
            self.detector.warmup(width, height)

    def process(self, frame_bgr: np.ndarray, frame_id: int, ts_ms: int) -> PerceptionResult:
        h, w = frame_bgr.shape[:2]
        detections = self.detector.detect(frame_bgr) if self.detector is not None else []
        if self.color_detector is not None:
            detections.extend(self.color_detector.detect(frame_bgr))
        pose = self.pose.estimate(frame_bgr) if self.pose else None
        hands = self.hands.extract(frame_bgr) if self.hands else []
        hoi = self.hoi.tag(hands, detections) if self.hoi and hands else []
        questions: dict[str, float] = {}
        if self.questioner is not None:
            self.questioner.submit(frame_bgr)
            questions = self.questioner.latest()
        return PerceptionResult(
            frame_id=frame_id,
            ts_ms=ts_ms,
            width=w,
            height=h,
            detections=detections,
            pose=pose,
            hands=hands,
            hoi=hoi,
            questions=questions,
        )
