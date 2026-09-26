"""Tests for the signed, hash-chained event log and the downlink report."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bas_har.io.signed_log import (
    GENESIS_HASH,
    SignedJsonlEventSink,
    build_downlink,
    chain_hash,
    downlink_bytes,
    load_or_create_station_key,
    load_public_key,
    plan_sha256,
    verify_downlink,
    verify_signed_log,
    write_downlink,
)
from bas_har.schema.event_schema import AlertCode, EventRecord, StepStatus
from bas_har.schema.plan_schema import ExperimentPlan


def _plan() -> ExperimentPlan:
    steps = []
    for index, name in enumerate(["open", "take", "close"]):
        steps.append(
            {
                "id": name,
                "description": name,
                "evidence": [{"kind": "object_visible", "object": "box"}],
                "next": [["take", "close", None][index]] if index < 2 else [],
            }
        )
    return ExperimentPlan.model_validate(
        {
            "id": "EXP-SIGN",
            "name": "Signing",
            "objects": [{"id": "box", "classes": ["box"]}],
            "steps": steps,
        }
    )


def _event(step: str, status: StepStatus, seconds: float, **extra: object) -> EventRecord:
    alert = extra.pop("alert_code", None)
    return EventRecord(
        ts_utc=datetime.now(UTC),
        exp_id="EXP-SIGN",
        step_id=step,
        step_status=status,
        confidence=0.9,
        evidence_summary="test",
        alert_code=alert,
        extra={"video_time_s": seconds, **extra},
    )


def _write_session(tmp_path: Path) -> tuple[Path, SignedJsonlEventSink]:
    key = load_or_create_station_key(tmp_path / "keys")
    log_path = tmp_path / "session.jsonl"
    sink = SignedJsonlEventSink(log_path, key, _plan())
    sink.write(_event("open", StepStatus.COMPLETED, 1.5))
    sink.write(_event("take", StepStatus.SKIPPED, 3.0, alert_code=AlertCode.SKIP_DETECTED))
    sink.write(_event("close", StepStatus.COMPLETED, 4.25))
    sink.write(_event("take", StepStatus.COMPLETED, 6.0, out_of_order=True))
    sink.close()
    return log_path, sink


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def test_station_key_is_created_once_and_reused(tmp_path: Path) -> None:
    first = load_or_create_station_key(tmp_path)
    second = load_or_create_station_key(tmp_path)
    assert first.key_id == second.key_id
    assert load_public_key(tmp_path / "station_ed25519.pub") == first.public_bytes


def test_chain_hash_depends_on_previous_sequence_and_content() -> None:
    base = chain_hash(GENESIS_HASH, 0, {"a": 1})
    assert base != chain_hash(GENESIS_HASH, 1, {"a": 1})
    assert base != chain_hash("1" * 64, 0, {"a": 1})
    assert base != chain_hash(GENESIS_HASH, 0, {"a": 2})
    assert base == chain_hash(GENESIS_HASH, 0, {"a": 1})


def test_plan_sha256_is_stable_and_content_sensitive() -> None:
    plan = _plan()
    assert plan_sha256(plan) == plan_sha256(_plan())
    plan.steps[0].description = "changed"
    assert plan_sha256(plan) != plan_sha256(_plan())


def test_signed_log_verifies_with_station_key(tmp_path: Path) -> None:
    log_path, sink = _write_session(tmp_path)
    report = verify_signed_log(log_path, load_public_key(tmp_path / "keys/station_ed25519.pub"))
    assert report.ok
    assert report.trusted_key is True
    assert report.lines == 5
    assert report.events == 4
    assert report.final_hash == sink.final_hash
    assert report.exp_id == "EXP-SIGN"


def test_signed_log_detects_edited_payload(tmp_path: Path) -> None:
    log_path, _ = _write_session(tmp_path)
    lines = _lines(log_path)
    lines[2] = lines[2].replace('"skipped"', '"completed"')
    log_path.write_text("".join(lines), encoding="utf-8")
    report = verify_signed_log(log_path)
    assert not report.ok
    assert report.error_line == 3
    assert "hash" in (report.error or "")


def test_signed_log_detects_deleted_line(tmp_path: Path) -> None:
    log_path, _ = _write_session(tmp_path)
    lines = _lines(log_path)
    del lines[2]
    log_path.write_text("".join(lines), encoding="utf-8")
    report = verify_signed_log(log_path)
    assert not report.ok
    assert report.error_line == 3


def test_signed_log_detects_reordered_lines(tmp_path: Path) -> None:
    log_path, _ = _write_session(tmp_path)
    lines = _lines(log_path)
    lines[2], lines[3] = lines[3], lines[2]
    log_path.write_text("".join(lines), encoding="utf-8")
    assert not verify_signed_log(log_path).ok


def test_signed_log_detects_rebuilt_chain_with_forged_signature(tmp_path: Path) -> None:
    log_path, _ = _write_session(tmp_path)
    lines = _lines(log_path)
    entry = json.loads(lines[1])
    entry["payload"]["confidence"] = 0.1
    entry["hash"] = chain_hash(entry["prev"], entry["seq"], entry["payload"])
    lines[1] = json.dumps(entry) + "\n"
    log_path.write_text("".join(lines), encoding="utf-8")
    report = verify_signed_log(log_path)
    assert not report.ok
    assert report.error_line in {2, 3}


def test_signed_log_rejects_other_station_key(tmp_path: Path) -> None:
    log_path, _ = _write_session(tmp_path)
    other = load_or_create_station_key(tmp_path / "other")
    report = verify_signed_log(log_path, other.public_bytes)
    assert not report.ok
    assert report.trusted_key is False


def test_signed_log_rejects_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    assert not verify_signed_log(empty).ok


def test_signed_log_writer_refuses_to_overwrite(tmp_path: Path) -> None:
    log_path, _ = _write_session(tmp_path)
    key = load_or_create_station_key(tmp_path / "keys")
    with pytest.raises(FileExistsError):
        SignedJsonlEventSink(log_path, key, _plan())


def test_downlink_summarises_session_and_verifies(tmp_path: Path) -> None:
    log_path, sink = _write_session(tmp_path)
    key = load_or_create_station_key(tmp_path / "keys")
    report = build_downlink(sink, key, source_bytes=9_720_664)
    assert [step.status for step in report.steps] == ["completed", "completed", "completed"]
    assert report.steps[1].late
    assert report.steps[0].t_s == 1.5
    assert [alert.code for alert in report.alerts] == ["SKIP_DETECTED"]
    assert report.event_count == 4
    assert report.log_final_hash == sink.final_hash
    size = write_downlink(report, tmp_path / "session.downlink.json")
    assert size == len(downlink_bytes(report))
    assert size < 2048
    result = verify_downlink(tmp_path / "session.downlink.json", key.public_bytes, log_path)
    assert result.ok
    assert result.matches_log is True
    assert result.report_bytes == size


def test_downlink_detects_edit_and_truncated_log(tmp_path: Path) -> None:
    log_path, sink = _write_session(tmp_path)
    key = load_or_create_station_key(tmp_path / "keys")
    downlink = tmp_path / "session.downlink.json"
    write_downlink(build_downlink(sink, key), downlink)
    lines = _lines(log_path)
    log_path.write_text("".join(lines[:-1]), encoding="utf-8")
    truncated = verify_downlink(downlink, key.public_bytes, log_path)
    assert not truncated.ok
    assert truncated.matches_log is False
    data = json.loads(downlink.read_text(encoding="utf-8"))
    data["alerts"] = []
    downlink.write_text(json.dumps(data), encoding="utf-8")
    assert not verify_downlink(downlink, key.public_bytes).ok


def test_downlink_rejects_other_key(tmp_path: Path) -> None:
    _, sink = _write_session(tmp_path)
    key = load_or_create_station_key(tmp_path / "keys")
    downlink = tmp_path / "session.downlink.json"
    write_downlink(build_downlink(sink, key), downlink)
    other = load_or_create_station_key(tmp_path / "other")
    result = verify_downlink(downlink, other.public_bytes)
    assert not result.ok
    assert result.trusted_key is False


def test_downlink_marks_missed_steps(tmp_path: Path) -> None:
    key = load_or_create_station_key(tmp_path / "keys")
    sink = SignedJsonlEventSink(tmp_path / "short.jsonl", key, _plan())
    sink.write(_event("open", StepStatus.COMPLETED, 2.0))
    sink.close()
    report = build_downlink(sink, key)
    assert [step.status for step in report.steps] == ["completed", "missed", "missed"]
