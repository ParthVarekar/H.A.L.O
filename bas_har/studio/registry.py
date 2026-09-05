"""Filesystem-backed registry for local activity packages."""

from __future__ import annotations

from pathlib import Path

import yaml

from bas_har.config import activities_dir
from bas_har.schema.activity_schema import ActivityId, ActivityManifest


class ActivityRegistry:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or activities_dir()

    def create(self, manifest: ActivityManifest) -> ActivityManifest:
        package_dir = self.package_dir(manifest.activity_id)
        if package_dir.exists():
            raise FileExistsError(f"activity package already exists: {manifest.activity_id}")
        package_dir.mkdir(parents=True)
        self._write_manifest(package_dir, manifest)
        return manifest

    def save(self, manifest: ActivityManifest) -> ActivityManifest:
        package_dir = self.package_dir(manifest.activity_id)
        if not package_dir.is_dir():
            raise FileNotFoundError(f"activity package not found: {manifest.activity_id}")
        self._write_manifest(package_dir, manifest)
        return manifest

    def load(self, activity_id: ActivityId | str) -> ActivityManifest:
        manifest_path = self.package_dir(activity_id) / "activity.yaml"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"activity manifest not found: {manifest_path}")
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"activity manifest root must be a mapping: {manifest_path}")
        return ActivityManifest.model_validate(raw)

    def list_activities(self) -> list[ActivityManifest]:
        if not self.root.is_dir():
            return []
        manifests: list[ActivityManifest] = []
        for package_dir in sorted(path for path in self.root.iterdir() if path.is_dir()):
            manifest_path = package_dir / "activity.yaml"
            if manifest_path.is_file():
                manifests.append(self.load(package_dir.name))
        return manifests

    def package_dir(self, activity_id: ActivityId | str) -> Path:
        return self.root / str(activity_id)

    def _write_manifest(self, package_dir: Path, manifest: ActivityManifest) -> None:
        package_dir.mkdir(parents=True, exist_ok=True)
        for name in ("takes", "datasets", "reports", "releases", "camera_profiles"):
            (package_dir / name).mkdir(exist_ok=True)
        path = package_dir / "activity.yaml"
        payload = manifest.model_dump(mode="json", by_alias=True, exclude_none=True)
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


__all__ = ["ActivityRegistry"]
