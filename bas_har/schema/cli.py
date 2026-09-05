"""`validate-plan` CLI: load, lint, and print a summary of an experiment plan YAML.

Accepts one or more YAML paths. Returns 0 on success, 1 on any failure.
The 'human-reads-the-plan' check is intentionally a separate manual step (see
`docs/architecture.md`); the validator handles mechanical correctness.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from pydantic import ValidationError

from bas_har.schema.plan_schema import ExperimentPlan


def load_plan(path: Path) -> ExperimentPlan:
    if not path.exists():
        raise FileNotFoundError(f"plan file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"plan root must be a mapping, got {type(raw).__name__}")
    return ExperimentPlan.model_validate(raw)


def summarize(plan: ExperimentPlan) -> str:
    lines: list[str] = []
    lines.append(f"Experiment: {plan.name} (id={plan.experiment_id}, v{plan.version})")
    lines.append(f"Author: {plan.author}  Created: {plan.created or 'n/a'}")
    lines.append("")
    lines.append(
        f"Camera: source={plan.camera.source} "
        f"{plan.camera.resolution[0]}x{plan.camera.resolution[1]}@{plan.camera.fps}"
    )
    lines.append(
        f"Fiducial: {plan.fiducial.type} (family={plan.fiducial.family}, "
        f"size={plan.fiducial.size_mm}mm)"
    )
    lines.append(f"Objects ({len(plan.objects)}):")
    for obj in plan.objects:
        colors = ",".join(obj.colors_any) or "any"
        lines.append(f"  - {obj.id}: classes={obj.classes} colors={colors}")
    if plan.regions:
        lines.append(f"Regions: {plan.regions}")
    else:
        lines.append("Regions: (none defined)")
    lines.append("")
    lines.append(f"Steps ({len(plan.steps)}):")
    for i, step in enumerate(plan.steps, 1):
        next_ids = ",".join(step.next) if step.next else "TERMINAL"
        timeout = f" timeout={step.timeout_s:.0f}s" if step.timeout_s else ""
        lines.append(f"  {i}. {step.id}  -> [{next_ids}]{timeout}")
        lines.append(f"     {step.description}")
        for rule in step.evidence:
            lines.append(f"     - {rule.model_dump(exclude_none=True)}")
    lines.append("")
    ap = plan.alert_policy
    lines.append(
        f"Alert policy: conf>={ap.skip_confidence_threshold} "
        f"persist>={ap.skip_persistence_frames}f "
        f"rate_limit={ap.rate_limit_s}s "
        f"silence={ap.silence_window_s}s "
        f"pause_tol={ap.pause_tolerance_s}s"
    )
    return "\n".join(lines)


def validate_path(path: Path) -> tuple[bool, str]:
    try:
        plan = load_plan(path)
    except FileNotFoundError as exc:
        return False, f"[ERROR] {exc}"
    except yaml.YAMLError as exc:
        return False, f"[ERROR] YAML parse failed for {path}: {exc}"
    except ValidationError as exc:
        return False, f"[ERROR] Schema validation failed for {path}:\n{exc}"
    except ValueError as exc:
        return False, f"[ERROR] {exc}"
    return True, summarize(plan)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate-plan",
        description="Validate an experiment plan YAML against the schema.",
    )
    parser.add_argument(
        "plans",
        nargs="+",
        type=Path,
        help="One or more experiment_plan.yaml files.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print errors, not summaries.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    failures = 0
    for plan_path in args.plans:
        ok, message = validate_path(plan_path)
        if not ok:
            failures += 1
            print(message)
            print()
        elif not args.quiet:
            print(f"OK  {plan_path}")
            print(message)
            print()
    if failures:
        print(f"{failures} plan(s) failed validation.")
        return 1
    if not args.quiet:
        print("All plans valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
