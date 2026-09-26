"""Tests for the stream-output Pydantic contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bas_har.schema.stream_schema import StreamOutputSettings, StreamOutputStatus


def test_stream_output_settings_minimal_valid() -> None:
    settings = StreamOutputSettings()
    assert not settings.enabled
    assert settings.target == "127.0.0.1:5000"
    assert settings.url == "udp://127.0.0.1:5000?pkt_size=1316"
    assert settings.player_url == "udp://@:5000"


def test_stream_output_settings_full_valid() -> None:
    settings = StreamOutputSettings(
        enabled=True, host="192.168.1.20", port=6000, fps=25, bitrate_kbps=4000
    )
    assert settings.target == "192.168.1.20:6000"


def test_stream_output_settings_brackets_ipv6() -> None:
    assert StreamOutputSettings(host="::1").target == "[::1]:5000"


def test_stream_output_settings_rejects_hostname_and_bad_port() -> None:
    with pytest.raises(ValidationError):
        StreamOutputSettings(host="ground-station.local")
    with pytest.raises(ValidationError):
        StreamOutputSettings(port=80)
    with pytest.raises(ValidationError):
        StreamOutputSettings(fps=0)


def test_stream_output_settings_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        StreamOutputSettings.model_validate({"protocol": "rtmp"})


def test_stream_output_settings_from_url() -> None:
    settings = StreamOutputSettings.from_url("udp://10.0.0.7:5004")
    assert settings.enabled
    assert settings.target == "10.0.0.7:5004"
    assert StreamOutputSettings.from_url("udp://[::1]:5004").target == "[::1]:5004"
    with pytest.raises(ValueError):
        StreamOutputSettings.from_url("rtmp://10.0.0.7:5004")
    with pytest.raises(ValueError):
        StreamOutputSettings.from_url("udp://10.0.0.7")


def test_stream_output_status_requires_target() -> None:
    status = StreamOutputStatus(enabled=True, target="1.2.3.4:5000", player_url="udp://@:5000")
    assert status.frames_sent == 0
    with pytest.raises(ValidationError):
        StreamOutputStatus.model_validate({"enabled": True})
