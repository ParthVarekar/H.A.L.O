"""Pydantic contracts for the one-command reproduction check."""

from pydantic import Field

from bas_har.schema.plan_schema import StrictModel


class CheckResult(StrictModel):
    name: str = Field(min_length=1)
    ok: bool
    detail: str = ""


class SelfCheckReport(StrictModel):
    checks: list[CheckResult] = Field(default_factory=list)
    log_path: str | None = None
    downlink_path: str | None = None

    @property
    def ok(self) -> bool:
        return bool(self.checks) and all(check.ok for check in self.checks)
