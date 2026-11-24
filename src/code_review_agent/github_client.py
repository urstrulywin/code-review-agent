import os
import sys
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.exceptions import MCPError


async def fetch_pull_request(
    repo: str,
    pr_number: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "code_review_agent.github_mcp"],
        env=os.environ.copy(),
    )

    async with (
        stdio_client(server) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        try:
            await session.initialize()
        except MCPError:
            raise RuntimeError("MCP initialization failed.") from None

        try:
            pr_result = await session.call_tool(
                "get_pull_request",
                {"repo": repo, "pr_number": pr_number},
            )
        except MCPError:
            raise RuntimeError("Pull request tool call failed.") from None

        try:
            diff_result = await session.call_tool(
                "get_diff",
                {"repo": repo, "pr_number": pr_number},
            )
        except MCPError:
            raise RuntimeError("Diff tool call failed.") from None

    if pr_result.is_error:
        raise RuntimeError("GitHub MCP failed to fetch pull request details.")
    if diff_result.is_error:
        raise RuntimeError("GitHub MCP failed to fetch the pull request diff.")

    pr_data = pr_result.structured_content
    diff_data = diff_result.structured_content

    if isinstance(pr_data, dict) and set(pr_data) == {"result"}:
        pr_data = pr_data["result"]
    if isinstance(diff_data, dict) and set(diff_data) == {"result"}:
        diff_data = diff_data["result"]

    if not isinstance(pr_data, dict):
        raise TypeError("GitHub MCP returned an invalid pull request payload.")
    if not isinstance(diff_data, list):
        raise TypeError("GitHub MCP returned an invalid diff payload.")

    return pr_data, diff_data