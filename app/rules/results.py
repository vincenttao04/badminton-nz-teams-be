from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.enums import Event


class Severity(StrEnum):
    """How serious a finding is. A block fails the check; a flag only warns."""

    BLOCK = "block"
    FLAG = "flag"


class Location(BaseModel):
    """Where in a lineup or list a finding applies. Both parts are optional so a
    finding can point at a whole event or at one position within it."""

    event: Event | None = None
    position: int | None = None


class Finding(BaseModel):
    """One problem the rules engine found, with how to fix it."""

    severity: Severity
    location: Location
    rule: str
    message: str
    how_to_fix: str


class ValidationResult(BaseModel):
    """The outcome of a check: the findings, and whether it passed."""

    ok: bool
    findings: list[Finding] = Field(default_factory=list)

    @classmethod
    def from_findings(cls, findings: list[Finding]) -> "ValidationResult":
        """Build a result, passing only when there are no blocking findings."""
        ok = not any(finding.severity == Severity.BLOCK for finding in findings)
        return cls(ok=ok, findings=findings)
