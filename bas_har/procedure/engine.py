"""Procedure engine: deterministic FSM over an `ExperimentPlan`.

Consumes `PerceptionResult` frames, evaluates the current step's evidence
rules, smooths confidence, applies the two-stage alert filter, and emits
`EventRecord`s to an `EventSink`. The sink is injected so the dashboard / log
tailing can subscribe separately from the engine's hot path.

State machine:

    IDLE → (first frame) → IN_PROGRESS (first step)
    IN_PROGRESS → (step evidence satisfied for min_frames) → IN_PROGRESS (next step)
    IN_PROGRESS → (current step paused > tolerance_s) → PAUSED (log only)
    IN_PROGRESS → (a *later* step's evidence persists) → SKIP alert, jump to after that step
    IN_PROGRESS → (a skipped step's evidence persists) → completed late, OUT_OF_ORDER alert
    PAUSED  → (progress resumes) → IN_PROGRESS

A later (or skipped) step counts as performed once its evidence rules matched in at least
`SKIP_CONFIRM_RATIO` of the last `SKIP_CONFIRM_S` seconds of frames, including the current frame, so
detector flicker does not reset confirmation while a brief false detection cannot trigger it. Every step
between the current step and that later step is recorded as skipped.

The pause tolerance while waiting for a step is the plan's `pause_tolerance_s`, raised to
`PAUSE_DURATION_MARGIN` times the `expected_duration_s` of the step that just completed, because
that step's activity is still under way while the next step's evidence is awaited.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from bas_har.perception.types import PerceptionResult
from bas_har.procedure.alerts import AlertCandidate, Alerter
from bas_har.procedure.events import JsonlEventSink, make_utc_now
from bas_har.procedure.evidence import EvidenceAccumulator, EvidenceVerdict, rule_summary
from bas_har.procedure.smoothing import (
    PauseWatchdog,
    RecentEvents,
    StepSmoother,
)
from bas_har.schema.event_schema import AlertCode, EventRecord, StepStatus
from bas_har.schema.plan_schema import ExperimentPlan, StepSpec

PAUSE_DURATION_MARGIN = 1.5
SKIP_CONFIRM_S = 1.5
SKIP_CONFIRM_RATIO = 0.6


class EngineState(StrEnum):
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"


class EventSink(Protocol):
    def write(self, record: EventRecord) -> None: ...


@dataclass(slots=True)
class EngineOutput:
    state: EngineState
    current_step_id: str
    current_step_confidence: float
    last_event: EventRecord | None
    fired_alerts: list[AlertCode]
    pause_active: bool
    in_cooldown: bool
    events: list[EventRecord] = field(default_factory=list)


@dataclass(slots=True)
class ProcedureEngine:
    plan: ExperimentPlan
    sink: EventSink | None = None
    use_media_time: bool = False
    alerter: Alerter = field(init=False)
    accumulator: EvidenceAccumulator = field(init=False)
    smoother: StepSmoother = field(init=False)
    pause_watchdog: PauseWatchdog = field(init=False)
    recent: RecentEvents = field(init=False)

    _state: EngineState = EngineState.IDLE
    _current: StepSpec | None = field(default=None, init=False)
    _step_started_at_frame: int = field(default=0, init=False)
    _fired: list[AlertCode] = field(default_factory=list, init=False)
    _frame_counter: int = field(default=0, init=False)
    _last_emit_frame: int = field(default=-10_000, init=False)
    _consecutive_heartbeat: int = field(default=0, init=False)
    _now: float | None = field(default=None, init=False)
    _skipped: list[str] = field(default_factory=list, init=False)
    _persistence: dict[str, deque[bool]] = field(default_factory=dict, init=False)
    _step_events: list[EventRecord] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.alerter = Alerter(self.plan.alert_policy)
        self.accumulator = EvidenceAccumulator(
            objects_by_id={o.id: o for o in self.plan.objects},
            regions=set(self.plan.regions),
            region_geometries=dict(self.plan.region_geometries),
        )
        self.smoother = StepSmoother(ema_alpha=0.4, cooldown_s=1.5)
        self.pause_watchdog = PauseWatchdog(tolerance_s=self.plan.alert_policy.pause_tolerance_s)
        self.recent = RecentEvents(capacity=32)
        if self.plan.steps:
            self._current = self.plan.steps[0]
            self._state = EngineState.IN_PROGRESS

    @property
    def state(self) -> EngineState:
        return self._state

    @property
    def current_step(self) -> StepSpec | None:
        return self._current

    def pause_tolerance_after(self, completed: StepSpec) -> float:
        base = self.plan.alert_policy.pause_tolerance_s
        if completed.expected_duration_s is None:
            return base
        return max(base, completed.expected_duration_s * PAUSE_DURATION_MARGIN)

    @property
    def skipped_step_ids(self) -> list[str]:
        return list(self._skipped)

    @property
    def skip_window_frames(self) -> int:
        return max(
            self.plan.alert_policy.skip_persistence_frames,
            round(SKIP_CONFIRM_S * self.plan.camera.fps),
        )

    def silence(self) -> None:
        self.alerter.silence(now=self._now)
        if self.sink is not None and self._current is not None:
            self._emit(
                self._current.id,
                StepStatus.IN_PROGRESS,
                confidence=0.0,
                evidence_summary="silence_alerts enabled",
                alert_code=AlertCode.LOW_CONFIDENCE,
                extra={"silence_remaining_s": self.alerter.silence_remaining(now=self._now)},
            )

    def close(self) -> None:
        if self.sink is not None:
            close = getattr(self.sink, "close", None)
            if callable(close):
                close()

    def step(self, result: PerceptionResult) -> EngineOutput:
        self._step_events = []
        if self._current is None:
            return self._output()
        self._frame_counter += 1
        frame_id = result.frame_id
        self._now = result.ts_ms / 1000.0 if self.use_media_time else None
        now = self._now
        if self.use_media_time and self._frame_counter == 1:
            self.pause_watchdog.reset(now=now)

        satisfied, verdicts = self.accumulator.evaluate_step(self._current, result)
        avg_conf = sum(v.conf for v in verdicts) / max(1, len(verdicts))
        smoothed = self.smoother.update(self._current.id, avg_conf)

        if self.smoother.in_cooldown(self._current.id, now=now):
            return self._output(current_confidence=smoothed)

        if satisfied:
            self.accumulator.reset_step(self._current.id)
            self.smoother.lock(self._current.id, now=now)
            self._emit(
                self._current.id,
                StepStatus.COMPLETED,
                confidence=smoothed,
                evidence_summary=rule_summary(verdicts),
            )
            completed = self._current
            next_step = self._pick_next(self._current, result)
            if next_step is None:
                self._state = EngineState.COMPLETED
                self._current = None
                return self._output(current_confidence=smoothed)
            self._current = next_step
            self._step_started_at_frame = frame_id
            self.pause_watchdog.tolerance_s = self.pause_tolerance_after(completed)
            self.pause_watchdog.reset(now=now)
            return self._output(current_confidence=smoothed)

        late = self._persisting(self._skipped_steps(), result)
        if late is not None:
            self._complete_late(late, now)
        later = self._persisting(self._later_steps(), result)
        if later is not None:
            return self._skip_to(later, result, smoothed, verdicts, now)

        made_progress = any(v.matched for v in verdicts)
        self.pause_watchdog.tick(made_progress=made_progress, now=now)
        if self.pause_watchdog.active and self._state != EngineState.PAUSED:
            self._state = EngineState.PAUSED
            self._emit(
                self._current.id,
                StepStatus.ANOMALOUS,
                confidence=smoothed,
                evidence_summary="no progress for pause_tolerance_s",
                alert_code=AlertCode.PAUSE_EXCEEDED,
                extra={"pause_tolerance_s": self.pause_watchdog.tolerance_s},
            )
        elif made_progress and self._state == EngineState.PAUSED:
            self._state = EngineState.IN_PROGRESS
            self.pause_watchdog.reset(now=now)
            self._emit(
                self._current.id,
                StepStatus.IN_PROGRESS,
                confidence=smoothed,
                evidence_summary=rule_summary(verdicts),
            )

        if made_progress:
            self._consecutive_heartbeat = 0
        else:
            self._consecutive_heartbeat += 1
        if self._frame_counter - self._last_emit_frame >= 30:
            self._emit(
                self._current.id,
                StepStatus.IN_PROGRESS,
                confidence=smoothed,
                evidence_summary=rule_summary(verdicts),
            )
        return self._output(current_confidence=smoothed)

    def _later_steps(self) -> list[StepSpec]:
        if self._current is None:
            return []
        steps = self.plan.steps
        current_idx = next(i for i, s in enumerate(steps) if s.id == self._current.id)
        return [
            candidate
            for offset, candidate in enumerate(steps[current_idx + 1 :], start=current_idx + 1)
            if not self._state_change_pending(steps[current_idx:offset], candidate)
        ]

    @staticmethod
    def _state_change_pending(pending: list[StepSpec], candidate: StepSpec) -> bool:
        wanted = {
            (rule.object, rule.state) for rule in candidate.evidence if rule.kind == "object_state"
        }
        return any(
            rule.kind == "object_state"
            and any(obj == rule.object and state != rule.state for obj, state in wanted)
            for step in pending
            for rule in step.evidence
        )

    def _skipped_steps(self) -> list[StepSpec]:
        return [s for s in self.plan.steps if s.id in self._skipped]

    def _persisting(self, candidates: list[StepSpec], result: PerceptionResult) -> StepSpec | None:
        found: StepSpec | None = None
        size = self.skip_window_frames
        for candidate in candidates:
            _, verdicts = self.accumulator.evaluate_step(candidate, result)
            matched = bool(verdicts) and all(v.matched for v in verdicts)
            window = self._persistence.setdefault(candidate.id, deque(maxlen=size))
            window.append(matched)
            if (
                found is None
                and matched
                and len(window) == size
                and sum(window) >= SKIP_CONFIRM_RATIO * size
            ):
                found = candidate
        return found

    def _fire(self, code: AlertCode, step_id: str, message: str, now: float | None) -> bool:
        alert = AlertCandidate(
            code=code,
            step_id=step_id,
            message=message,
            confidence=self.plan.alert_policy.skip_confidence_threshold,
            persistence_frames=self.plan.alert_policy.skip_persistence_frames,
            extra={},
        )
        if not self.alerter.fire(alert, now=now):
            return False
        self._fired.append(code)
        return True

    def _complete_late(self, step: StepSpec, now: float | None) -> None:
        self._skipped.remove(step.id)
        self._persistence.pop(step.id, None)
        self.accumulator.reset_step(step.id)
        fired = self._fire(
            AlertCode.OUT_OF_ORDER, step.id, f"Step {step.id} performed out of order.", now
        )
        self._emit(
            step.id,
            StepStatus.COMPLETED,
            confidence=self.plan.alert_policy.skip_confidence_threshold,
            evidence_summary="completed after it was skipped",
            alert_code=AlertCode.OUT_OF_ORDER if fired else None,
            extra={"out_of_order": True},
        )

    def _skip_to(
        self,
        later: StepSpec,
        result: PerceptionResult,
        smoothed: float,
        verdicts: list[EvidenceVerdict],
        now: float | None,
    ) -> EngineOutput:
        assert self._current is not None
        steps = self.plan.steps
        start = next(i for i, s in enumerate(steps) if s.id == self._current.id)
        end = next(i for i, s in enumerate(steps) if s.id == later.id)
        skipped = [s for s in steps[start:end] if s.id not in self._skipped]
        fired = self._fire(
            AlertCode.SKIP_DETECTED,
            later.id,
            f"Step {later.id} detected before completing {self._current.id}.",
            now,
        )
        for index, step in enumerate(skipped):
            self._skipped.append(step.id)
            self._persistence.pop(step.id, None)
            self.accumulator.reset_step(step.id)
            self._emit(
                step.id,
                StepStatus.SKIPPED,
                confidence=self.plan.alert_policy.skip_confidence_threshold,
                evidence_summary=rule_summary(verdicts) if step is self._current else "skipped",
                alert_code=AlertCode.SKIP_DETECTED if fired and index == 0 else None,
                extra={"detected_step_id": later.id},
            )
        self._persistence.pop(later.id, None)
        self.accumulator.reset_step(later.id)
        self.smoother.lock(later.id, now=now)
        self._emit(
            later.id,
            StepStatus.COMPLETED,
            confidence=self.plan.alert_policy.skip_confidence_threshold,
            evidence_summary="detected after skipping earlier steps",
        )
        self._state = EngineState.IN_PROGRESS
        next_step = self._pick_next(later, result)
        if next_step is None:
            self._state = EngineState.COMPLETED
            self._current = None
            return self._output(current_confidence=smoothed)
        self._current = next_step
        self._step_started_at_frame = result.frame_id
        self.pause_watchdog.tolerance_s = self.pause_tolerance_after(later)
        self.pause_watchdog.reset(now=now)
        return self._output(current_confidence=smoothed)

    def _pick_next(self, current: StepSpec, result: PerceptionResult) -> StepSpec | None:
        if not current.next:
            return None
        steps_by_id = {s.id: s for s in self.plan.steps}
        for cand_id in current.next:
            cand = steps_by_id.get(cand_id)
            if cand is None:
                continue
            ok, _ = self.accumulator.evaluate_step(cand, result)
            self.accumulator.reset_step(cand.id)
            if ok:
                return cand
        return steps_by_id.get(current.next[0])

    def _emit(
        self,
        step_id: str,
        status: StepStatus,
        confidence: float,
        evidence_summary: str,
        alert_code: AlertCode | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        details = dict(extra or {})
        if self.use_media_time and self._now is not None:
            details["video_time_s"] = round(self._now, 2)
        rec = EventRecord(
            ts_utc=make_utc_now(),
            exp_id=self.plan.experiment_id,
            step_id=step_id,
            step_status=status,
            confidence=confidence,
            evidence_summary=evidence_summary,
            alert_code=alert_code,
            extra=details,
        )
        self.recent.push(rec)
        self._step_events.append(rec)
        if self.sink is not None:
            self.sink.write(rec)
        self._last_emit_frame = self._frame_counter

    def _output(self, current_confidence: float | None = None) -> EngineOutput:
        conf = (
            current_confidence
            if current_confidence is not None
            else (self.smoother.get(self._current.id) if self._current is not None else 0.0)
        )
        last_event = self.recent.all()[-1] if self.recent.all() else None
        return EngineOutput(
            state=self._state,
            current_step_id=self._current.id if self._current is not None else "",
            current_step_confidence=conf,
            last_event=last_event,
            fired_alerts=list(self._fired),
            events=list(self._step_events),
            pause_active=self.pause_watchdog.active,
            in_cooldown=(
                self.smoother.in_cooldown(self._current.id, now=self._now)
                if self._current is not None
                else False
            ),
        )


def build_engine(
    plan: ExperimentPlan,
    sink: EventSink | None = None,
    sink_path: Path | None = None,
    use_media_time: bool = False,
) -> ProcedureEngine:
    if sink is None and sink_path is not None:
        sink = JsonlEventSink(sink_path)
    return ProcedureEngine(plan=plan, sink=sink, use_media_time=use_media_time)


__all__ = [
    "PAUSE_DURATION_MARGIN",
    "SKIP_CONFIRM_RATIO",
    "SKIP_CONFIRM_S",
    "Alerter",
    "EngineOutput",
    "EngineState",
    "EventSink",
    "JsonlEventSink",
    "ProcedureEngine",
    "build_engine",
]
