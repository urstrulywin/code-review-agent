import os
import re
from typing import Any, TypedDict
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
import httpx
from mcp.server.mcpserver import Context, MCPServer

from dotenv import load_dotenv

load_dotenv()

_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class AppContext(TypedDict):
    github: httpx.AsyncClient


@asynccontextmanager
async def server_lifespan(
    server: MCPServer,
) -> AsyncGenerator[AppContext, None]:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required to start the GitHub MCP server.")

    async with httpx.AsyncClient(
        base_url="https://api.github.com",
        timeout=20.0,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    ) as client:
        yield {"github": client}


def create_server(
    transport: httpx.AsyncBaseTransport | None = None,
) -> MCPServer:
    instance = MCPServer(
        name="github-readonly",
        version="0.1.0",
        instructions=(
            "Read-only GitHub pull request tools. "
            "These tools cannot modify repositories or pull requests."
        ),
        lifespan=server_lifespan,
    )
    instance._github_transport = transport
    register_tools(instance)
    return instance


def register_tools(instance: MCPServer) -> None:
    """Register read-only GitHub tools on an MCP server."""

    @instance.tool()
    async def get_pull_request(
        repo: str,
        pr_number: int,
        ctx: Context,
    ) -> dict[str, Any]:
        """Get basic metadata for a GitHub pull request."""
        validate_pr_args(repo, pr_number)

        client: httpx.AsyncClient = ctx.request_context.lifespan_context["github"]
        data = await github_get(
            client,
            f"/repos/{repo}/pulls/{pr_number}",
        )

        return {
            "repo": repo,
            "number": data["number"],
            "title": data["title"],
            "body": data["body"] or "",
            "author": data["user"]["login"],
            "state": data["state"],
            "draft": data["draft"],
            "html_url": data["html_url"],
            "base_ref": data["base"]["ref"],
            "head_ref": data["head"]["ref"],
            "head_sha": data["head"]["sha"],
        }

    @instance.tool()
    async def get_diff(
        repo: str,
        pr_number: int,
        ctx: Context,
    ) -> list[dict[str, Any]]:
        """Get changed file names, change counts, and patches."""
        validate_pr_args(repo, pr_number)

        client: httpx.AsyncClient = ctx.request_context.lifespan_context["github"]
        data = await github_get(
            client,
            f"/repos/{repo}/pulls/{pr_number}/files?per_page=100",
        )

        return [
            {
                "file": item["filename"],
                "status": item["status"],
                "additions": item["additions"],
                "deletions": item["deletions"],
                "patch": item.get("patch"),
            }
            for item in data
        ]


def validate_pr_args(repo: str, pr_number: int) -> None:
    if not _REPO_PATTERN.fullmatch(repo):
        raise ValueError("repo must use owner/name format.")
    if pr_number < 1:
        raise ValueError("pr_number must be positive.")


async def github_get(
    client: httpx.AsyncClient,
    path: str,
) -> Any:
    response = await client.get(path)
    response.raise_for_status()
    return response.json()


server = create_server()


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
