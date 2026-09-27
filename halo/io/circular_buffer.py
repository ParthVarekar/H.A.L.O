"""Rotating MP4 frame buffer for retaining the most recent video segments."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2

from halo.schema.io_schema import CircularBufferConfig


class Mp4CircularBuffer:
    def __init__(self, config: CircularBufferConfig) -> None:
        self.config = config
        self._writer: cv2.VideoWriter | None = None
        self._paths: list[Path] = sorted(config.directory.glob("segment_*.mp4"))
        self._segment_index = self._last_segment_index()
        self._segment_frames = 0
        self._frames_per_segment = max(1, round(config.fps * config.segment_seconds))
        self._closed = False

    def write(self, frame: Any) -> None:
        if self._closed:
            raise RuntimeError("circular buffer is closed")
        if self._writer is None:
            self._open_segment()
        if self._writer is None:
            raise RuntimeError("circular buffer writer is not open")
        self._writer.write(frame)
        self._segment_frames += 1
        if self._segment_frames >= self._frames_per_segment:
            self._close_segment()

    def paths(self) -> list[Path]:
        return [path for path in self._paths if path.exists()]

    def flush(self) -> None:
        self._close_segment()

    def close(self) -> None:
        if self._closed:
            return
        self._close_segment()
        self._closed = True

    def __enter__(self) -> Mp4CircularBuffer:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _open_segment(self) -> None:
        self.config.directory.mkdir(parents=True, exist_ok=True)
        self._segment_index += 1
        path = self.config.directory / f"segment_{self._segment_index:06d}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*self.config.codec)
        writer = cv2.VideoWriter(str(path), fourcc, self.config.fps, self.config.resolution)
        if not writer.isOpened():
            writer.release()
            raise RuntimeError(f"could not open video writer: {path}")
        self._writer = writer
        self._segment_frames = 0
        self._paths.append(path)
        while len(self._paths) > self.config.max_segments:
            old_path = self._paths.pop(0)
            old_path.unlink(missing_ok=True)

    def _close_segment(self) -> None:
        if self._writer is None:
            return
        self._writer.release()
        self._writer = None
        self._segment_frames = 0

    def _last_segment_index(self) -> int:
        indices = [self._segment_number(path) for path in self._paths]
        return max(indices, default=0)

    @staticmethod
    def _segment_number(path: Path) -> int:
        try:
            return int(path.stem.split("_", 1)[1])
        except (IndexError, ValueError):
            return 0
