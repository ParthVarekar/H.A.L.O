"""Smoke tests for the procedure engine module surface."""

from __future__ import annotations

from halo.procedure import (
    Alerter,
    EngineState,
    ProcedureEngine,
    build_engine,
)


def test_engine_module_exports_engine_class() -> None:
    assert callable(ProcedureEngine)
    assert callable(build_engine)
    assert EngineState.IN_PROGRESS == "in_progress"


def test_alerter_class_is_importable() -> None:
    assert callable(Alerter)
