"""Pydantic models for the agency domain."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ModuleStatus(str, Enum):
    """Lifecycle status of an agency module."""

    DISCOVERED = "discovered"
    REGISTERED = "registered"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    EXPERIMENTAL = "experimental"


class TaskStatus(str, Enum):
    """Status of an agency task."""

    PENDING = "pending"
    ROUTING = "routing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RepoCategory(str, Enum):
    """Canonical categories for repos."""

    AGENT_FRAMEWORK = "agent_framework"
    VOICE_AI = "voice_ai"
    REAL_ESTATE = "real_estate"
    SECURITY = "security"
    MCP_TOOL = "mcp_tool"
    COOKBOOK = "cookbook"
    OS_PLATFORM = "os_platform"
    INFRASTRUCTURE = "infrastructure"
    CONTENT_MEDIA = "content_media"        # YouTube / media automation
    KNOWLEDGE = "knowledge"                # Obsidian / second brain
    CAREER = "career"                      # Job search / career agents
    FORK = "fork"
    UNCATEGORIZED = "uncategorized"


class RiskLevel(str, Enum):
    """Risk classification for a module or task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RoutingRule(BaseModel):
    """A config-driven routing rule: regex pattern -> target module key."""

    pattern: str = Field(..., description="Regex pattern matched against task intent")
    target: str = Field(..., description="Ecosystem key of the module to route to")


class RepoNode(BaseModel):
    """A repository registered as an agency module."""

    id: str = Field(..., description="Unique module ID, usually repo name")
    name: str = Field(..., description="Repository name")
    owner: str = Field(default="sahiixx")
    full_name: str = Field(..., description="owner/name")
    description: str | None = Field(default=None)
    url: str = Field(..., description="GitHub HTML URL")
    clone_url: str | None = Field(default=None)
    category: RepoCategory = Field(default=RepoCategory.UNCATEGORIZED)
    subcategories: list[str] = Field(default_factory=list)
    language: str | None = Field(default=None)
    languages: dict[str, int] = Field(default_factory=dict)
    stars: int = Field(default=0)
    forks: int = Field(default=0)
    is_fork: bool = Field(default=False)
    is_private: bool = Field(default=False)
    topics: list[str] = Field(default_factory=list)
    updated_at: datetime | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    pushed_at: datetime | None = Field(default=None)
    status: ModuleStatus = Field(default=ModuleStatus.DISCOVERED)
    capabilities: list[str] = Field(default_factory=list)
    manifest: dict[str, Any] = Field(default_factory=dict)
    adapter_config: dict[str, Any] = Field(default_factory=dict)
    local_path: str | None = Field(default=None)
    last_synced: datetime | None = Field(default=None)
    source: str = Field(default="registry")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)


class AgencyTask(BaseModel):
    """A unit of work dispatched through the agency."""

    id: str = Field(..., description="Unique task ID")
    intent: str = Field(..., description="Natural language intent or command")
    module_id: str | None = Field(default=None, description="Target module if pre-selected")
    category: RepoCategory | None = Field(default=None, description="Target category if pre-selected")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = Field(default=None)
    error: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    parent_id: str | None = Field(default=None)
    child_ids: list[str] = Field(default_factory=list)


class BusMessage(BaseModel):
    """Message on the agency message bus."""

    id: str
    topic: str
    sender: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str | None = Field(default=None)
    priority: int = Field(default=0)


class IntelReport(BaseModel):
    """GitHub intelligence scout report."""

    id: str
    report_type: Literal["trending", "velocity", "newborn", "hidden_gems", "custom"]
    repos: list[RepoNode] = Field(default_factory=list)
    summary: str = Field(default="")
    raw_queries: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DiscoveryConfig(BaseModel):
    """External discovery feed settings."""

    enabled: bool = Field(default=True)
    min_stars: int = Field(default=50)
    languages: list[str] = Field(
        default_factory=lambda: ["python", "typescript", "javascript", "go", "rust"]
    )
    subreddits: list[str] = Field(
        default_factory=lambda: ["MachineLearning", "webdev", "LocalLLaMA", "selfhosted"]
    )
    auto_clone: bool = Field(default=False)
    schedule: str = Field(default="0 6 * * *")


class ApprovalConfig(BaseModel):
    """Human-in-the-loop approval gate settings."""

    auto_approve_low_risk: bool = Field(default=True)
    require_approval_for: list[str] = Field(default_factory=lambda: ["high", "critical"])


class AgencyConfig(BaseModel):
    """Runtime configuration for the agency."""

    github_username: str = Field(default="sahiixx")
    github_token: str | None = Field(default=None)
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8080)
    dashboard_port: int = Field(default=3000)
    mcp_port: int = Field(default=8081)
    memory_backend: Literal["sqlite", "json"] = Field(default="sqlite")
    data_dir: str = Field(default="./data")
    auto_sync_interval_minutes: int = Field(default=60)
    log_level: str = Field(default="INFO")
    default_llm: str | None = Field(default=None)
    llm_api_key: str | None = Field(default=None)
    t3mp3st_approval_token: str | None = Field(
        default=None,
        description="Token required to authorize T3MP3ST full-arsenal mode.",
    )
    # Config-driven routing rules loaded from agency.yaml
    routing_rules: list[RoutingRule] = Field(
        default_factory=list,
        description="Ordered list of regex pattern -> module target routing rules",
    )
    # Ecosystem module registry loaded from agency.yaml
    ecosystem: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Named ecosystem modules with repo, url, role, bus_channel, etc.",
    )
    # Discovery feed defaults loaded from agency.yaml
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    # Approval gate settings loaded from agency.yaml
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig)


class DiscoveryResult(BaseModel):
    """A repo discovered from an external source."""

    full_name: str
    url: str
    description: str = ""
    stars: int = 0
    language: str = "Unknown"
    source: str = "discovery"
    category: RepoCategory = Field(default=RepoCategory.UNCATEGORIZED)
    risk_level: RiskLevel = RiskLevel.LOW
    entrypoint: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApprovalRequest(BaseModel):
    """A pending human approval for a risky task."""

    id: str
    task_id: str
    risk_level: RiskLevel
    reason: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_at: datetime | None = None
    approved_by: str | None = None
    status: str = "pending"  # pending, approved, rejected

