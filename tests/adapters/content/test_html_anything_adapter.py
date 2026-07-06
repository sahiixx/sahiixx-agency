"""Tests for the HTML-Anything adapter."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from sahiixx_agency.adapters.content.html_anything_adapter import HtmlAnythingAdapter


def test_adapter_finds_repo(tmp_path) -> None:
    repo = tmp_path / "html-anything"
    repo.mkdir()
    (repo / "package.json").write_text('{"name": "html-anything"}')
    adapter = HtmlAnythingAdapter(repo_dir=repo)
    assert adapter.repo_dir == repo


def test_install_reports_missing_repo(tmp_path) -> None:
    adapter = HtmlAnythingAdapter(repo_dir=tmp_path / "missing")
    result = adapter.install()
    assert result.ok is False
    assert "Repo not found" in result.stderr


def test_install_runs_pnpm_install(tmp_path) -> None:
    repo = tmp_path / "html-anything"
    repo.mkdir()
    (repo / "package.json").write_text('{"name": "html-anything"}')
    adapter = HtmlAnythingAdapter(repo_dir=repo)

    with patch.object(adapter, "_run", return_value=HtmlAnythingAdapter.__new__(HtmlAnythingAdapter)) as mock_run:
        # Configure the mock return value properly
        from sahiixx_agency.adapters.content.html_anything_adapter import HtmlAnythingResult
        mock_run.return_value = HtmlAnythingResult(ok=True, command="pnpm install", returncode=0, stdout="", stderr="")
        result = adapter.install()
        assert result.ok is True
        mock_run.assert_called_once_with(["pnpm", "install"])


def test_generate_returns_dev_url(tmp_path) -> None:
    repo = tmp_path / "html-anything"
    repo.mkdir()
    (repo / "package.json").write_text('{"name": "html-anything"}')
    adapter = HtmlAnythingAdapter(repo_dir=repo)

    from sahiixx_agency.adapters.content.html_anything_adapter import HtmlAnythingResult
    with patch.object(adapter, "_run", return_value=HtmlAnythingResult(ok=True, command="pnpm -F @html-anything/next dev", returncode=0, stdout="", stderr="")):
        result = adapter.generate("make a landing page")
        assert result.url == "http://localhost:3000"


@pytest.mark.asyncio
async def test_run_returns_result(tmp_path) -> None:
    from sahiixx_agency.core.models import RepoNode

    repo = tmp_path / "html-anything"
    repo.mkdir()
    (repo / "package.json").write_text('{"name": "html-anything"}')
    adapter = HtmlAnythingAdapter(repo_dir=repo)

    from sahiixx_agency.adapters.content.html_anything_adapter import HtmlAnythingResult
    with patch.object(adapter, "_run", return_value=HtmlAnythingResult(ok=True, command="pnpm install", returncode=0, stdout="", stderr="")):
        node = RepoNode(
            id="html_anything",
            name="html-anything",
            owner="nexu-io",
            full_name="nexu-io/html-anything",
            url="https://github.com/nexu-io/html-anything",
        )
        result = await adapter.run(node, {"prompt": "landing page"})
        assert result["module"] == "html-anything"
        assert result["url"] == "http://localhost:3000"
