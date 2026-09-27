"""Hardware discovery for local Training Studio jobs."""

from __future__ import annotations

import platform
from typing import Any


def hardware_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cuda_available": False,
        "device": "cpu",
        "device_name": None,
        "vram_gb": None,
    }
    try:
        import torch
    except ImportError:
        return snapshot
    if not torch.cuda.is_available():
        return snapshot
    device_index = torch.cuda.current_device()
    total_memory = torch.cuda.get_device_properties(device_index).total_memory
    snapshot.update(
        {
            "cuda_available": True,
            "device": f"cuda:{device_index}",
            "device_name": torch.cuda.get_device_name(device_index),
            "vram_gb": round(total_memory / (1024**3), 2),
        }
    )
    return snapshot


__all__ = ["hardware_snapshot"]
