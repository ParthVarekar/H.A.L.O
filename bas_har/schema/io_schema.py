"""Pydantic contracts for capture buffering and integrity-protected JSONL."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CircularBufferConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    directory: Path
    fps: float = Field(default=30.0, gt=0, le=240)
    resolution: tuple[int, int] = (1920, 1080)
    segment_seconds: float = Field(default=10.0, gt=0)
    max_segments: int = Field(default=6, ge=1)
    codec: str = Field(default="mp4v", min_length=4, max_length=4)

    @field_validator("resolution")
    @classmethod
    def check_resolution(cls, value: tuple[int, int]) -> tuple[int, int]:
        if value[0] <= 0 or value[1] <= 0:
            raise ValueError("resolution must be positive integers")
        return value


class CrcJsonlEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    payload: dict[str, Any]
    crc32: str = Field(pattern=r"^[0-9a-fA-F]{8}$")

    @field_validator("crc32")
    @classmethod
    def normalize_crc(cls, value: str) -> str:
        return value.lower()
