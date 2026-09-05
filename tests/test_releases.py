"""Tests for model release checksums and approval gates."""

from __future__ import annotations

from pathlib import Path

import pytest

from bas_har.schema.activity_schema import (
    ActivityKind,
    ActivityManifest,
    EvaluationReport,
    ReleaseStatus,
)
from bas_har.studio.evaluation import load_evaluation_report
from bas_har.studio.registry import ActivityRegistry
from bas_har.studio.releases import activate_release, approve_release, create_candidate
from bas_har.studio.verification import release_audit_csv, verify_activity_package


def _registry(tmp_path: Path, passed: bool = True) -> tuple[ActivityRegistry, Path]:
    registry = ActivityRegistry(tmp_path / "activities")
    registry.create(
        ActivityManifest(id="sample_handling", name="Sample Handling", kind=ActivityKind.EXPERIMENT)
    )
    report = EvaluationReport(
        id="evaluation-1",
        activity_id="sample_handling",
        dataset_id="dataset_v1",
        training_job_id="train-1",
        passed=passed,
        metrics={"f1": 0.9 if passed else 0.2},
    )
    report_path = registry.package_dir("sample_handling") / "reports" / "evaluation-1.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report.model_dump_json(by_alias=True), encoding="utf-8")
    model = tmp_path / "best.pt"
    model.write_bytes(b"model")
    return registry, model


def test_release_requires_passed_report_and_records_checksum(tmp_path: Path) -> None:
    registry, model = _registry(tmp_path)

    candidate = create_candidate(registry, "sample_handling", "evaluation-1", model, "0.1.0")
    approved = approve_release(registry, "sample_handling", candidate.release_id, "Parth")
    active = activate_release(registry, "sample_handling", candidate.release_id)

    assert len(candidate.model_sha256) == 64
    assert approved.status is ReleaseStatus.APPROVED
    assert active.status is ReleaseStatus.ACTIVE
    assert registry.load("sample_handling").active_release_id == candidate.release_id
    assert load_evaluation_report(registry, "sample_handling", "evaluation-1").passed
    verification = verify_activity_package(registry, "sample_handling")
    assert verification.passed is False
    assert "plan" in verification.errors[0]
    assert b"release_id" in release_audit_csv(registry, "sample_handling")


def test_release_rejects_failed_report(tmp_path: Path) -> None:
    registry, model = _registry(tmp_path, passed=False)

    with pytest.raises(ValueError, match="passed evaluation"):
        create_candidate(registry, "sample_handling", "evaluation-1", model, "0.1.0")
