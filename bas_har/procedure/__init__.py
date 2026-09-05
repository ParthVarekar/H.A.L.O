"""Procedure engine package.

FSM over an ExperimentPlan that consumes PerceptionResult frames and emits
EventRecord events. Built in Phase 2.
"""

from __future__ import annotations

from bas_har.procedure.alerts import AlertCandidate, Alerter
from bas_har.procedure.engine import (
    EngineOutput,
    EngineState,
    EventSink,
    ProcedureEngine,
    build_engine,
)
from bas_har.procedure.events import JsonlEventSink, make_utc_now
from bas_har.procedure.evidence import (
    EvidenceAccumulator,
    EvidenceVerdict,
    rule_summary,
)
from bas_har.procedure.sequence import ColorSequenceTracker, SequenceObservation
from bas_har.procedure.smoothing import (
    PauseWatchdog,
    RateLimiter,
    RecentEvents,
    SilenceWindow,
    StepSmoother,
)

__all__ = [
    "AlertCandidate",
    "Alerter",
    "ColorSequenceTracker",
    "EngineOutput",
    "EngineState",
    "EventSink",
    "EvidenceAccumulator",
    "EvidenceVerdict",
    "JsonlEventSink",
    "PauseWatchdog",
    "ProcedureEngine",
    "RateLimiter",
    "RecentEvents",
    "SequenceObservation",
    "SilenceWindow",
    "StepSmoother",
    "build_engine",
    "make_utc_now",
    "rule_summary",
]
