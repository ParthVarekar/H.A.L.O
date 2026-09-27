"""Checksummed model candidates and explicit human release approval."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from uuid import uuid4

from pydantic import TypeAdapter

from halo.config import project_root
from halo.schema.activity_schema import (
    ActivityId,
    ActivityLifecycle,
    ModelRelease,
    RecordId,
    ReleaseStatus,
)
from halo.studio.evaluation import load_evaluation_report
from halo.studio.registry import ActivityRegistry


def create_candidate(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    evaluation_report_id: RecordId | str,
    model_path: str | Path,
    version: str,
) -> ModelRelease:
    manifest = registry.load(activity_id)
    report = load_evaluation_report(registry, manifest.activity_id, str(evaluation_report_id))
    if not report.passed:
        raise ValueError("only a passed evaluation can produce a release candidate")
    safe_version = TypeAdapter(RecordId).validate_python(version)
    source = _resolve_path(model_path)
    if not source.is_file():
        raise FileNotFoundError(f"trained model not found: {source}")
    release_id = f"release-{uuid4().hex[:12]}"
    release_dir = registry.package_dir(manifest.activity_id) / "releases"
    release_dir.mkdir(parents=True, exist_ok=True)
    destination = release_dir / f"{safe_version}.pt"
    if destination.exists():
        raise FileExistsError(f"release version already exists: {safe_version}")
    shutil.copy2(source, destination)
    release = ModelRelease(
        id=release_id,
        activity_id=manifest.activity_id,
        version=safe_version,
        model_path=str(destination.relative_to(registry.package_dir(manifest.activity_id))),
        plan_path=manifest.plan_path,
        dataset_id=report.dataset_id,
        evaluation_report_id=report.report_id,
        model_sha256=_sha256(destination),
    )
    _write_release(registry, release)
    return release


def approve_release(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    release_id: RecordId | str,
    reviewer: str,
) -> ModelRelease:
    manifest = registry.load(activity_id)
    release = load_release(registry, manifest.activity_id, release_id)
    if release.status is not ReleaseStatus.CANDIDATE:
        raise ValueError(f"release is not a candidate: {release.release_id}")
    reviewer_name = reviewer.strip()
    if not reviewer_name:
        raise ValueError("reviewer is required for release approval")
    report = load_evaluation_report(registry, manifest.activity_id, release.evaluation_report_id)
    if not report.passed:
        raise ValueError("release evaluation is no longer passing")
    approved = release.model_copy(
        update={"status": ReleaseStatus.APPROVED, "approved_by": reviewer_name}
    )
    _write_release(registry, approved)
    registry.save(manifest.model_copy(update={"lifecycle": ActivityLifecycle.APPROVED}))
    return approved


def activate_release(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    release_id: RecordId | str,
) -> ModelRelease:
    manifest = registry.load(activity_id)
    release = load_release(registry, manifest.activity_id, release_id)
    if release.status is not ReleaseStatus.APPROVED:
        raise ValueError("only an approved release can become active")
    active = release.model_copy(update={"status": ReleaseStatus.ACTIVE})
    _write_release(registry, active)
    registry.save(
        manifest.model_copy(
            update={"lifecycle": ActivityLifecycle.ACTIVE, "active_release_id": active.release_id}
        )
    )
    return active


def list_releases(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
) -> list[ModelRelease]:
    manifest = registry.load(activity_id)
    release_dir = registry.package_dir(manifest.activity_id) / "releases"
    if not release_dir.is_dir():
        return []
    releases: list[ModelRelease] = []
    for path in sorted(release_dir.glob("release-*.json")):
        releases.append(ModelRelease.model_validate_json(path.read_text(encoding="utf-8")))
    return releases


def load_release(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    release_id: RecordId | str,
) -> ModelRelease:
    manifest = registry.load(activity_id)
    safe_id = TypeAdapter(RecordId).validate_python(release_id)
    path = registry.package_dir(manifest.activity_id) / "releases" / f"{safe_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"release not found: {path}")
    return ModelRelease.model_validate_json(path.read_text(encoding="utf-8"))


def _write_release(registry: ActivityRegistry, release: ModelRelease) -> None:
    path = registry.package_dir(release.activity_id) / "releases" / f"{release.release_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(release.model_dump_json(by_alias=True, indent=2), encoding="utf-8")


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root() / path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "activate_release",
    "approve_release",
    "create_candidate",
    "list_releases",
    "load_release",
]
