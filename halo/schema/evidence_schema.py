"""Pydantic contracts for the signed, hash-chained event log and the downlink report."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints

from bas_har.schema.plan_schema import StrictModel

SIGNED_LOG_FORMAT = "bas-har-signed-log/1"
DOWNLINK_FORMAT = "bas-har-downlink/1"

Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
KeyId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{16}$")]


class SignedLogHeader(StrictModel):
    kind: Literal["header"] = "header"
    format: Literal["bas-har-signed-log/1"] = SIGNED_LOG_FORMAT
    exp_id: str = Field(min_length=1)
    plan_sha256: Sha256Hex
    public_key: str = Field(min_length=40, description="Raw Ed25519 public key, base64.")
    key_id: KeyId
    created_utc: datetime


class SignedLogLine(StrictModel):
    seq: int = Field(ge=0)
    payload: dict[str, Any]
    prev: Sha256Hex
    hash: Sha256Hex
    sig: str = Field(min_length=80, description="Ed25519 signature of the hash, base64.")


class SignedLogReport(StrictModel):
    ok: bool
    path: str
    lines: int = Field(ge=0)
    events: int = Field(ge=0)
    exp_id: str | None = None
    key_id: str | None = None
    trusted_key: bool | None = Field(
        default=None,
        description="True when the log was signed by the expected station key, None when no key was given.",
    )
    final_hash: str | None = None
    error_line: int | None = None
    error: str | None = None


class DownlinkStep(StrictModel):
    id: str
    status: Literal["completed", "skipped", "missed"]
    t_s: float | None = Field(
        default=None, description="Seconds into the session when it completed."
    )
    late: bool = False


class DownlinkAlert(StrictModel):
    code: str
    step: str
    t_s: float | None = None


class DownlinkReport(StrictModel):
    format: Literal["bas-har-downlink/1"] = DOWNLINK_FORMAT
    exp_id: str
    plan_sha256: Sha256Hex
    key_id: KeyId
    started_utc: datetime | None = None
    ended_utc: datetime
    steps: list[DownlinkStep]
    alerts: list[DownlinkAlert] = Field(default_factory=list)
    event_count: int = Field(ge=0)
    log_final_hash: Sha256Hex
    source_bytes: int | None = Field(
        default=None, ge=0, description="Size of the video this report summarises."
    )
    sig: str = Field(default="", description="Ed25519 signature over every other field, base64.")


class DownlinkVerification(StrictModel):
    ok: bool
    report_bytes: int = Field(ge=0)
    key_id: str | None = None
    trusted_key: bool | None = None
    matches_log: bool | None = Field(
        default=None, description="True when the report seals the given log's final hash and count."
    )
    error: str | None = None
