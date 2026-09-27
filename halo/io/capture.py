"""OpenCV frame sources for webcams, MP4 files, and RTSP sub-streams."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2


class VideoCaptureSource:
    def __init__(
        self,
        source: int | str,
        resolution: tuple[int, int] | None = None,
        fps: int | None = None,
    ) -> None:
        self.source = source
        self.resolution = resolution
        self._requested_fps = fps
        self._capture: cv2.VideoCapture | None = None

    @property
    def is_open(self) -> bool:
        return self._capture is not None and self._capture.isOpened()

    @property
    def fps(self) -> float:
        if self._capture is None:
            return 0.0
        return float(self._capture.get(cv2.CAP_PROP_FPS) or 0.0)

    def open(self) -> None:
        if self.is_open:
            return
        backend = cv2.CAP_FFMPEG if self._is_rtsp_source() else cv2.CAP_ANY
        capture = cv2.VideoCapture(self.source, backend)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"could not open capture source: {self.source}")
        if self.resolution is not None:
            width, height = self.resolution
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if self._requested_fps is not None:
            capture.set(cv2.CAP_PROP_FPS, self._requested_fps)
        self._capture = capture

    def read(self) -> tuple[bool, Any]:
        if not self.is_open:
            self.open()
        if self._capture is None:
            raise RuntimeError("capture source is not open")
        return self._capture.read()

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> VideoCaptureSource:
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _is_rtsp_source(self) -> bool:
        return isinstance(self.source, str) and self.source.lower().startswith("rtsp://")


def source_from_path(path: Path) -> VideoCaptureSource:
    return VideoCaptureSource(str(path))
