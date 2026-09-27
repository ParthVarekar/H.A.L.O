"""Tests for halo.schema.cli (the `validate-plan` command)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from halo.schema.cli import main, validate_path


def _write_plan(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "experiment_plan.yaml"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


VALID_PLAN = """
    id: EXP-1
    name: Test
    objects:
      - id: box
        classes: [box]
    steps:
      - id: open
        description: open
        evidence:
          - kind: hand_object_interaction
            object: box
            label: opening
            min_frames: 1
        next: [close]
      - id: close
        description: close
        evidence:
          - kind: hand_object_interaction
            object: box
            label: closing
            min_frames: 1
        next: []
"""


def test_validate_path_ok(tmp_path: Path) -> None:
    p = _write_plan(tmp_path, VALID_PLAN)
    ok, msg = validate_path(p)
    assert ok, msg
    assert "EXP-1" in msg


def test_validate_path_missing_file(tmp_path: Path) -> None:
    p = tmp_path / "nope.yaml"
    ok, msg = validate_path(p)
    assert not ok
    assert "not found" in msg.lower()


def test_validate_path_bad_yaml(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("id: [unterminated", encoding="utf-8")
    ok, msg = validate_path(p)
    assert not ok
    assert "yaml" in msg.lower()


def test_validate_path_schema_violation(tmp_path: Path) -> None:
    p = _write_plan(
        tmp_path,
        """
        id: EXP-1
        name: Bad
        steps:
          - id: open
            description: open
            evidence:
              - kind: hand_object_interaction
                object: missing_obj
                label: opening
            next: []
        """,
    )
    ok, msg = validate_path(p)
    assert not ok
    assert "unknown object" in msg


def test_main_returns_0_for_valid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = _write_plan(tmp_path, VALID_PLAN)
    rc = main([str(p), "--quiet"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out == "" or "EXP-1" in out


def test_main_returns_1_for_invalid(tmp_path: Path) -> None:
    p = _write_plan(
        tmp_path,
        """
        id: EXP-1
        name: Bad
        steps: []
        """,
    )
    rc = main([str(p), "--quiet"])
    assert rc == 1
