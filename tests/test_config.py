"""Smoke test for halo.config helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from halo import config


def test_project_root_is_dir() -> None:
    assert isinstance(config.project_root(), Path)
    assert config.project_root().is_dir()


def test_experiments_dir_exists_in_repo() -> None:
    assert config.experiments_dir().name == "experiments"


def test_logs_dir_creates_on_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "project_root", lambda: tmp_path)
    log_dir = config.logs_dir()
    assert log_dir.is_dir()


def test_keys_dir_creates_on_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "project_root", lambda: tmp_path)
    assert config.keys_dir() == tmp_path / "keys"
    assert config.keys_dir().is_dir()


def test_default_camera_source_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HALO_CAMERA", "2")
    assert config.default_camera_source() == 2
    monkeypatch.delenv("HALO_CAMERA", raising=False)
    assert config.default_camera_source() == 0
