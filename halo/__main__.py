"""Entry point for `python -m bas_har`.

Subcommands:
    verify           reproduce the reference ISS run and check its signed evidence
    verify-log       check a signed, hash-chained event log line by line
    verify-downlink  check a signed downlink report, optionally against its log
"""

from __future__ import annotations

import argparse
from pathlib import Path

from bas_har import __version__
from bas_har.config import keys_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bas-har",
        description="AI Human Activity Recognition for on-board BAS experiments (SIH26174).",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit.",
    )
    commands = parser.add_subparsers(dest="command")
    verify = commands.add_parser(
        "verify",
        help="Run the committed ISS take end to end and check steps, alerts and signatures.",
    )
    verify.add_argument("--device", default="auto", help="auto, cpu, cuda or cuda:0.")
    default_key = keys_dir() / "station_ed25519.pub"
    log = commands.add_parser("verify-log", help="Check a signed event log.")
    log.add_argument("log", type=Path)
    log.add_argument("--public-key", type=Path, default=default_key)
    downlink = commands.add_parser("verify-downlink", help="Check a signed downlink report.")
    downlink.add_argument("report", type=Path)
    downlink.add_argument("--log", type=Path, default=None, help="The event log it should seal.")
    downlink.add_argument("--public-key", type=Path, default=default_key)
    return parser


def _trusted_key(path: Path) -> bytes | None:
    from bas_har.io.signed_log import load_public_key

    return load_public_key(path) if path.is_file() else None


def _verify_log(log: Path, public_key: Path) -> int:
    from bas_har.io.signed_log import verify_signed_log

    report = verify_signed_log(log, _trusted_key(public_key))
    if report.ok:
        trust = {True: "station key", None: "key in the log header"}[report.trusted_key]
        print(
            f"VALID  {report.lines} lines, {report.events} events, signed by {trust} {report.key_id}"
        )
        print(f"       final hash {report.final_hash}")
        return 0
    where = f" at line {report.error_line}" if report.error_line else ""
    print(f"INVALID{where}: {report.error}")
    return 1


def _verify_downlink(report_path: Path, log: Path | None, public_key: Path) -> int:
    from bas_har.io.signed_log import verify_downlink

    key = _trusted_key(public_key)
    if key is None:
        print(f"INVALID: station public key not found at {public_key}")
        return 1
    result = verify_downlink(report_path, key, log)
    if result.ok:
        sealed = " and seals the given log" if result.matches_log else ""
        print(
            f"VALID  {result.report_bytes:,} bytes, signed by station key {result.key_id}{sealed}"
        )
        return 0
    print(f"INVALID: {result.error}")
    return 1


def _verify(device: str) -> int:
    from bas_har.selfcheck import format_report, run_selfcheck

    print("Reproducing the reference run: MELFI sample stowage, ESA Ignis mission footage.\n")
    report = run_selfcheck(device=device)
    print(format_report(report))
    return 0 if report.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.command == "verify":
        return _verify(args.device)
    if args.command == "verify-log":
        return _verify_log(args.log, args.public_key)
    if args.command == "verify-downlink":
        return _verify_downlink(args.report, args.log, args.public_key)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
