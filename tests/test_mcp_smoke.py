import os
import sys

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@pytest.mark.asyncio
async def test_server_exposes_read_only_tools() -> None:
    env = os.environ.copy()
    env["GITHUB_TOKEN"] = "test-token"

    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "code_review_agent.github_mcp"],
        env=env,
    )

    async with (
        stdio_client(server) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        result = await session.list_tools()

    tool_names = {tool.name for tool in result.tools}
    assert tool_names == {"get_pull_request", "get_diff"}
