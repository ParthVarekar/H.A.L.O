"""Tests for the reproduction-check Pydantic contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bas_har.schema.selfcheck_schema import CheckResult, SelfCheckReport


def test_check_result_minimal_valid() -> None:
    assert CheckResult(name="Plans", ok=True).detail == ""


def test_check_result_rejects_missing_fields_and_empty_name() -> None:
    with pytest.raises(ValidationError):
        CheckResult.model_validate({"ok": True})
    with pytest.raises(ValidationError):
        CheckResult(name="", ok=True)


def test_self_check_report_full_valid() -> None:
    report = SelfCheckReport(
        checks=[CheckResult(name="Plans", ok=True)],
        log_path="logs/a.jsonl",
        downlink_path="logs/a.downlink.json",
    )
    assert report.ok


def test_self_check_report_with_no_checks_is_not_ok() -> None:
    assert not SelfCheckReport().ok


def test_self_check_report_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        SelfCheckReport.model_validate({"checks": [], "verdict": "pass"})
