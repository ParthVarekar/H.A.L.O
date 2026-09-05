"""Compatibility entry point for the React dashboard server."""

from __future__ import annotations

import sys

from bas_har.web.server import main as web_main


def main(argv: list[str] | None = None) -> int:
    return web_main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
