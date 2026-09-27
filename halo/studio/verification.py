"""Activity-package verification and release audit exports."""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path

from halo.schema.activity_schema import (
    ActivityId,
    PackageVerification,
    RecordId,
    ReleaseStatus,
)
from halo.studio.evaluation import load_evaluation_report
from halo.studio.plans import load_activity_plan
from halo.studio.registry import ActivityRegistry
from halo.studio.releases import list_releases, load_release


def verify_activity_package(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    release_id: RecordId | str | None = None,
) -> PackageVerification:
    manifest = registry.load(activity_id)
    checks: dict[str, bool] = {}
    errors: list[str] = []
    try:
        load_activity_plan(registry, manifest.activity_id)
        checks["plan"] = True
    except (FileNotFoundError, ValueError) as exc:
        checks["plan"] = False
        errors.append(str(exc))
    releases = list_releases(registry, manifest.activity_id)
    selected = None
    if release_id is not None:
        try:
            selected = load_release(registry, manifest.activity_id, release_id)
        except (FileNotFoundError, ValueError) as exc:
            errors.append(str(exc))
    else:
        selected = next(
            (
                release
                for release in releases
                if release.release_id == manifest.active_release_id
                and release.status in {ReleaseStatus.APPROVED, ReleaseStatus.ACTIVE}
            ),
            next(
                (
                    release
                    for release in reversed(releases)
                    if release.status in {ReleaseStatus.APPROVED, ReleaseStatus.ACTIVE}
                ),
                None,
            ),
        )
    checks["release_available"] = selected is not None
    if selected is None:
        errors.append("no approved or active release is available")
    else:
        checks["release_status"] = selected.status in {ReleaseStatus.APPROVED, ReleaseStatus.ACTIVE}
        if not checks["release_status"]:
            errors.append("selected release is not approved or active")
        model_path = registry.package_dir(manifest.activity_id) / selected.model_path
        checks["model_exists"] = model_path.is_file()
        if not checks["model_exists"]:
            errors.append(f"release model not found: {model_path}")
        checksum_matches = checks["model_exists"] and selected.model_sha256 is not None
        if checksum_matches:
            checksum_matches = _sha256(model_path) == selected.model_sha256
        checks["checksum"] = checksum_matches
        if not checksum_matches:
            errors.append("release model checksum does not match its recorded checksum")
        try:
            report = load_evaluation_report(
                registry, manifest.activity_id, selected.evaluation_report_id
            )
            checks["evaluation"] = report.passed
            if not report.passed:
                errors.append("release evaluation is not passing")
        except (FileNotFoundError, ValueError) as exc:
            checks["evaluation"] = False
            errors.append(str(exc))
    verification = PackageVerification(
        id=f"verification-{manifest.activity_id}",
        activity_id=manifest.activity_id,
        release_id=selected.release_id if selected is not None else None,
        passed=bool(checks) and all(checks.values()) and not errors,
        checks=checks,
        errors=errors,
    )
    path = registry.package_dir(manifest.activity_id) / "reports" / "package_verification.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(verification.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
    return verification


def load_verification(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
) -> PackageVerification:
    manifest = registry.load(activity_id)
    path = registry.package_dir(manifest.activity_id) / "reports" / "package_verification.json"
    if not path.is_file():
        raise FileNotFoundError(f"package verification not found: {path}")
    return PackageVerification.model_validate_json(path.read_text(encoding="utf-8"))


def release_audit_csv(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
) -> bytes:
    releases = list_releases(registry, activity_id)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "release_id",
            "version",
            "status",
            "model_path",
            "dataset_id",
            "evaluation_report_id",
            "model_sha256",
            "approved_by",
        ]
    )
    for release in releases:
        writer.writerow(
            [
                release.release_id,
                release.version,
                release.status,
                release.model_path,
                release.dataset_id,
                release.evaluation_report_id,
                release.model_sha256 or "",
                release.approved_by or "",
            ]
        )
    return output.getvalue().encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "load_verification",
    "release_audit_csv",
    "verify_activity_package",
]
