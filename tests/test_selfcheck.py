"""Tests for the one-command reproduction check and the `python -m halo` subcommands."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from halo import __main__ as cli
from halo import selfcheck
from halo.io.signed_log import (
    SignedJsonlEventSink,
    build_downlink,
    load_or_create_station_key,
    write_downlink,
)
from halo.schema.cli import load_plan
from halo.schema.event_schema import AlertCode, EventRecord, StepStatus
from halo.schema.selfcheck_schema import CheckResult, SelfCheckReport

PLAN = Path("experiments/red_blue_box/experiment_plan.yaml")


def _session(tmp_path: Path, alert: bool = False) -> tuple[dict, Path]:
    plan = load_plan(PLAN)
    keys = tmp_path / "keys"
    key = load_or_create_station_key(keys)
    sink = SignedJsonlEventSink(tmp_path / "run.jsonl", key, plan)
    for step in plan.steps:
        sink.write(
            EventRecord(
                ts_utc=datetime.now(UTC),
                exp_id=plan.experiment_id,
                step_id=step.id,
                step_status=StepStatus.COMPLETED,
                confidence=0.9,
                evidence_summary="ok",
                alert_code=AlertCode.OUT_OF_ORDER if alert else None,
                extra={"video_time_s": 1.0},
            )
        )
    sink.close()
    downlink = tmp_path / "run.downlink.json"
    write_downlink(build_downlink(sink, key, source_bytes=1_000_000), downlink)
    ids = [step.id for step in plan.steps]
    status = {
        "device": "cpu",
        "elapsed_s": 1.0,
        "error": None,
        "summary": {
            "total_steps": len(ids),
            "completed_steps": ids,
            "out_of_order_steps": [],
            "skipped_steps": [],
            "missed_steps": [],
            "source_finished": True,
        },
        "downlink": {
            "path": str(downlink),
            "log_path": str(sink.path),
            "ratio": 1000,
        },
    }
    return status, keys


def test_check_plans_passes_for_repository_plans() -> None:
    result = selfcheck.check_plans(selfcheck.plan_paths())
    assert result.ok
    assert result.detail.startswith(f"{len(selfcheck.plan_paths())} of")


def test_check_plans_reports_invalid_plan(tmp_path: Path) -> None:
    broken = tmp_path / "broken" / "plan.yaml"
    broken.parent.mkdir()
    broken.write_text("id: X\nname: X\nsteps: []\n", encoding="utf-8")
    result = selfcheck.check_plans([broken])
    assert not result.ok
    assert "broken" in result.detail


def test_check_session_passes_clean_run(tmp_path: Path) -> None:
    status, _ = _session(tmp_path)
    assert all(check.ok for check in selfcheck.check_session(status))


def test_check_session_fails_on_alerts_and_missing_steps(tmp_path: Path) -> None:
    status, _ = _session(tmp_path, alert=True)
    status["summary"]["completed_steps"] = status["summary"]["completed_steps"][:-1]
    results = {check.name: check.ok for check in selfcheck.check_session(status)}
    assert results["No false alerts"] is False
    assert results["Every step recognised"] is False


def test_check_skip_caught_needs_a_skip_alert_on_the_removed_step(tmp_path: Path) -> None:
    clean, _ = _session(tmp_path / "clean")
    assert not selfcheck.check_skip_caught(clean).ok
    plan = load_plan(PLAN)
    key = load_or_create_station_key(tmp_path / "keys")
    sink = SignedJsonlEventSink(tmp_path / "skip.jsonl", key, plan)
    sink.write(
        EventRecord(
            ts_utc=datetime.now(UTC),
            exp_id=plan.experiment_id,
            step_id=plan.steps[0].id,
            step_status=StepStatus.SKIPPED,
            confidence=0.9,
            evidence_summary="skipped",
            alert_code=AlertCode.SKIP_DETECTED,
            extra={"video_time_s": 1.5},
        )
    )
    sink.close()
    downlink = tmp_path / "skip.downlink.json"
    write_downlink(build_downlink(sink, key), downlink)
    result = selfcheck.check_skip_caught({"downlink": {"path": str(downlink)}}, plan.steps[0].id)
    assert result.ok
    assert "1.5 s" in result.detail


def test_check_session_reports_runtime_error() -> None:
    results = selfcheck.check_session({"error": "camera lost"})
    assert [check.ok for check in results] == [False]


def test_check_evidence_verifies_log_and_downlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    status, keys = _session(tmp_path)
    monkeypatch.setattr(selfcheck, "keys_dir", lambda: keys)
    results = selfcheck.check_evidence(status)
    assert [check.ok for check in results] == [True, True]
    assert "1,000x smaller" in results[1].detail


def test_format_report_shows_verdict() -> None:
    report = SelfCheckReport(
        checks=[CheckResult(name="One", ok=True, detail="fine"), CheckResult(name="Two", ok=False)]
    )
    text = selfcheck.format_report(report)
    assert "PASS  One" in text
    assert "FAIL  Two" in text
    assert "SOME CHECKS FAILED (1/2)" in text
    assert not report.ok
    assert SelfCheckReport(checks=[CheckResult(name="One", ok=True)]).ok


def test_cli_verify_log_and_downlink(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    status, keys = _session(tmp_path)
    public = str(keys / "station_ed25519.pub")
    log = status["downlink"]["log_path"]
    report = status["downlink"]["path"]
    assert cli.main(["verify-log", log, "--public-key", public]) == 0
    assert "VALID" in capsys.readouterr().out
    assert cli.main(["verify-downlink", report, "--log", log, "--public-key", public]) == 0
    assert "seals the given log" in capsys.readouterr().out
    lines = Path(log).read_text(encoding="utf-8").splitlines(keepends=True)
    Path(log).write_text("".join(lines[:2] + lines[3:]), encoding="utf-8")
    assert cli.main(["verify-log", log, "--public-key", public]) == 1
    assert "INVALID at line 3" in capsys.readouterr().out


def test_cli_verify_downlink_needs_public_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status, _ = _session(tmp_path)
    missing = str(tmp_path / "nope.pub")
    assert cli.main(["verify-downlink", status["downlink"]["path"], "--public-key", missing]) == 1
    assert "not found" in capsys.readouterr().out


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--version"]) == 0
    assert capsys.readouterr().out.strip()
