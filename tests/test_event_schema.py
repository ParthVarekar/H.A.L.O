"""Tests for halo.schema.event_schema.EventRecord."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from halo.schema.event_schema import AlertCode, EventRecord, StepStatus


def test_event_record_minimal() -> None:
    rec = EventRecord(
        ts_utc=EventRecord.now_utc(),
        exp_id="EXP-1",
        step_id="open",
        step_status=StepStatus.IN_PROGRESS,
        confidence=0.9,
        evidence_summary="hand grasping box",
    )
    assert rec.alert_code is None
    assert rec.media_ref is None
    assert rec.extra == {}


def test_event_record_to_jsonl_round_trip() -> None:
    rec = EventRecord(
        ts_utc=EventRecord.now_utc(),
        exp_id="EXP-1",
        step_id="open",
        step_status=StepStatus.COMPLETED,
        confidence=0.95,
        evidence_summary="hand grasping box for 30 frames",
        alert_code=AlertCode.SKIP_DETECTED,
        media_ref="chunk_0042#f1230",
    )
    line = rec.to_jsonl()
    parsed = json.loads(line)
    assert parsed["exp_id"] == "EXP-1"
    assert parsed["step_status"] == "completed"
    assert parsed["alert_code"] == "SKIP_DETECTED"


def test_event_record_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValidationError):
        EventRecord(
            ts_utc=EventRecord.now_utc(),
            exp_id="EXP-1",
            step_id="open",
            step_status=StepStatus.IN_PROGRESS,
            confidence=1.5,
            evidence_summary="x",
        )


def test_event_record_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        EventRecord(
            ts_utc=EventRecord.now_utc(),
            exp_id="EXP-1",
            step_id="open",
            step_status="doing_it",  # type: ignore[arg-type]
            confidence=0.5,
            evidence_summary="x",
        )


def test_event_record_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        EventRecord(
            ts_utc=EventRecord.now_utc(),
            exp_id="EXP-1",
            step_id="open",
            step_status=StepStatus.IN_PROGRESS,
            confidence=0.5,
            evidence_summary="x",
            rogue_field="nope",
        )
