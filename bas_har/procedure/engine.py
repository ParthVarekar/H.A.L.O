"""Procedure engine: deterministic FSM over an `ExperimentPlan`.

Consumes `PerceptionResult` frames, evaluates the current step's evidence
rules, smooths confidence, applies the two-stage alert filter, and emits
`EventRecord`s to an `EventSink`. The sink is injected so the dashboard / log
tailing can subscribe separately from the engine's hot path.

State machine:

    IDLE → (first frame) → IN_PROGRESS (first step)
    IN_PROGRESS → (step evidence satisfied for min_frames) → IN_PROGRESS (next step)
    IN_PROGRESS → (current step paused > tolerance_s) → PAUSED (log only)
    IN_PROGRESS → (next-step evidence appears for a *later* step) → SKIPPED alert
    PAUSED  → (progress resumes) → IN_PROGRESS
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from bas_har.perception.types import PerceptionResult
from bas_har.procedure.alerts import AlertCandidate, Alerter
from bas_har.procedure.events import JsonlEventSink, make_utc_now
from bas_har.procedure.evidence import EvidenceAccumulator, rule_summary
from bas_har.procedure.smoothing import (
    PauseWatchdog,
    RecentEvents,
    StepSmoother,
)
from bas_har.schema.event_schema import AlertCode, EventRecord, StepStatus
from bas_har.schema.plan_schema import ExperimentPlan, StepSpec


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


@dataclass(slots=True)
class ProcedureEngine:
    plan: ExperimentPlan
    sink: EventSink | None = None
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

    def silence(self) -> None:
        self.alerter.silence()
        if self.sink is not None and self._current is not None:
            self._emit(
                self._current.id,
                StepStatus.IN_PROGRESS,
                confidence=0.0,
                evidence_summary="silence_alerts enabled",
                alert_code=AlertCode.LOW_CONFIDENCE,
                extra={"silence_remaining_s": self.alerter.silence_remaining()},
            )

    def close(self) -> None:
        if self.sink is not None:
            close = getattr(self.sink, "close", None)
            if callable(close):
                close()

    def step(self, result: PerceptionResult) -> EngineOutput:
        if self._current is None:
            return self._output()
        self._frame_counter += 1
        frame_id = result.frame_id

        satisfied, verdicts = self.accumulator.evaluate_step(self._current, result)
        avg_conf = sum(v.conf for v in verdicts) / max(1, len(verdicts))
        smoothed = self.smoother.update(self._current.id, avg_conf)

        if self.smoother.in_cooldown(self._current.id):
            return self._output(current_confidence=smoothed)

        if satisfied:
            self.accumulator.reset_step(self._current.id)
            self.smoother.lock(self._current.id)
            self._emit(
                self._current.id,
                StepStatus.COMPLETED,
                confidence=smoothed,
                evidence_summary=rule_summary(verdicts),
            )
            next_step = self._pick_next(self._current, result)
            if next_step is None:
                self._state = EngineState.COMPLETED
                self._current = None
                return self._output(current_confidence=smoothed)
            self._current = next_step
            self._step_started_at_frame = frame_id
            self.pause_watchdog.reset()
            return self._output(current_confidence=smoothed)

        later = self._find_later_step_match(result, completed_step_id=self._current.id)
        if later is not None:
            alert = AlertCandidate(
                code=AlertCode.SKIP_DETECTED,
                step_id=later.id,
                message=f"Step {later.id} detected before completing {self._current.id}.",
                confidence=self.plan.alert_policy.skip_confidence_threshold,
                persistence_frames=self.plan.alert_policy.skip_persistence_frames,
                extra={},
            )
            if self.alerter.fire(alert):
                self._fired.append(alert.code)
                self._emit(
                    self._current.id,
                    StepStatus.ANOMALOUS,
                    confidence=self.plan.alert_policy.skip_confidence_threshold,
                    evidence_summary=rule_summary(verdicts),
                    alert_code=alert.code,
                )

        made_progress = any(v.matched for v in verdicts)
        self.pause_watchdog.tick(made_progress=made_progress)
        if self.pause_watchdog.active and self._state != EngineState.PAUSED:
            self._state = EngineState.PAUSED
            self._emit(
                self._current.id,
                StepStatus.ANOMALOUS,
                confidence=smoothed,
                evidence_summary="no progress for pause_tolerance_s",
                alert_code=AlertCode.PAUSE_EXCEEDED,
            )
        elif made_progress and self._state == EngineState.PAUSED:
            self._state = EngineState.IN_PROGRESS
            self.pause_watchdog.reset()
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

    def _find_later_step_match(
        self, result: PerceptionResult, completed_step_id: str
    ) -> StepSpec | None:
        if self._current is None:
            return None
        steps = self.plan.steps
        current_idx = next(i for i, s in enumerate(steps) if s.id == self._current.id)
        for later in steps[current_idx + 1 :]:
            ok, _ = self.accumulator.evaluate_step(later, result)
            if ok:
                return later
        return None

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
        rec = EventRecord(
            ts_utc=make_utc_now(),
            exp_id=self.plan.experiment_id,
            step_id=step_id,
            step_status=status,
            confidence=confidence,
            evidence_summary=evidence_summary,
            alert_code=alert_code,
            extra=extra or {},
        )
        self.recent.push(rec)
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
            pause_active=self.pause_watchdog.active,
            in_cooldown=(
                self.smoother.in_cooldown(self._current.id) if self._current is not None else False
            ),
        )


def build_engine(
    plan: ExperimentPlan,
    sink: EventSink | None = None,
    sink_path: Path | None = None,
) -> ProcedureEngine:
    if sink is None and sink_path is not None:
        sink = JsonlEventSink(sink_path)
    return ProcedureEngine(plan=plan, sink=sink)


__all__ = [
    "Alerter",
    "EngineOutput",
    "EngineState",
    "EventSink",
    "JsonlEventSink",
    "ProcedureEngine",
    "build_engine",
]
