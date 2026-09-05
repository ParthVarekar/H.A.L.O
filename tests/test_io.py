"""Tests for Phase 5 capture, buffering, and integrity utilities."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from bas_har.io.capture import VideoCaptureSource, source_from_path
from bas_har.io.circular_buffer import Mp4CircularBuffer
from bas_har.io.crc_jsonl import CrcJsonlEventSink, CrcJsonlVerifier, CrcJsonlWriter
from bas_har.schema.event_schema import EventRecord, StepStatus
from bas_har.schema.io_schema import CircularBufferConfig


class _FakeCapture:
    def __init__(self, opened: bool) -> None:
        self.opened = opened
        self.released = False
        self.settings: dict[int, float] = {}

    def isOpened(self) -> bool:
        return self.opened

    def set(self, property_id: int, value: float) -> bool:
        self.settings[property_id] = value
        return True

    def get(self, property_id: int) -> float:
        if property_id == cv2.CAP_PROP_FPS:
            return 24.0
        return self.settings.get(property_id, 0.0)

    def read(self) -> tuple[bool, str]:
        return True, "frame"

    def release(self) -> None:
        self.released = True


def test_video_capture_source_uses_ffmpeg_for_rtsp(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeCapture(opened=True)
    calls: list[tuple[object, int]] = []

    def factory(source: object, backend: int) -> _FakeCapture:
        calls.append((source, backend))
        return fake

    monkeypatch.setattr(cv2, "VideoCapture", factory)
    source = VideoCaptureSource("rtsp://camera/sub", resolution=(640, 480), fps=15)

    source.open()
    ok, frame = source.read()
    capture_fps = source.fps
    source.close()

    assert calls == [("rtsp://camera/sub", cv2.CAP_FFMPEG)]
    assert ok and frame == "frame"
    assert fake.settings[cv2.CAP_PROP_FRAME_WIDTH] == 640
    assert fake.settings[cv2.CAP_PROP_FRAME_HEIGHT] == 480
    assert fake.settings[cv2.CAP_PROP_FPS] == 15
    assert capture_fps == 24.0
    assert fake.released
    assert not source.is_open


def test_video_capture_source_rejects_unavailable_source(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeCapture(opened=False)
    monkeypatch.setattr(cv2, "VideoCapture", lambda *_args: fake)

    with pytest.raises(RuntimeError, match="could not open capture source"):
        VideoCaptureSource(99).open()

    assert fake.released


def test_source_from_path_preserves_path_value() -> None:
    source = source_from_path(Path("sample.mp4"))

    assert source.source == "sample.mp4"


def test_mp4_circular_buffer_retains_only_recent_segments(tmp_path: Path) -> None:
    config = CircularBufferConfig(
        directory=tmp_path / "buffer",
        fps=10,
        resolution=(16, 16),
        segment_seconds=0.1,
        max_segments=2,
    )
    frame = np.zeros((16, 16, 3), dtype=np.uint8)

    with Mp4CircularBuffer(config) as buffer:
        for _ in range(5):
            buffer.write(frame)
        paths = buffer.paths()

    assert len(paths) == 2
    assert all(path.exists() and path.stat().st_size > 0 for path in paths)


def test_mp4_circular_buffer_rejects_writes_after_close(tmp_path: Path) -> None:
    config = CircularBufferConfig(directory=tmp_path / "buffer", resolution=(16, 16))
    buffer = Mp4CircularBuffer(config)
    buffer.close()

    with pytest.raises(RuntimeError, match="buffer is closed"):
        buffer.write(np.zeros((16, 16, 3), dtype=np.uint8))


def test_crc_jsonl_round_trip_and_tamper_detection(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    with CrcJsonlWriter(path) as writer:
        entry = writer.write({"event": "step_completed", "confidence": 0.9})

    assert entry.crc32 == CrcJsonlWriter.checksum(entry.payload)
    assert CrcJsonlVerifier.verify(path) == [{"event": "step_completed", "confidence": 0.9}]

    tampered = path.read_text(encoding="utf-8").replace("0.9", "0.8")
    path.write_text(tampered, encoding="utf-8")
    with pytest.raises(ValueError, match="CRC mismatch"):
        CrcJsonlVerifier.verify(path)


def test_crc_event_sink_writes_verifiable_event(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    sink = CrcJsonlEventSink(path)
    sink.write(
        EventRecord(
            ts_utc=EventRecord.now_utc(),
            exp_id="EXP",
            step_id="step",
            step_status=StepStatus.COMPLETED,
            confidence=0.9,
            evidence_summary="ok",
        )
    )
    sink.close()

    records = CrcJsonlVerifier.verify(path)

    assert records[0]["exp_id"] == "EXP"
