"""Ed25519-signed, SHA-256 hash-chained JSONL event log and the signed downlink report.

Every line carries the hash of the line before it, so deleting, editing or reordering a line breaks
the chain; every hash is signed with the station key, so the chain cannot be rebuilt without it. The
downlink report seals the final hash and event count, which also makes a truncated log detectable.
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from pydantic import ValidationError

from bas_har.schema.event_schema import AlertCode, EventRecord, StepStatus
from bas_har.schema.evidence_schema import (
    DownlinkAlert,
    DownlinkReport,
    DownlinkStep,
    DownlinkVerification,
    SignedLogHeader,
    SignedLogLine,
    SignedLogReport,
)
from bas_har.schema.plan_schema import ExperimentPlan

GENESIS_HASH = "0" * 64
PRIVATE_KEY_NAME = "station_ed25519.pem"
PUBLIC_KEY_NAME = "station_ed25519.pub"


def canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(payload),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def chain_hash(prev: str, seq: int, payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    digest.update(f"{prev}\n{seq}\n".encode())
    digest.update(canonical_json(payload))
    return digest.hexdigest()


def plan_sha256(plan: ExperimentPlan) -> str:
    return hashlib.sha256(canonical_json(plan.model_dump(mode="json", by_alias=True))).hexdigest()


def key_id_for(public_key: bytes) -> str:
    return hashlib.sha256(public_key).hexdigest()[:16]


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _public_raw(key: Ed25519PublicKey) -> bytes:
    return key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


@dataclass(frozen=True, slots=True)
class StationKey:
    private_key: Ed25519PrivateKey

    @property
    def public_bytes(self) -> bytes:
        return _public_raw(self.private_key.public_key())

    @property
    def public_b64(self) -> str:
        return _b64(self.public_bytes)

    @property
    def key_id(self) -> str:
        return key_id_for(self.public_bytes)

    def sign(self, data: bytes) -> str:
        return _b64(self.private_key.sign(data))


def load_or_create_station_key(directory: Path) -> StationKey:
    """The station's signing key, created on first use; the public half is exported beside it."""
    directory.mkdir(parents=True, exist_ok=True)
    private_path = directory / PRIVATE_KEY_NAME
    if private_path.exists():
        loaded = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
        if not isinstance(loaded, Ed25519PrivateKey):
            raise ValueError(f"{private_path} is not an Ed25519 private key")
        key = StationKey(loaded)
    else:
        key = StationKey(Ed25519PrivateKey.generate())
        private_path.write_bytes(
            key.private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
    public_path = directory / PUBLIC_KEY_NAME
    if (
        not public_path.exists()
        or public_path.read_text(encoding="ascii").strip() != key.public_b64
    ):
        public_path.write_text(key.public_b64 + "\n", encoding="ascii")
    return key


def load_public_key(path: Path) -> bytes:
    return base64.b64decode(Path(path).read_text(encoding="ascii").strip(), validate=True)


def _verify_signature(public_key: bytes, signature_b64: str, data: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(base64.b64decode(signature_b64), data)
    except (InvalidSignature, ValueError):
        return False
    return True


class SignedJsonlWriter:
    def __init__(self, path: Path, key: StationKey, header: SignedLogHeader) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._key = key
        self._handle = self.path.open("x", encoding="utf-8", buffering=1)
        self._closed = False
        self.final_hash = GENESIS_HASH
        self.count = 0
        self.write(header.model_dump(mode="json"))

    def write(self, payload: Mapping[str, Any]) -> SignedLogLine:
        if self._closed:
            raise RuntimeError("signed log writer is closed")
        normalized = json.loads(canonical_json(payload))
        digest = chain_hash(self.final_hash, self.count, normalized)
        line = SignedLogLine(
            seq=self.count,
            payload=normalized,
            prev=self.final_hash,
            hash=digest,
            sig=self._key.sign(bytes.fromhex(digest)),
        )
        self._handle.write(line.model_dump_json() + "\n")
        self._handle.flush()
        self.final_hash = digest
        self.count += 1
        return line

    def close(self) -> None:
        if self._closed:
            return
        self._handle.close()
        self._closed = True


class SignedJsonlEventSink:
    """Event sink for the procedure engine that writes a signed chain and keeps the events."""

    def __init__(self, path: Path, key: StationKey, plan: ExperimentPlan) -> None:
        self.path = Path(path)
        self.plan = plan
        self.plan_hash = plan_sha256(plan)
        self.key = key
        self.started_utc = datetime.now(UTC)
        header = SignedLogHeader(
            exp_id=plan.experiment_id,
            plan_sha256=self.plan_hash,
            public_key=key.public_b64,
            key_id=key.key_id,
            created_utc=self.started_utc,
        )
        self._writer = SignedJsonlWriter(self.path, key, header)
        self.events: list[EventRecord] = []

    @property
    def final_hash(self) -> str:
        return self._writer.final_hash

    @property
    def line_count(self) -> int:
        return self._writer.count

    def write(self, record: EventRecord) -> None:
        self._writer.write(record.model_dump(mode="json"))
        self.events.append(record)

    def close(self) -> None:
        self._writer.close()


def verify_signed_log(path: Path, trusted_public_key: bytes | None = None) -> SignedLogReport:
    """Check every line's chain link, hash and signature; report the first line that fails."""
    path = Path(path)
    public_key: bytes | None = None
    header: SignedLogHeader | None = None
    prev = GENESIS_HASH
    count = 0

    def failed(line_number: int, reason: str) -> SignedLogReport:
        return SignedLogReport(
            ok=False,
            path=str(path),
            lines=count,
            events=max(0, count - 1),
            exp_id=header.exp_id if header else None,
            key_id=header.key_id if header else None,
            error_line=line_number,
            error=reason,
        )

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            try:
                line = SignedLogLine.model_validate_json(raw)
            except ValidationError:
                return failed(line_number, "line is not a signed log entry")
            if line.seq != count:
                return failed(line_number, f"sequence number {line.seq}, expected {count}")
            if line.prev != prev:
                return failed(line_number, "chain broken: previous hash does not match")
            if chain_hash(line.prev, line.seq, line.payload) != line.hash:
                return failed(line_number, "content changed: hash does not match")
            if count == 0:
                try:
                    header = SignedLogHeader.model_validate(line.payload)
                    public_key = base64.b64decode(header.public_key, validate=True)
                except (ValidationError, ValueError):
                    return failed(line_number, "first line is not a valid log header")
                if key_id_for(public_key) != header.key_id:
                    return failed(line_number, "header key id does not match its public key")
            assert public_key is not None
            if not _verify_signature(public_key, line.sig, bytes.fromhex(line.hash)):
                return failed(line_number, "signature is not valid")
            prev = line.hash
            count += 1
    if header is None or public_key is None:
        return failed(1, "log is empty")
    trusted = None if trusted_public_key is None else trusted_public_key == public_key
    return SignedLogReport(
        ok=trusted is not False,
        path=str(path),
        lines=count,
        events=count - 1,
        exp_id=header.exp_id,
        key_id=header.key_id,
        trusted_key=trusted,
        final_hash=prev,
        error=None if trusted is not False else "signed by a key that is not the station key",
    )


def _event_seconds(event: EventRecord, started: datetime) -> float:
    video_time = event.extra.get("video_time_s")
    if isinstance(video_time, int | float):
        return round(float(video_time), 2)
    return round((event.ts_utc - started).total_seconds(), 2)


def build_downlink(
    sink: SignedJsonlEventSink,
    key: StationKey,
    source_bytes: int | None = None,
) -> DownlinkReport:
    """A signed, kilobyte-scale summary of the session that seals the log's final hash."""
    completed: dict[str, float] = {}
    late: set[str] = set()
    skipped: set[str] = set()
    alerts: list[DownlinkAlert] = []
    for event in sink.events:
        if event.step_status == StepStatus.COMPLETED:
            completed.setdefault(event.step_id, _event_seconds(event, sink.started_utc))
            if event.extra.get("out_of_order"):
                late.add(event.step_id)
        elif event.step_status == StepStatus.SKIPPED:
            skipped.add(event.step_id)
        if event.alert_code is not None and event.alert_code != AlertCode.LOW_CONFIDENCE:
            alerts.append(
                DownlinkAlert(
                    code=event.alert_code.value,
                    step=event.step_id,
                    t_s=_event_seconds(event, sink.started_utc),
                )
            )
    steps = [
        DownlinkStep(
            id=step.id,
            status="completed"
            if step.id in completed
            else ("skipped" if step.id in skipped else "missed"),
            t_s=completed.get(step.id),
            late=step.id in late,
        )
        for step in sink.plan.steps
    ]
    report = DownlinkReport(
        exp_id=sink.plan.experiment_id,
        plan_sha256=sink.plan_hash,
        key_id=key.key_id,
        started_utc=sink.started_utc,
        ended_utc=datetime.now(UTC),
        steps=steps,
        alerts=alerts,
        event_count=sink.line_count - 1,
        log_final_hash=sink.final_hash,
        source_bytes=source_bytes,
    )
    report.sig = key.sign(_downlink_body(report))
    return report


def _downlink_body(report: DownlinkReport) -> bytes:
    return canonical_json(report.model_dump(mode="json", exclude={"sig"}))


def downlink_bytes(report: DownlinkReport) -> bytes:
    return report.model_dump_json(exclude_none=True).encode("utf-8")


def write_downlink(report: DownlinkReport, path: Path) -> int:
    data = downlink_bytes(report)
    Path(path).write_bytes(data)
    return len(data)


def verify_downlink(
    path: Path,
    public_key: bytes,
    log_path: Path | None = None,
) -> DownlinkVerification:
    """Check the report's signature and, when the log is given, that it seals that exact log."""
    data = Path(path).read_bytes()
    try:
        report = DownlinkReport.model_validate_json(data)
    except ValidationError:
        return DownlinkVerification(ok=False, report_bytes=len(data), error="not a downlink report")
    if key_id_for(public_key) != report.key_id:
        return DownlinkVerification(
            ok=False,
            report_bytes=len(data),
            key_id=report.key_id,
            trusted_key=False,
            error="report was signed by a different key",
        )
    if not _verify_signature(public_key, report.sig, _downlink_body(report)):
        return DownlinkVerification(
            ok=False,
            report_bytes=len(data),
            key_id=report.key_id,
            trusted_key=True,
            error="signature is not valid",
        )
    matches: bool | None = None
    if log_path is not None:
        log = verify_signed_log(log_path, public_key)
        matches = (
            log.ok and log.final_hash == report.log_final_hash and log.events == report.event_count
        )
        if not matches:
            return DownlinkVerification(
                ok=False,
                report_bytes=len(data),
                key_id=report.key_id,
                trusted_key=True,
                matches_log=False,
                error=log.error or "log does not match the sealed hash and event count",
            )
    return DownlinkVerification(
        ok=True,
        report_bytes=len(data),
        key_id=report.key_id,
        trusted_key=True,
        matches_log=matches,
    )
