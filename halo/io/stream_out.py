"""Sends the monitored video to a chosen IP address as an MPEG-TS stream over UDP.

Frames are offered from the presentation thread and encoded on the publisher's own thread; only the
newest frame is kept, so a slow network or encoder never holds up detection.
"""

from __future__ import annotations

import contextlib
import threading
import time
from fractions import Fraction
from typing import Any

import numpy as np

from bas_har.schema.stream_schema import StreamOutputSettings, StreamOutputStatus

CODEC_PREFERENCE = ("h264_nvenc", "libx264", "h264_mf", "mpeg2video")
CODEC_OPTIONS: dict[str, dict[str, str]] = {
    "h264_nvenc": {"preset": "p1", "tune": "ll", "zerolatency": "1"},
    "libx264": {"preset": "ultrafast", "tune": "zerolatency"},
}


class _NewestFrame:
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._frame: np.ndarray | None = None
        self.closed = False

    def put(self, frame: np.ndarray) -> None:
        with self._condition:
            self._frame = frame
            self._condition.notify()

    def take(self, timeout: float) -> np.ndarray | None:
        with self._condition:
            self._condition.wait_for(lambda: self._frame is not None or self.closed, timeout)
            frame, self._frame = self._frame, None
            return frame

    def close(self) -> None:
        with self._condition:
            self.closed = True
            self._condition.notify_all()


class UdpStreamPublisher:
    def __init__(
        self,
        settings: StreamOutputSettings,
        codecs: tuple[str, ...] = CODEC_PREFERENCE,
    ) -> None:
        self.settings = settings
        self._codecs = codecs
        self._slot = _NewestFrame()
        self._lock = threading.Lock()
        self._frames_sent = 0
        self._codec: str | None = None
        self._error: str | None = None
        self._thread = threading.Thread(target=self._run, name="bas-har-stream-out", daemon=True)
        self._thread.start()

    def offer(self, frame_bgr: np.ndarray) -> None:
        if not self._slot.closed:
            self._slot.put(frame_bgr)

    def close(self, timeout: float = 5.0) -> None:
        self._slot.close()
        if self._thread is not threading.current_thread():
            self._thread.join(timeout=timeout)

    def status(self) -> StreamOutputStatus:
        with self._lock:
            return StreamOutputStatus(
                enabled=self.settings.enabled and not self._slot.closed,
                target=self.settings.target,
                player_url=self.settings.player_url,
                frames_sent=self._frames_sent,
                codec=self._codec,
                error=self._error,
            )

    def _open(self, width: int, height: int) -> tuple[Any, Any]:
        import av

        failures: list[str] = []
        for name in self._codecs:
            container = av.open(self.settings.url, mode="w", format="mpegts")
            try:
                stream = container.add_stream(name, rate=self.settings.fps)
                stream.width = width
                stream.height = height
                stream.pix_fmt = "yuv420p"
                stream.bit_rate = self.settings.bitrate_kbps * 1000
                stream.time_base = Fraction(1, self.settings.fps)
                stream.codec_context.gop_size = self.settings.fps
                stream.codec_context.options = dict(CODEC_OPTIONS.get(name, {}))
                stream.codec_context.open()
            except Exception as exc:
                failures.append(f"{name}: {exc}")
                container.close()
                continue
            with self._lock:
                self._codec = name
            return container, stream
        raise RuntimeError("no video encoder could be opened (" + "; ".join(failures) + ")")

    def _run(self) -> None:
        import av

        container: Any | None = None
        stream: Any | None = None
        size: tuple[int, int] | None = None
        started = 0.0
        last_pts = -1
        interval = 1.0 / self.settings.fps
        next_due = 0.0
        try:
            while not self._slot.closed:
                frame = self._slot.take(timeout=0.5)
                if frame is None:
                    continue
                now = time.perf_counter()
                if now < next_due:
                    continue
                next_due = now + interval * 0.9
                height, width = frame.shape[:2]
                even = (width - width % 2, height - height % 2)
                if container is None:
                    container, stream = self._open(*even)
                    size = even
                    started = now
                video_frame = av.VideoFrame.from_ndarray(
                    np.ascontiguousarray(frame[: size[1], : size[0]]), format="bgr24"
                )
                pts = max(last_pts + 1, round((now - started) * self.settings.fps))
                video_frame.pts = pts
                last_pts = pts
                for packet in stream.encode(video_frame):
                    container.mux(packet)
                with self._lock:
                    self._frames_sent += 1
        except Exception as exc:
            with self._lock:
                self._error = str(exc)
        finally:
            if container is not None and stream is not None:
                with contextlib.suppress(Exception):
                    for packet in stream.encode(None):
                        container.mux(packet)
                container.close()
