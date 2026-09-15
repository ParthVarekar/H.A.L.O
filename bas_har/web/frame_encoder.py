"""JPEG encoding for dashboard stream frames, on the GPU (nvjpeg) when available."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

JPEG_QUALITY = 82


class FrameEncoder:
    def __init__(self, device: str = "auto", quality: int = JPEG_QUALITY) -> None:
        self.quality = quality
        self._torch: Any = None
        self._encode_jpeg: Any = None
        self._device: Any = None
        if device != "cpu":
            self._try_gpu(device)

    @property
    def backend(self) -> str:
        return "nvjpeg" if self._device is not None else "opencv"

    def _try_gpu(self, device: str) -> None:
        try:
            import torch
            from torchvision.io import encode_jpeg
        except ImportError:
            return
        if not torch.cuda.is_available():
            return
        target = torch.device("cuda:0" if device in ("auto", "cuda") else device)
        if target.type != "cuda":
            return
        try:
            probe = torch.zeros((3, 16, 16), dtype=torch.uint8, device=target)
            encode_jpeg(probe, quality=self.quality)
        except (RuntimeError, TypeError, ValueError):
            return
        self._torch = torch
        self._encode_jpeg = encode_jpeg
        self._device = target

    def encode(self, frame_bgr: np.ndarray) -> bytes | None:
        if self._device is not None:
            try:
                tensor = self._torch.from_numpy(np.ascontiguousarray(frame_bgr)).to(self._device)
                rgb = tensor.flip(-1).permute(2, 0, 1).contiguous()
                encoded = self._encode_jpeg(rgb, quality=self.quality)
                return bytes(encoded.cpu().numpy().tobytes())
            except (RuntimeError, TypeError, ValueError):
                self._device = None
        ok, buffer = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
        return buffer.tobytes() if ok else None


__all__ = ["JPEG_QUALITY", "FrameEncoder"]
