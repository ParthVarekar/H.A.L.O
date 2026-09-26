"""JSONL event schema for the on-board activity log.

One event per line, append-only, parseable by `pd.read_json(path, lines=True)`.
Per Technical Doc §6: UTC ms-precision timestamps, experiment/step identifiers,
status, confidence, evidence summary, alert code, media reference.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StepStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ANOMALOUS = "anomalous"
    UNKNOWN = "unknown"


class AlertCode(StrEnum):
    SKIP_DETECTED = "SKIP_DETECTED"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    WRONG_OBJECT = "WRONG_OBJECT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    PAUSE_EXCEEDED = "PAUSE_EXCEEDED"
    CAMERA_LOST = "CAMERA_LOST"
    STEP_OVERDUE = "STEP_OVERDUE"


class EventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    ts_utc: datetime = Field(description="UTC timestamp with ms precision.")
    exp_id: str
    step_id: str
    step_status: StepStatus
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_summary: str
    alert_code: AlertCode | None = None
    media_ref: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(UTC).replace(microsecond=(datetime.now().microsecond // 1000) * 1000)

    def to_jsonl(self) -> str:
        return self.model_dump_json()
