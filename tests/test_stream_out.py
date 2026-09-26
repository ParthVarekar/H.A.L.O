"""Tests for the UDP MPEG-TS stream publisher."""

from __future__ import annotations

import socket
import time

import numpy as np
import pytest

from bas_har.io.stream_out import UdpStreamPublisher
from bas_har.schema.stream_schema import StreamOutputSettings

TS_SYNC_BYTE = 0x47
TS_PACKET_BYTES = 188


@pytest.fixture
def receiver() -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(5)
    yield sock
    sock.close()


def _publish(receiver: socket.socket, codecs: tuple[str, ...]) -> tuple[UdpStreamPublisher, bytes]:
    port = receiver.getsockname()[1]
    publisher = UdpStreamPublisher(
        StreamOutputSettings(enabled=True, port=port, fps=15), codecs=codecs
    )
    for index in range(20):
        publisher.offer(np.full((120, 161, 3), index * 10, np.uint8))
        time.sleep(0.07)
    datagram = receiver.recv(65536)
    publisher.close()
    return publisher, datagram


def test_publisher_sends_mpeg_ts_packets(receiver: socket.socket) -> None:
    publisher, datagram = _publish(receiver, ("mpeg2video",))
    assert len(datagram) % TS_PACKET_BYTES == 0
    assert all(datagram[i] == TS_SYNC_BYTE for i in range(0, len(datagram), TS_PACKET_BYTES))
    status = publisher.status()
    assert status.codec == "mpeg2video"
    assert status.frames_sent > 0
    assert status.error is None
    assert not status.enabled


def test_publisher_falls_back_to_next_codec(receiver: socket.socket) -> None:
    publisher, _ = _publish(receiver, ("no_such_encoder", "mpeg2video"))
    assert publisher.status().codec == "mpeg2video"


def test_publisher_reports_when_no_codec_opens(receiver: socket.socket) -> None:
    port = receiver.getsockname()[1]
    publisher = UdpStreamPublisher(
        StreamOutputSettings(enabled=True, port=port), codecs=("no_such_encoder",)
    )
    publisher.offer(np.zeros((64, 64, 3), np.uint8))
    time.sleep(0.5)
    publisher.close()
    assert "no video encoder" in (publisher.status().error or "")


def test_publisher_ignores_frames_after_close(receiver: socket.socket) -> None:
    port = receiver.getsockname()[1]
    publisher = UdpStreamPublisher(StreamOutputSettings(enabled=True, port=port))
    publisher.close()
    publisher.offer(np.zeros((64, 64, 3), np.uint8))
    assert publisher.status().frames_sent == 0
