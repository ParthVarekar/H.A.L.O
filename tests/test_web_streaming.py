"""Tests for real-speed playback, frame hand-off, and push-based streaming helpers."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from halo.schema.cli import load_plan
from halo.web.server import (
    LatestSlot,
    PlaybackClock,
    SessionRunner,
    StageTimer,
    WebState,
    _cpu_fallback,
    _is_file_source,
)


class _FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class _RecordingStop(threading.Event):
    def __init__(self, clock: _FakeClock) -> None:
        super().__init__()
        self.clock = clock
        self.waits: list[float] = []

    def wait(self, timeout: float | None = None) -> bool:
        self.waits.append(round(timeout or 0.0, 3))
        self.clock.now += timeout or 0.0
        return False


def test_playback_clock_waits_until_each_frame_is_due() -> None:
    clock = _FakeClock()
    stop = _RecordingStop(clock)
    playback = PlaybackClock(25.0, stop, now=clock)
    playback.start()
    assert playback.wait_for(0)
    assert playback.wait_for(1)
    assert stop.waits == [0.04]
    clock.now += 0.01
    assert playback.wait_for(2)
    assert stop.waits[-1] == 0.03


def test_playback_clock_skips_frames_when_too_far_behind() -> None:
    clock = _FakeClock()
    playback = PlaybackClock(25.0, _RecordingStop(clock), now=clock, max_lag_s=0.5)
    playback.start()
    clock.now += 0.4
    assert playback.wait_for(0)
    clock.now += 0.3
    assert not playback.wait_for(1)
    assert playback.lag_s(1) > 0.5


def test_latest_slot_keeps_only_the_newest_item() -> None:
    slot = LatestSlot()
    for item in (1, 2, 3):
        slot.put(item)
    assert slot.take(timeout=0.01) == 3
    assert slot.dropped == 2
    assert slot.take(timeout=0.01) is None
    slot.close()
    assert slot.closed


def test_wait_for_frame_wakes_on_a_new_frame() -> None:
    state = WebState(load_plan(Path("experiments/red_blue_box/experiment_plan.yaml")))
    state.set_frame(b"first", 1)
    threading.Timer(0.05, state.set_frame, args=(b"second", 2)).start()
    started = time.perf_counter()
    frame, frame_id = state.wait_for_frame(1, timeout=2.0)
    assert (frame, frame_id) == (b"second", 2)
    assert time.perf_counter() - started < 1.0


def test_wait_for_frame_times_out_without_a_new_frame() -> None:
    state = WebState(load_plan(Path("experiments/red_blue_box/experiment_plan.yaml")))
    state.set_frame(b"only", 5)
    assert state.wait_for_frame(5, timeout=0.05) == (b"only", 5)


def test_file_sources_are_paced_and_uploads_skip_the_backup_buffer() -> None:
    state = WebState(load_plan(Path("experiments/red_blue_box/experiment_plan.yaml")))
    upload = SessionRunner(state, source="C:/videos/take.mp4", yolo_model="m.pt", upload=True)
    camera = SessionRunner(state, source="0", yolo_model="m.pt")
    stream = SessionRunner(state, source="rtsp://cam/stream", yolo_model="m.pt")
    assert upload.realtime and not upload.record_buffer
    assert not camera.realtime and camera.record_buffer
    assert not stream.realtime and stream.record_buffer
    assert _is_file_source("clip.MOV") and not _is_file_source(0)


def test_cpu_fallback_only_flags_cpu_runs_with_a_gpu_present() -> None:
    assert _cpu_fallback("cpu", gpu_present=True)
    assert not _cpu_fallback("cpu", gpu_present=False)
    assert not _cpu_fallback("cuda:0", gpu_present=True)


def test_stage_timer_smooths_values_in_milliseconds() -> None:
    timer = StageTimer(alpha=0.5)
    timer.record("detect", 0.010)
    timer.record("detect", 0.020)
    assert timer.snapshot() == {"detect": 15.0}
