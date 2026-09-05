"""Tests for Phase 5 I/O schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bas_har.schema.io_schema import CircularBufferConfig, CrcJsonlEntry


def test_circular_buffer_config_valid() -> None:
    config = CircularBufferConfig(directory="buffer", resolution=[640, 480])

    assert config.resolution == (640, 480)
    assert config.max_segments == 6


def test_circular_buffer_config_rejects_invalid_values() -> None:
    with pytest.raises(ValidationError):
        CircularBufferConfig(directory="buffer", resolution=[0, 480])
    with pytest.raises(ValidationError):
        CircularBufferConfig(directory="buffer", max_segments=0)
    with pytest.raises(ValidationError):
        CircularBufferConfig(directory="buffer", codec="mp4")


def test_crc_entry_normalizes_checksum() -> None:
    entry = CrcJsonlEntry(payload={"event": "ok"}, crc32="ABCDEF12")

    assert entry.crc32 == "abcdef12"


def test_crc_entry_rejects_bad_checksum() -> None:
    with pytest.raises(ValidationError):
        CrcJsonlEntry(payload={"event": "ok"}, crc32="not-a-crc")
