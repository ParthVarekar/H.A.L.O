"""Entry point for `python -m bas_har`.

Phase 0 placeholder: prints version and exits. Real pipeline composes in Phase 7.
"""

from __future__ import annotations

import argparse

from bas_har import __version__


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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
