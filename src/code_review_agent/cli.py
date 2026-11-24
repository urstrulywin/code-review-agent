import asyncio
import logging

import httpx
import typer
from anthropic import AnthropicError
from pydantic import ValidationError

from code_review_agent.github_client import fetch_pull_request
from code_review_agent.reviewer import review_diff
from code_review_agent.settings import Settings

logger = logging.getLogger(__name__)

app = typer.Typer(
    help="Review a pull request.",
    no_args_is_help=True,
    invoke_without_command=False,
)


@app.command()
def review(
    repo: str = typer.Option(..., help="Repository in owner/name format."),
    pr: int = typer.Option(..., min=1, help="Pull request number."),
) -> None:
    """Run a review of a pull request."""
    try:
        settings = Settings()
    except ValidationError:
        typer.echo("Review failed during configuration.", err=True)
        raise typer.Exit(code=1) from None

    try:
        pull_request, changed_files = asyncio.run(fetch_pull_request(repo, pr))
    except (
        RuntimeError,
        TypeError,
        ValueError,
        httpx.HTTPError,
    ) as exc:
        typer.echo(
            f"Review failed during GitHub fetch ({type(exc).__name__}).",
            err=True
        )
        raise typer.Exit(code=1) from None

    try:
        findings = review_diff(
            settings=settings,
            pull_request=pull_request,
            changed_files=changed_files,
        )
    except (
        AnthropicError,
        ValidationError,
        RuntimeError,
        ValueError,
    ) as exc:
        message = str(exc)
        prefix = "Review schema mismatch: "
        if message.startswith(prefix):
            detail = message.removeprefix(prefix)
            typer.echo(
                f"Review failed during Claude review (schema mismatch: {detail}).",
                err=True,
            )
        else:
            typer.echo(
                f"Review failed during Claude review ({type(exc).__name__}).",
                err=True,
            )
        raise typer.Exit(code=1) from None

    if not findings:
        typer.echo(f"No findings for {repo} PR #{pr}.")
        return

    for finding in findings:
        typer.echo(
            f"{finding.severity.value.upper()} "
            f"{finding.file}:{finding.line} [{finding.category}]"
        )
        typer.echo(f"  {finding.explanation}")
        if finding.suggestion:
            typer.echo(f"  Suggestion: {finding.suggestion}")


def main() -> None:
    logging.basicConfig(
        level=logging.ERROR,
        format="%(levelname)s %(name)s: %(message)s",
    )
    app()
