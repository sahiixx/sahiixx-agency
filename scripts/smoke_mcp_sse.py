"""MCP SSE client smoke test."""
from __future__ import annotations

import asyncio
import os
import sys

from mcp.client.session import ClientSession  # noqa: E402
from mcp.client.sse import sse_client  # noqa: E402

# Remove Hermes PYTHONPATH entries so site-packages resolve to the project venv.
for bad in [p for p in sys.path if "hermes-agent" in p]:
    sys.path.remove(bad)
os.environ.pop("PYTHONPATH", None)


async def main():
    async with sse_client("http://127.0.0.1:8081/sse") as (
        read_stream,
        write_stream,
    ), ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        tools = await session.list_tools()
        print("tools:", [tool.name for tool in tools.tools])


if __name__ == "__main__":
    asyncio.run(main())
