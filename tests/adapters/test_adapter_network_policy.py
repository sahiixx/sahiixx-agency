"""Tests that specialized adapters enforce the engine's network egress policy."""

from __future__ import annotations

import pytest

from sahiixx_agency.adapters.career.career_ops_adapter import CareerOpsAdapter
from sahiixx_agency.adapters.design.html_anything_adapter import HtmlAnythingAdapter
from sahiixx_agency.adapters.hiring.hiring_agent_adapter import HiringAgentAdapter
from sahiixx_agency.adapters.video.open_montage_adapter import OpenMontageAdapter
from sahiixx_agency.core.memory import AgencyMemory
from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy


@pytest.fixture
def restrictive_policy() -> NetworkPolicy:
    return NetworkPolicy(allowlist=["github.com"], default_allow=False)


@pytest.fixture
def audit_logger(tmp_path) -> AuditLogger:
    return AuditLogger(AgencyMemory(data_dir=str(tmp_path), backend="json"))


@pytest.mark.asyncio
async def test_career_ops_adapter_blocks_external_host(restrictive_policy, audit_logger):
    node = RepoNode(
        id="career-ops",
        name="career-ops",
        owner="sahiixx",
        full_name="sahiixx/career-ops",
        url="https://github.com/sahiixx/career-ops",
        external_hosts=["linkedin.com"],
    )
    adapter = CareerOpsAdapter(
        repo_dir="/nonexistent",
        network_policy=restrictive_policy,
        audit_logger=audit_logger,
    )
    with pytest.raises(RuntimeError, match="Network policy blocks"):
        await adapter.run(node, {"url": "https://example.com/jobs"})


@pytest.mark.asyncio
async def test_hiring_agent_adapter_blocks_external_host(restrictive_policy, audit_logger):
    node = RepoNode(
        id="hiring-agent",
        name="hiring-agent",
        owner="interviewstreet",
        full_name="interviewstreet/hiring-agent",
        url="https://github.com/interviewstreet/hiring-agent",
        external_hosts=["openai.com"],
    )
    adapter = HiringAgentAdapter(
        repo_dir="/nonexistent",
        network_policy=restrictive_policy,
        audit_logger=audit_logger,
    )
    with pytest.raises(RuntimeError, match="Network policy blocks"):
        await adapter.run(node, {"pdf_path": "/tmp/resume.pdf"})


@pytest.mark.asyncio
async def test_html_anything_adapter_blocks_external_host(restrictive_policy, audit_logger):
    node = RepoNode(
        id="html-anything",
        name="html-anything",
        owner="nexu-io",
        full_name="nexu-io/html-anything",
        url="https://github.com/nexu-io/html-anything",
        external_hosts=["vercel.com"],
    )
    adapter = HtmlAnythingAdapter(
        repo_dir="/nonexistent",
        network_policy=restrictive_policy,
        audit_logger=audit_logger,
    )
    with pytest.raises(RuntimeError, match="Network policy blocks"):
        await adapter.run(node, {"brief": "a landing page"})


@pytest.mark.asyncio
async def test_open_montage_adapter_blocks_external_host(restrictive_policy, audit_logger):
    node = RepoNode(
        id="openmontage",
        name="open-montage",
        owner="Open-Montage",
        full_name="Open-Montage/OpenMontage",
        url="https://github.com/Open-Montage/OpenMontage",
        external_hosts=["elevenlabs.io"],
    )
    adapter = OpenMontageAdapter(
        repo_dir="/nonexistent",
        network_policy=restrictive_policy,
        audit_logger=audit_logger,
    )
    with pytest.raises(RuntimeError, match="Network policy blocks"):
        await adapter.run(node, {"brief": "a video"})


@pytest.mark.asyncio
async def test_specialized_adapter_allows_host_in_allowlist(tmp_path):
    node = RepoNode(
        id="career-ops",
        name="career-ops",
        owner="sahiixx",
        full_name="sahiixx/career-ops",
        url="https://github.com/sahiixx/career-ops",
        external_hosts=["api.github.com"],
    )
    policy = NetworkPolicy(allowlist=["github.com"], default_allow=False)
    adapter = CareerOpsAdapter(
        repo_dir="/nonexistent",
        network_policy=policy,
    )
    result = await adapter.run(node, {"url": "https://example.com/jobs", "simulate": True})
    assert result["status"] == "simulated"


@pytest.mark.asyncio
async def test_specialized_adapter_blocked_host_logs_audit(tmp_path):
    node = RepoNode(
        id="career-ops",
        name="career-ops",
        owner="sahiixx",
        full_name="sahiixx/career-ops",
        url="https://github.com/sahiixx/career-ops",
        external_hosts=["evil.com"],
    )
    memory = AgencyMemory(data_dir=str(tmp_path), backend="json")
    audit = AuditLogger(memory)
    policy = NetworkPolicy(allowlist=["github.com"], default_allow=False)
    adapter = CareerOpsAdapter(
        repo_dir="/nonexistent",
        network_policy=policy,
        audit_logger=audit,
    )
    with pytest.raises(RuntimeError):
        await adapter.run(node, {"url": "https://example.com/jobs"})

    events = memory.recent_events(topic="audit")
    assert len(events) == 1
    assert events[0]["payload"]["action"] == "network_policy_violation"
    assert "evil.com" in events[0]["payload"]["details"]["blocked_hosts"]
