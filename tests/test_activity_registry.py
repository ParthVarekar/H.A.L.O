"""Tests for local activity package storage."""

from __future__ import annotations

from pathlib import Path

import pytest

from bas_har.schema.activity_schema import ActivityKind, ActivityManifest
from bas_har.studio.registry import ActivityRegistry


def _manifest() -> ActivityManifest:
    return ActivityManifest(
        id="sample_handling",
        name="Sample Handling",
        kind=ActivityKind.EXPERIMENT,
    )


def test_registry_create_load_and_list(tmp_path: Path) -> None:
    registry = ActivityRegistry(tmp_path)
    created = registry.create(_manifest())

    loaded = registry.load("sample_handling")

    assert loaded == created
    assert [item.activity_id for item in registry.list_activities()] == ["sample_handling"]
    assert (tmp_path / "sample_handling" / "takes").is_dir()


def test_registry_rejects_duplicate_activity(tmp_path: Path) -> None:
    registry = ActivityRegistry(tmp_path)
    registry.create(_manifest())

    with pytest.raises(FileExistsError):
        registry.create(_manifest())


def test_registry_load_rejects_missing_activity(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ActivityRegistry(tmp_path).load("missing_activity")
