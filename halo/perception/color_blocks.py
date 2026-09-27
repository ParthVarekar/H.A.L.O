"""Color-segmented block detections for experiments with known object colors."""

from __future__ import annotations

from collections.abc import Iterable

import cv2
import numpy as np

from halo.perception.types import BBox, Detection


class ColorBlockDetector:
    def __init__(self, colors: Iterable[str], min_area: float = 400.0) -> None:
        self.colors = tuple(sorted({color.lower() for color in colors}))
        self.min_area = min_area

    def detect(self, frame_bgr: np.ndarray) -> list[Detection]:
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        detections: list[Detection] = []
        for color in self.colors:
            mask = self._mask_for_color(hsv, color)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contour = self._largest_contour(contours)
            if contour is None:
                continue
            x, y, width, height = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            frame_area = max(1, frame_bgr.shape[0] * frame_bgr.shape[1])
            confidence = min(0.99, 0.65 + area / frame_area * 5.0)
            detections.append(
                Detection(
                    cls="box",
                    conf=confidence,
                    bbox=BBox(x1=x, y1=y, x2=x + width, y2=y + height),
                    color=color,
                )
            )
        return detections

    def _largest_contour(self, contours: Iterable[np.ndarray]) -> np.ndarray | None:
        candidates = [contour for contour in contours if cv2.contourArea(contour) >= self.min_area]
        return max(candidates, key=cv2.contourArea, default=None)

    @staticmethod
    def _mask_for_color(hsv: np.ndarray, color: str) -> np.ndarray:
        if color == "red":
            return cv2.inRange(hsv, np.array([0, 145, 80]), np.array([12, 255, 255])) | cv2.inRange(
                hsv, np.array([170, 145, 80]), np.array([180, 255, 255])
            )
        if color == "blue":
            return cv2.inRange(hsv, np.array([90, 100, 60]), np.array([135, 255, 255]))
        return np.zeros(hsv.shape[:2], dtype=np.uint8)


__all__ = ["ColorBlockDetector"]
