"""CRC32-enveloped JSONL writer and verifier."""

from __future__ import annotations

import json
import zlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from halo.schema.event_schema import EventRecord
from halo.schema.io_schema import CrcJsonlEntry


class CrcJsonlWriter:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8", buffering=1)
        self._closed = False

    def write(self, payload: Mapping[str, Any]) -> CrcJsonlEntry:
        if self._closed:
            raise RuntimeError("CRC JSONL writer is closed")
        normalized = dict(payload)
        checksum = self.checksum(normalized)
        entry = CrcJsonlEntry(payload=normalized, crc32=checksum)
        self._handle.write(entry.model_dump_json() + "\n")
        self._handle.flush()
        return entry

    def close(self) -> None:
        if self._closed:
            return
        self._handle.close()
        self._closed = True

    def __enter__(self) -> CrcJsonlWriter:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @staticmethod
    def checksum(payload: Mapping[str, Any]) -> str:
        canonical = json.dumps(
            dict(payload),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
        return f"{zlib.crc32(canonical) & 0xFFFFFFFF:08x}"


class CrcJsonlVerifier:
    @staticmethod
    def verify(path: Path) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        with Path(path).open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    raise ValueError(f"empty JSONL line at {line_number}")
                try:
                    entry = CrcJsonlEntry.model_validate_json(line)
                except ValueError as exc:
                    raise ValueError(f"invalid CRC JSONL entry at line {line_number}") from exc
                expected = CrcJsonlWriter.checksum(entry.payload)
                if entry.crc32 != expected:
                    raise ValueError(f"CRC mismatch at line {line_number}")
                records.append(entry.payload)
        return records


class CrcJsonlEventSink:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._writer = CrcJsonlWriter(self.path)

    def write(self, record: EventRecord) -> None:
        self._writer.write(record.model_dump(mode="json"))

    def close(self) -> None:
        self._writer.close()

    def __enter__(self) -> CrcJsonlEventSink:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
