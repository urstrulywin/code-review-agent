from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Finding(BaseModel):
    file: str
    line: int = Field(ge=1)
    severity: Severity
    category: str
    explanation: str
    suggestion: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    agent: str
