"""Validated activity plan persistence for the Training Studio."""

from __future__ import annotations

from pathlib import Path

import yaml

from bas_har.schema.activity_schema import ActivityLifecycle
from bas_har.schema.plan_schema import ExperimentPlan
from bas_har.studio.registry import ActivityRegistry


def load_activity_plan(
    registry: ActivityRegistry,
    activity_id: str,
) -> ExperimentPlan:
    manifest = registry.load(activity_id)
    package_dir = registry.package_dir(manifest.activity_id).resolve()
    plan_path = _safe_package_path(package_dir, manifest.plan_path)
    if not plan_path.is_file():
        raise FileNotFoundError(f"activity plan not found: {plan_path}")
    raw = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"activity plan root must be a mapping: {plan_path}")
    return ExperimentPlan.model_validate(raw)


def save_activity_plan(
    registry: ActivityRegistry,
    activity_id: str,
    plan: ExperimentPlan,
) -> ExperimentPlan:
    manifest = registry.load(activity_id)
    if plan.experiment_id != manifest.activity_id:
        raise ValueError("plan id must match the activity id")
    package_dir = registry.package_dir(manifest.activity_id).resolve()
    plan_path = _safe_package_path(package_dir, manifest.plan_path)
    plan_path.write_text(
        yaml.safe_dump(plan.model_dump(mode="json", by_alias=True), sort_keys=False),
        encoding="utf-8",
    )
    if manifest.lifecycle is ActivityLifecycle.DRAFT:
        registry.save(manifest.model_copy(update={"lifecycle": ActivityLifecycle.IMPORTED}))
    return plan


def _safe_package_path(package_dir: Path, relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError("activity plan path must be relative to the package")
    resolved = (package_dir / candidate).resolve()
    if package_dir not in resolved.parents:
        raise ValueError("activity plan path must stay inside the package")
    return resolved


__all__ = ["load_activity_plan", "save_activity_plan"]
