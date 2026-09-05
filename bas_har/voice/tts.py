"""Offline TTS wrapper around pyttsx3.

Falls back gracefully if pyttsx3 cannot init (no audio device, headless
server): alerts are still emitted to the engine, just silently. The dashboard
shows the alert text even without audio.
"""

from __future__ import annotations

import contextlib
import threading
from queue import Empty, Queue

from loguru import logger


class TtsEngine:
    def __init__(self, rate: int = 175) -> None:
        self._queue: Queue[str | None] = Queue()
        self._rate = rate
        self._engine = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._init_engine()
        self._thread = threading.Thread(target=self._loop, name="bas-har-tts", daemon=True)
        self._thread.start()

    def _init_engine(self) -> None:
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._rate)
        except Exception as exc:
            logger.warning(f"pyttsx3 init failed: {exc}. Voice alerts will be silent.")
            self._engine = None

    def say(self, text: str) -> None:
        if not text or self._stop_event.is_set():
            return
        self._queue.put(text)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                text = self._queue.get(timeout=0.5)
            except Empty:
                continue
            if text is None:
                break
            with self._lock:
                if self._engine is None:
                    logger.info(f"[TTS] {text}")
                    continue
                try:
                    self._engine.say(text)
                    self._engine.runAndWait()
                except Exception as exc:
                    logger.warning(f"TTS speak failed: {exc}")

    def shutdown(self) -> None:
        self._stop_event.set()
        with self._lock:
            if self._engine is not None:
                with contextlib.suppress(Exception):
                    self._engine.stop()
        self._queue.put(None)
        self._thread.join(timeout=2.0)


class ConfirmationSound:
    def __init__(self, frequency: int = 880, duration_ms: int = 90) -> None:
        self._frequency = frequency
        self._duration_ms = duration_ms
        self._queue: Queue[bool | None] = Queue()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._loop, name="bas-har-confirmation-sound", daemon=True
        )
        self._thread.start()

    def ping(self) -> None:
        if not self._stop_event.is_set():
            self._queue.put(True)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.5)
            except Empty:
                continue
            if item is None:
                break
            self._beep()

    def _beep(self) -> None:
        try:
            import winsound

            winsound.Beep(self._frequency, self._duration_ms)
        except (ImportError, OSError, RuntimeError):
            return

    def shutdown(self) -> None:
        self._stop_event.set()
        self._queue.put(None)
        self._thread.join(timeout=2.0)
