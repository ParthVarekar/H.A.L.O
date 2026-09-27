"""Confidence smoothing + hysteresis for the procedure engine.

Two responsibilities:

1. **Confidence smoothing** — keep an EMA over per-step match probability so
   the alert filter has a stable number to threshold against.
2. **Transition hysteresis** — once a step is satisfied, hold it in
   `in_progress` for a cooldown window so we don't immediately fall back
   to the previous step on a single noisy frame.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from time import monotonic
from typing import Any


@dataclass(slots=True)
class StepSmoother:
    ema_alpha: float = 0.4
    cooldown_s: float = 1.5
    _ema: dict[str, float] = field(default_factory=dict)
    _cooldown_until: dict[str, float] = field(default_factory=dict)

    def update(self, step_id: str, match_prob: float) -> float:
        prev = self._ema.get(step_id, match_prob)
        smoothed = self.ema_alpha * match_prob + (1.0 - self.ema_alpha) * prev
        self._ema[step_id] = smoothed
        return smoothed

    def get(self, step_id: str) -> float:
        return self._ema.get(step_id, 0.0)

    def lock(self, step_id: str, now: float | None = None) -> None:
        ts = now if now is not None else monotonic()
        self._cooldown_until[step_id] = ts + self.cooldown_s

    def in_cooldown(self, step_id: str, now: float | None = None) -> bool:
        ts = now if now is not None else monotonic()
        until = self._cooldown_until.get(step_id, 0.0)
        return ts < until

    def reset(self) -> None:
        self._ema.clear()
        self._cooldown_until.clear()


@dataclass(slots=True)
class PauseWatchdog:
    """Logs a pause event if no progress for `tolerance_s` seconds."""

    tolerance_s: float
    last_progress_at: float = field(default_factory=monotonic)
    active: bool = False
    fired_at: float | None = None
    _now_fn: Any = field(default=monotonic, repr=False)

    def tick(self, made_progress: bool, now: float | None = None) -> None:
        ts = now if now is not None else self._now_fn()
        if made_progress:
            self.last_progress_at = ts
            self.active = False
            self.fired_at = None
            return
        if not self.active and (ts - self.last_progress_at) >= self.tolerance_s:
            self.active = True
            self.fired_at = ts

    def reset(self, now: float | None = None) -> None:
        ts = now if now is not None else self._now_fn()
        self.last_progress_at = ts
        self.active = False
        self.fired_at = None


@dataclass(slots=True)
class RateLimiter:
    """Block a second event from the same source within `window_s`."""

    window_s: float
    _last: dict[str, float] = field(default_factory=dict)

    def allow(self, key: str, now: float | None = None) -> bool:
        ts = now if now is not None else monotonic()
        last = self._last.get(key, float("-inf"))
        if ts - last < self.window_s:
            return False
        self._last[key] = ts
        return True

    def reset(self) -> None:
        self._last.clear()


@dataclass(slots=True)
class SilenceWindow:
    """Silence-alerts toggle: prevents alerts for `window_s` after enable()."""

    window_s: float
    _until: float = 0.0

    def enable(self, now: float | None = None) -> None:
        ts = now if now is not None else monotonic()
        self._until = ts + self.window_s

    def active(self, now: float | None = None) -> bool:
        ts = now if now is not None else monotonic()
        return ts < self._until

    def remaining(self, now: float | None = None) -> float:
        ts = now if now is not None else monotonic()
        return max(0.0, self._until - ts)


@dataclass(slots=True)
class RecentEvents:
    """Small ring buffer of recent transition events for the dashboard / log tail."""

    capacity: int = 32
    _items: deque = field(default_factory=deque)

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity must be positive")
        self._items = deque(maxlen=self.capacity)

    def push(self, item: Any) -> None:
        self._items.append(item)

    def all(self) -> list[Any]:
        return list(self._items)
