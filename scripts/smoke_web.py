"""Headless smoke test for the React dashboard build and plan contract."""

from __future__ import annotations

from bas_har.config import project_root
from bas_har.schema.cli import load_plan
from bas_har.web.server import STATIC_DIR, _plan_summary


def main() -> int:
    plan_path = project_root() / "experiments" / "red_blue_box" / "experiment_plan.yaml"
    plan = load_plan(plan_path)
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        raise RuntimeError(f"React build not found: {index}")
    summary = _plan_summary(plan)
    if len(summary["steps"]) != len(plan.steps):
        raise RuntimeError("React plan summary does not match the YAML plan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
