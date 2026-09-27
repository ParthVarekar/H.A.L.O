"""Alert message templates for the voice layer."""

from __future__ import annotations

from bas_har.procedure.alerts import AlertCandidate
from bas_har.procedure.engine import ProcedureEngine
from bas_har.schema.event_schema import AlertCode


def format_alert_message(engine: ProcedureEngine, candidate: AlertCandidate) -> str:
    current = engine.current_step.id if engine.current_step else "experiment"
    step_desc = engine.current_step.description if engine.current_step else "the current step"
    if candidate.code == AlertCode.SKIP_DETECTED:
        return f"Step {candidate.step_id} was skipped. Please complete it before {current}."
    if candidate.code == AlertCode.OUT_OF_ORDER:
        return f"Step {candidate.step_id} is out of order. Resume {step_desc.lower()}."
    if candidate.code == AlertCode.WRONG_OBJECT:
        return f"Wrong object for {candidate.step_id}. Expected the correct item."
    if candidate.code == AlertCode.PAUSE_EXCEEDED:
        return f"No progress on {current}. Please continue."
    if candidate.code == AlertCode.LOW_CONFIDENCE:
        return f"Low confidence on {current}. Standing by for ground review."
    return f"Alert on {candidate.step_id}."
