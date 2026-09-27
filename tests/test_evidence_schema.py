"""Tests for the signed-log and downlink Pydantic contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from halo.schema.evidence_schema import (
    DownlinkReport,
    DownlinkStep,
    SignedLogHeader,
    SignedLogLine,
)

HASH = "a" * 64
KEY_ID = "0123456789abcdef"
PUBLIC_KEY = "A" * 44
SIGNATURE = "B" * 88


def test_signed_log_header_minimal_valid() -> None:
    header = SignedLogHeader(
        exp_id="EXP",
        plan_sha256=HASH,
        public_key=PUBLIC_KEY,
        key_id=KEY_ID,
        created_utc=datetime.now(UTC),
    )
    assert header.kind == "header"
    assert header.format == "halo-signed-log/1"


def test_signed_log_header_rejects_bad_hash_and_missing_key() -> None:
    with pytest.raises(ValidationError):
        SignedLogHeader(
            exp_id="EXP",
            plan_sha256="XYZ",
            public_key=PUBLIC_KEY,
            key_id=KEY_ID,
            created_utc=datetime.now(UTC),
        )
    with pytest.raises(ValidationError):
        SignedLogHeader.model_validate(
            {"exp_id": "EXP", "plan_sha256": HASH, "created_utc": "2026-09-26T00:00:00Z"}
        )


def test_signed_log_line_valid_and_rejects_negative_sequence() -> None:
    line = SignedLogLine(seq=0, payload={}, prev=HASH, hash=HASH, sig=SIGNATURE)
    assert line.seq == 0
    with pytest.raises(ValidationError):
        SignedLogLine(seq=-1, payload={}, prev=HASH, hash=HASH, sig=SIGNATURE)


def test_downlink_report_full_valid() -> None:
    report = DownlinkReport(
        exp_id="EXP",
        plan_sha256=HASH,
        key_id=KEY_ID,
        started_utc=datetime.now(UTC),
        ended_utc=datetime.now(UTC),
        steps=[DownlinkStep(id="open", status="completed", t_s=1.0)],
        event_count=3,
        log_final_hash=HASH,
        source_bytes=100,
    )
    assert report.format == "halo-downlink/1"
    assert report.alerts == []


def test_downlink_step_rejects_bad_status() -> None:
    with pytest.raises(ValidationError):
        DownlinkStep(id="open", status="done")


def test_downlink_report_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        DownlinkReport.model_validate(
            {
                "exp_id": "EXP",
                "plan_sha256": HASH,
                "key_id": KEY_ID,
                "ended_utc": "2026-09-26T00:00:00Z",
                "steps": [],
                "event_count": 0,
                "log_final_hash": HASH,
                "surprise": True,
            }
        )
