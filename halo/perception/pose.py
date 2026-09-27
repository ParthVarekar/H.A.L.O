"""2D pose wrapper using MediaPipe Pose Landmarker (33 keypoints, 3D-ish but
we use only the xy + visibility here).

COCO-17 names are kept as a reference alias; MediaPipe Pose returns 33 landmarks
in its own ordering, listed below.
"""

from __future__ import annotations

import numpy as np

from halo.perception.types import PoseKeypoints

MEDIAPIPE_POSE_LANDMARK_NAMES: list[str] = [
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]

COCO_KEYPOINT_NAMES: list[str] = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]


class PoseEstimator:
    def __init__(
        self,
        static_image_mode: bool = False,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        import mediapipe as mp

        self._pose = mp.solutions.pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmark_enum = mp.solutions.pose.PoseLandmark

    def estimate(self, frame_bgr: np.ndarray) -> PoseKeypoints | None:
        import cv2

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self._pose.process(rgb)
        if result.pose_landmarks is None:
            return None
        h, w = frame_bgr.shape[:2]
        keypoints: list[tuple[float, float, float]] = []
        total_vis = 0.0
        for lm in result.pose_landmarks.landmark:
            x_px = lm.x * w
            y_px = lm.y * h
            vis = float(lm.visibility)
            keypoints.append((x_px, y_px, vis))
            total_vis += vis
        score = total_vis / max(1, len(keypoints))
        return PoseKeypoints(keypoints=keypoints, score=score)

    def landmark_index(self, name: str) -> int:
        if name in MEDIAPIPE_POSE_LANDMARK_NAMES:
            return MEDIAPIPE_POSE_LANDMARK_NAMES.index(name)
        raise KeyError(f"unknown pose landmark: {name}")
