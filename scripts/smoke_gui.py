"""Compatibility alias for the React dashboard smoke test."""

from __future__ import annotations

from scripts.smoke_web import main

if __name__ == "__main__":
    raise SystemExit(main())
