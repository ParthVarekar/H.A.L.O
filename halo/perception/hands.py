"""Hand keypoint wrapper using MediaPipe Hands (21 landmarks per hand)."""

from __future__ import annotations

import numpy as np

from halo.perception.types import HandKeypoints


class HandKeypointExtractor:
    def __init__(
        self,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        import mediapipe as mp

        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def extract(self, frame_bgr: np.ndarray) -> list[HandKeypoints]:
        import cv2

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self._hands.process(rgb)
        if result.multi_hand_landmarks is None:
            return []
        out: list[HandKeypoints] = []
        h, w = frame_bgr.shape[:2]
        handedness = "right"
        if result.multi_handedness:
            first = result.multi_handedness[0]
            handedness = first.classification[0].label.lower()
        for hand_landmarks in result.multi_hand_landmarks:
            keypoints: list[tuple[float, float, float]] = []
            for lm in hand_landmarks.landmark:
                keypoints.append((lm.x * w, lm.y * h, float(lm.visibility)))
            out.append(
                HandKeypoints(
                    handedness=handedness,
                    score=float(hand_landmarks.landmark[0].visibility),
                    keypoints=keypoints,
                )
            )
        return out
