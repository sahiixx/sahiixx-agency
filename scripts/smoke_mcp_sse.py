"""MCP SSE client smoke test."""
from __future__ import annotations

import asyncio
import json

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


async def main():
    async with sse_client("http://127.0.0.1:8081/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])
            result = await session.call_tool("agency_stats", {})
            print("agency_stats:", result.content[0].text[:200])


if __name__ == "__main__":
    asyncio.run(main())
