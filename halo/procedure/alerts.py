"""Two-stage alert filter + rate limiter + silence window.

Per Technical Doc §6: confidence > 0.85 AND persistence ≥ 5 frames for a
"trigger". One alert per 5 seconds. Silence window 60s (audit-logged).

The engine produces alert **candidates**; the filter decides which actually
fire. The filter is decoupled so it can be unit-tested in isolation and so
the voice layer (Phase 4) can subscribe to `Alerter.fired`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any

from halo.procedure.smoothing import RateLimiter, SilenceWindow
from halo.schema.event_schema import AlertCode
from halo.schema.plan_schema import AlertPolicy


@dataclass(slots=True)
class AlertCandidate:
    code: AlertCode
    step_id: str
    message: str
    confidence: float
    persistence_frames: int
    extra: dict[str, Any]


class Alerter:
    def __init__(self, policy: AlertPolicy) -> None:
        self._policy = policy
        self._rate = RateLimiter(window_s=policy.rate_limit_s)
        self._silence = SilenceWindow(window_s=policy.silence_window_s)
        self._fired: list[tuple[float, AlertCandidate]] = []
        self._listeners: list[Callable[[AlertCandidate], None]] = []

    def silence(self, now: float | None = None) -> None:
        self._silence.enable(now=now)

    def silence_active(self, now: float | None = None) -> bool:
        return self._silence.active(now=now)

    def silence_remaining(self, now: float | None = None) -> float:
        return self._silence.remaining(now=now)

    def on_fire(self, callback: Callable[[AlertCandidate], None]) -> None:
        self._listeners.append(callback)

    def fired(self) -> list[tuple[float, AlertCandidate]]:
        return list(self._fired)

    def should_fire(self, candidate: AlertCandidate, now: float | None = None) -> bool:
        ts = now if now is not None else monotonic()
        if candidate.confidence < self._policy.skip_confidence_threshold:
            return False
        if candidate.persistence_frames < self._policy.skip_persistence_frames:
            return False
        if self._silence.active(now=ts):
            return False
        return self._rate.allow(candidate.code, now=ts)

    def fire(self, candidate: AlertCandidate, now: float | None = None) -> bool:
        if not self.should_fire(candidate, now=now):
            return False
        ts = now if now is not None else monotonic()
        self._fired.append((ts, candidate))
        for cb in self._listeners:
            cb(candidate)
        return True
