"""Tests for the voice engine lifecycle."""

from __future__ import annotations

from halo.voice import ConfirmationSound, TtsEngine


def test_tts_shutdown_stops_worker_thread() -> None:
    engine = TtsEngine()
    engine.shutdown()

    assert not engine._thread.is_alive()


def test_confirmation_sound_can_ping_and_shutdown() -> None:
    sound = ConfirmationSound()
    sound._beep = lambda: None
    sound.ping()
    sound.shutdown()

    assert not sound._thread.is_alive()
