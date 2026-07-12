"""MCP SSE client end-to-end dispatch test."""
from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp.client.session import ClientSession  # noqa: E402
from mcp.client.sse import sse_client  # noqa: E402

# Remove Hermes PYTHONPATH entries so site-packages resolve to the project venv.
for bad in [p for p in sys.path if "hermes-agent" in p]:
    sys.path.remove(bad)
os.environ.pop("PYTHONPATH", None)

MCP_SSE_URL = "http://127.0.0.1:8081/sse"


async def main():
    async with sse_client(MCP_SSE_URL) as (
        read_stream,
        write_stream,
    ), ClientSession(read_stream, write_stream) as session:
        await session.initialize()

        # Test dispatch_task for a CVE-hunting intent
        result = await session.call_tool(
            "dispatch_task",
            {"intent": "hunt CVEs for apache", "payload": json.dumps({"simulate": True})},
        )
        print("dispatch_task result:")
        for content in result.content:
            if content.type == "text":
                data = json.loads(content.text)
                print(json.dumps(data, indent=2)[:800])


if __name__ == "__main__":
    asyncio.run(main())
