"""MCP SSE end-to-end smoke tests."""
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


async def dispatch(session: ClientSession, intent: str) -> dict:
    result = await session.call_tool(
        "dispatch_task",
        {"intent": intent, "payload": json.dumps({"simulate": True})},
    )
    text = result.content[0].text
    return json.loads(text)


async def main():
    async with sse_client(MCP_SSE_URL) as (
        read,
        write,
    ), ClientSession(read, write) as session:
        await session.initialize()

        expectations = {
            "hunt CVEs for apache": ("T3MP3ST", "security"),
            "scan target.com for vulnerabilities": ("T3MP3ST", "security"),
            "spin up a stateful agent with long-term memory": ("letta_code", "agent_framework"),
            "screen resumes for python backend": ("hiring_agent", "agent_framework"),
            "make a cinematic video montage": ("openmontage", "content_media"),
            "generate an HTML landing page for my saas": ("html_anything", "content_media"),
        }

        passed = 0
        for intent, (expected_module, expected_category) in expectations.items():
            data = await dispatch(session, intent)
            actual_module = data.get("module")
            actual_category = data.get("category")
            ok = actual_module == expected_module and actual_category == expected_category
            status = "PASS" if ok else "FAIL"
            print(f"{status}: {intent!r}")
            print(f"       expected {expected_module}/{expected_category}, got {actual_module}/{actual_category}")
            if ok:
                passed += 1

        print(f"\n{passed}/{len(expectations)} MCP dispatch checks passed")
        if passed != len(expectations):
            raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
