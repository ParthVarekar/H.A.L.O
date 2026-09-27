"""JSONL event sink for the procedure engine.

Append-only, flush-on-write so a crash never loses the most recent decision.
CRC-verified tail is computed in Phase 5; for now we keep it simple.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from halo.schema.event_schema import EventRecord


class JsonlEventSink:
    def __init__(self, path: Path, buffer_flush: bool = True) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        self._handle = self._tmp.open("a", encoding="utf-8", buffering=1 if buffer_flush else -1)
        self._finalised = False

    @property
    def path(self) -> Path:
        return self._path

    def write(self, record: EventRecord) -> None:
        self._handle.write(record.to_jsonl() + "\n")

    def close(self) -> None:
        if self._finalised:
            return
        self._handle.close()
        if self._tmp.exists():
            if self._path.exists():
                self._path.unlink()
            os.replace(self._tmp, self._path)
        self._finalised = True

    def __enter__(self) -> JsonlEventSink:
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def make_utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=(datetime.now().microsecond // 1000) * 1000)
