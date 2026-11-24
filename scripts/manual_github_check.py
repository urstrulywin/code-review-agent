import asyncio
import json
import os
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    if not os.getenv("GITHUB_TOKEN"):
        raise RuntimeError("Set GITHUB_TOKEN in this terminal first.")

    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "code_review_agent.github_mcp"],
        env=os.environ.copy(),
        errlog=sys.stderr,
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            pr = await session.call_tool(
                "get_pull_request",
                {"repo": "urstrulywin/github-assistant", "pr_number": 10},
            )
            diff = await session.call_tool(
                "get_diff",
                {"repo": "urstrulywin/github-assistant", "pr_number": 10},
            )

            print("Pull request:")
            print(json.dumps(pr.structured_content, indent=2))
            print("\nChanged files:")
            print(json.dumps(diff.structured_content, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
