from types import SimpleNamespace
from unittest.mock import Mock

from code_review_agent.models import Finding, Severity
from code_review_agent.reviewer import ReviewOutput, review_diff
from code_review_agent.settings import Settings


def test_review_diff_returns_validated_findings(monkeypatch) -> None:
    finding = Finding(
        file="src/auth.py",
        line=12,
        severity=Severity.HIGH,
        category="security",
        explanation="Untrusted input is used without validation.",
        suggestion="Validate the input before use.",
        confidence=0.95,
        agent="claude-reviewer",
    )
    # parsed_output = SimpleNamespace(findings=[finding])
    # create = Mock(return_value=SimpleNamespace(parsed_output=parsed_output))
    # client = SimpleNamespace(messages=SimpleNamespace(parse=create))
    response = SimpleNamespace(
        stop_reason="end_turn",
        content=[
            SimpleNamespace(
                type="text",
                text=ReviewOutput(findings=[finding]).model_dump_json(),
            )
        ],
    )
    create = Mock(return_value=response)
    client = SimpleNamespace(messages=SimpleNamespace(create=create))

    monkeypatch.setattr("code_review_agent.reviewer.Anthropic", lambda **_: client)

    settings = Settings(
        anthropic_api_key="test-key",
        anthropic_base_url="https://example.invalid",
        anthropic_model="test-model",
    )

    result = review_diff(
        settings=settings,
        pull_request={"title": "Example PR"},
        changed_files=[{"file": "src/auth.py", "patch": "@@ -1 +12 @@"}],
    )

    assert result == [finding]
    kwargs = create.call_args.kwargs
    assert kwargs["model"] == "test-model"
    # assert kwargs["output_format"].__name__ == "ReviewOutput"
    assert "JSON" in kwargs["system"]
    assert kwargs["messages"][0]["role"] == "user"
    assert "Example PR" in kwargs["messages"][0]["content"]


def test_review_diff_rejects_oversized_input() -> None:
    settings = Settings(
        anthropic_api_key="test-key",
        anthropic_base_url="https://example.invalid",
        anthropic_model="test-model",
    )

    try:
        review_diff(
            settings=settings,
            pull_request={},
            changed_files=[{"patch": "x" * 200_001}],
        )
    except ValueError as exc:
        assert "200,000-character limit" in str(exc)
    else:
        raise AssertionError("Oversized review input should be rejected.")
