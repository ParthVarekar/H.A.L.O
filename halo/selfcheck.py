"""One-command reproduction check: every plan validates; the committed ISS take is followed end to
end with every step in order, no alerts, and a signed log and downlink that verify; and the same
footage with its first step cut out raises a skip alert."""

from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import ValidationError

from halo.config import activities_dir, experiments_dir, keys_dir
from halo.io.signed_log import (
    PUBLIC_KEY_NAME,
    load_public_key,
    verify_downlink,
    verify_signed_log,
)
from halo.schema.cli import load_plan
from halo.schema.selfcheck_schema import CheckResult, SelfCheckReport

REFERENCE_ACTIVITY = "cold_stowage_melfi"
REFERENCE_TAKE = "takes/slawosz_using_melfi-8821822197.mp4"
SKIP_CLIP = "verification/step1_removed.mp4"
SKIPPED_STEP = "step_01"


def plan_paths() -> list[Path]:
    return sorted(activities_dir().glob("*/plan.yaml")) + sorted(
        experiments_dir().glob("*/experiment_plan.yaml")
    )


def check_plans(paths: list[Path]) -> CheckResult:
    failures: list[str] = []
    for path in paths:
        try:
            load_plan(path)
        except (OSError, ValueError, ValidationError) as exc:
            failures.append(f"{path.parent.name}: {str(exc).splitlines()[0]}")
    if failures:
        return CheckResult(name="Experiment plans validate", ok=False, detail="; ".join(failures))
    return CheckResult(
        name="Experiment plans validate", ok=True, detail=f"{len(paths)} of {len(paths)}"
    )


def run_reference_session(
    activity_dir: Path,
    take: Path,
    device: str = "auto",
    timeout_s: float = 900.0,
) -> dict:
    """Run the take through the same session runner the dashboard uses and return its final status."""
    from halo.web.server import SessionRunner, WebState

    plan = load_plan(activity_dir / "plan.yaml")
    state = WebState(plan)
    state.prepare_for_capture(str(take))
    runner = SessionRunner(
        state,
        source=str(take),
        yolo_model=str(activity_dir / "models" / "detector.pt"),
        device=device,
        filter_default_classes=False,
        use_media_time=True,
        realtime=False,
        upload=True,
    )
    started = time.perf_counter()
    runner.start()
    runner.thread.join(timeout=timeout_s)
    if runner.is_alive():
        runner.stop()
        raise TimeoutError(f"reference session did not finish within {timeout_s:.0f} s")
    status = state.snapshot()
    status["elapsed_s"] = round(time.perf_counter() - started, 1)
    return status


def check_session(status: dict) -> list[CheckResult]:
    summary = status.get("summary") or {}
    if status.get("error"):
        return [CheckResult(name="Reference take runs", ok=False, detail=str(status["error"]))]
    total = int(summary.get("total_steps", 0))
    done = summary.get("completed_steps", [])
    in_order = not summary.get("out_of_order_steps") and not summary.get("skipped_steps")
    alerts = _alerts(status)
    return [
        CheckResult(
            name="Reference take runs",
            ok=bool(summary.get("source_finished")),
            detail=f"{status.get('device')} · {status.get('elapsed_s')} s",
        ),
        CheckResult(
            name="Every step recognised",
            ok=total > 0 and len(done) == total,
            detail=f"{len(done)} of {total}",
        ),
        CheckResult(name="Steps in the planned order", ok=in_order, detail="no skips, none late"),
        CheckResult(
            name="No false alerts",
            ok=not alerts,
            detail=f"{len(alerts)} alert{'s' if len(alerts) != 1 else ''}",
        ),
    ]


def check_evidence(status: dict) -> list[CheckResult]:
    downlink = status.get("downlink") or {}
    log_path = downlink.get("log_path")
    report_path = downlink.get("path")
    if not log_path or not report_path:
        return [CheckResult(name="Signed event log verifies", ok=False, detail="no log written")]
    public_key = load_public_key(keys_dir() / PUBLIC_KEY_NAME)
    log = verify_signed_log(Path(log_path), public_key)
    sealed = verify_downlink(Path(report_path), public_key, Path(log_path))
    ratio = downlink.get("ratio")
    return [
        CheckResult(
            name="Signed event log verifies",
            ok=log.ok,
            detail=log.error or f"{log.lines} lines · Ed25519 · key {log.key_id}",
        ),
        CheckResult(
            name="Downlink report seals the log",
            ok=sealed.ok,
            detail=sealed.error
            or f"{sealed.report_bytes:,} bytes"
            + (f" · {ratio:,}x smaller than the video" if ratio else ""),
        ),
    ]


def _alerts(status: dict) -> list[dict]:
    path = (status.get("downlink") or {}).get("path")
    if not path or not Path(path).is_file():
        return []
    return json.loads(Path(path).read_text(encoding="utf-8")).get("alerts", [])


def check_skip_caught(status: dict, step_id: str = SKIPPED_STEP) -> CheckResult:
    skips = [
        alert
        for alert in _alerts(status)
        if alert.get("code") == "SKIP_DETECTED" and alert.get("step") == step_id
    ]
    if not skips:
        return CheckResult(name="Removed step is caught", ok=False, detail="no skip alert")
    return CheckResult(
        name="Removed step is caught",
        ok=True,
        detail=f"skip alert {skips[0].get('t_s')} s into the clip with step 1 cut out",
    )


def run_selfcheck(device: str = "auto") -> SelfCheckReport:
    activity_dir = activities_dir() / REFERENCE_ACTIVITY
    report = SelfCheckReport(checks=[check_plans(plan_paths())])
    take = activity_dir / REFERENCE_TAKE
    if not take.is_file():
        report.checks.append(CheckResult(name="Reference take present", ok=False, detail=str(take)))
        return report
    try:
        status = run_reference_session(activity_dir, take, device=device)
    except (OSError, RuntimeError, TimeoutError) as exc:
        report.checks.append(CheckResult(name="Reference take runs", ok=False, detail=str(exc)))
        return report
    report.checks += check_session(status)
    report.checks += check_evidence(status)
    downlink = status.get("downlink") or {}
    report.log_path = downlink.get("log_path")
    report.downlink_path = downlink.get("path")
    clip = activity_dir / SKIP_CLIP
    if clip.is_file():
        try:
            report.checks.append(
                check_skip_caught(run_reference_session(activity_dir, clip, device=device))
            )
        except (OSError, RuntimeError, TimeoutError) as exc:
            report.checks.append(
                CheckResult(name="Removed step is caught", ok=False, detail=str(exc))
            )
    return report


def format_report(report: SelfCheckReport) -> str:
    width = max(len(check.name) for check in report.checks)
    lines = [
        f"  {'PASS' if check.ok else 'FAIL'}  {check.name.ljust(width)}  {check.detail}"
        for check in report.checks
    ]
    if report.log_path:
        lines.append(f"\n  Signed log:  {report.log_path}")
    if report.downlink_path:
        lines.append(f"  Downlink:    {report.downlink_path}")
    passed = sum(check.ok for check in report.checks)
    verdict = "ALL CHECKS PASSED" if report.ok else "SOME CHECKS FAILED"
    lines.append(f"\n  {verdict} ({passed}/{len(report.checks)})")
    return "\n".join(lines)
