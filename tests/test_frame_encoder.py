"""Tests for dashboard JPEG encoding."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from bas_har.web.frame_encoder import FrameEncoder


def _frame() -> np.ndarray:
    frame = np.zeros((48, 64, 3), dtype=np.uint8)
    frame[:, :32] = (255, 0, 0)
    frame[:, 32:] = (0, 0, 255)
    return frame


def _decoded(data: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)


def test_cpu_encoder_produces_a_decodable_jpeg() -> None:
    encoder = FrameEncoder(device="cpu")
    data = encoder.encode(_frame())
    assert encoder.backend == "opencv"
    assert data is not None and data[:2] == b"\xff\xd8"
    decoded = _decoded(data)
    assert decoded.shape == (48, 64, 3)
    assert decoded[24, 10, 0] > 200 and decoded[24, 54, 2] > 200


def test_gpu_encoder_keeps_colour_order_when_cuda_is_available() -> None:
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("CUDA not available")
    encoder = FrameEncoder(device="cuda:0")
    data = encoder.encode(_frame())
    assert data is not None
    decoded = _decoded(data)
    assert decoded[24, 10, 0] > 200 and decoded[24, 10, 2] < 60
    assert decoded[24, 54, 2] > 200 and decoded[24, 54, 0] < 60


def test_gpu_failure_falls_back_to_opencv() -> None:
    encoder = FrameEncoder(device="cpu")

    class _Broken:
        @staticmethod
        def from_numpy(_array: np.ndarray) -> None:
            raise RuntimeError("nvjpeg unavailable")

    encoder._torch = _Broken()
    encoder._device = "cuda:0"
    data = encoder.encode(_frame())
    assert encoder.backend == "opencv"
    assert data is not None and data[:2] == b"\xff\xd8"
