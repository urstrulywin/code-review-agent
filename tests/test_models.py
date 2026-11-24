import pytest
from pydantic import ValidationError

from code_review_agent.models import Finding, Severity


def test_finding_accepts_valid_data() -> None:
    finding = Finding(
        file="src/auth.py",
        line=12,
        severity=Severity.HIGH,
        category="hardcoded-secret",
        explanation="A signing secret is embedded in the source.",
        suggestion="Load the secret from an environment variable.",
        confidence=0.95,
        agent="security",
    )

    assert finding.file == "src/auth.py"
    assert finding.severity == Severity.HIGH


def test_finding_rejects_line_zero() -> None:
    with pytest.raises(ValidationError):
        Finding(
            file="src/auth.py",
            line=0,
            severity=Severity.HIGH,
            category="hardcoded-secret",
            explanation="Invalid line number.",
            confidence=0.95,
            agent="security",
        )


def test_finding_rejects_confidence_above_one() -> None:
    with pytest.raises(ValidationError):
        Finding(
            file="src/auth.py",
            line=12,
            severity=Severity.HIGH,
            category="hardcoded-secret",
            explanation="Invalid confidence.",
            confidence=1.2,
            agent="security",
        )
