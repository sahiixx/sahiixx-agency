from __future__ import annotations

import pytest

from sahiixx_agency.discovery.sources import fetch_github_velocity


@pytest.mark.asyncio
async def test_fetch_github_velocity_parses_search_results(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "items": [
                    {
                        "id": 1,
                        "full_name": "nexu-io/html-anything",
                        "html_url": "https://github.com/nexu-io/html-anything",
                        "description": "Generate HTML from prompts",
                        "stargazers_count": 1200,
                        "language": "TypeScript",
                        "created_at": "2026-06-01T00:00:00Z",
                        "updated_at": "2026-07-01T00:00:00Z",
                    }
                ]
            }

    class FakeClient:
        async def get(self, url, **kwargs):
            calls.append(url)
            return FakeResponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr("sahiixx_agency.discovery.sources.httpx.AsyncClient", lambda **kwargs: FakeClient())
    results = await fetch_github_velocity(languages=["python"])
    assert len(results) == 1
    assert results[0]["full_name"] == "nexu-io/html-anything"
    assert results[0]["stars"] == 1200
