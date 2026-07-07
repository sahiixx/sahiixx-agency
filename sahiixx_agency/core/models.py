"""Pydantic models for the agency domain."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


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
    external_hosts: list[str] = Field(
        default_factory=list,
        description="Hostnames/IPs the module declares it will call outbound",
    )


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
    tenant_id: str | None = Field(default=None, description="Owning tenant for multi-tenancy")
    project_id: str | None = Field(default=None, description="Owning project for multi-tenancy")


class Tenant(BaseModel):
    """An agency tenant (customer/organization)."""

    id: str = Field(...)
    name: str = Field(...)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Project(BaseModel):
    """A project/workspace inside a tenant."""

    id: str = Field(...)
    tenant_id: str = Field(...)
    name: str = Field(...)
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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


class TelegramConfig(BaseModel):
    """Telegram bot integration settings."""

    enabled: bool = Field(default=False)
    token: str | None = Field(default=None, description="Telegram bot token")
    webhook_url: str | None = Field(default=None, description="Optional webhook URL for setWebhook")
    allowed_chat_ids: list[int] = Field(
        default_factory=list,
        description="If non-empty, only these chat IDs may interact with the bot",
    )
    poll_timeout: int = Field(default=30, description="Long-polling timeout in seconds")
    notify_on_approval: bool = Field(default=True, description="Send a message when approval is requested")


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    GENERIC = "generic"


class LLMMessage(BaseModel):
    """A single message for an LLM chat completion request."""

    role: Literal["system", "user", "assistant"] = Field(...)
    content: str = Field(...)


class LLMUsage(BaseModel):
    """Token usage returned by an LLM provider."""

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class LLMResponse(BaseModel):
    """Normalised response from any LLM provider."""

    provider: str
    model: str
    content: str
    usage: LLMUsage
    cost_usd: float | None = Field(default=None)
    latency_ms: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LLMModelPricing(BaseModel):
    """Per-model pricing in USD per 1M tokens."""

    input_per_1m_tokens: float = Field(..., ge=0)
    output_per_1m_tokens: float = Field(..., ge=0)


class LLMProviderConfig(BaseModel):
    """Provider-specific configuration and credentials."""

    api_key: str | None = Field(default=None)
    base_url: str | None = Field(default=None)
    default_model: str | None = Field(default=None)


class LLMConfig(BaseModel):
    """LLM abstraction configuration."""

    enabled: bool = Field(default=True)
    default_provider: LLMProvider = Field(default=LLMProvider.OPENAI)
    default_model: str | None = Field(default=None)
    providers: dict[str, LLMProviderConfig] = Field(default_factory=dict)
    pricing: dict[str, LLMModelPricing] = Field(default_factory=dict)


class SecurityConfig(BaseModel):
    """Security hardening settings."""

    network_allowlist: list[str] = Field(
        default_factory=list,
        description="Allowed outbound host suffixes for sandboxed execution",
    )
    network_blocklist: list[str] = Field(
        default_factory=list,
        description="Blocked outbound host suffixes",
    )
    audit_enabled: bool = Field(default=True)
    sanitize_input: bool = Field(default=True)
    dependency_scan_enabled: bool = Field(
        default=False,
        description="Enable dependency vulnerability scanning before repo execution",
    )


class DependencyScanReport(BaseModel):
    """Result of a dependency vulnerability scan."""

    passed: bool = Field(..., description="True when no known vulnerabilities were detected")
    failures: list[str] = Field(default_factory=list, description="Detected vulnerability messages")
    command: str | None = Field(default=None, description="CLI command that was attempted")
    stderr: str | None = Field(default=None, description="CLI stderr or fallback reason")


class WhiteLabelConfig(BaseModel):
    """Per-project white-label dashboard branding."""

    brand_name: str = Field(default="One Person Agency", alias="brandName")
    logo_url: str = Field(default="", alias="logoUrl")
    primary_color: str = Field(default="#6366f1", alias="primaryColor")
    favicon_url: str = Field(default="", alias="faviconUrl")

    model_config = {"populate_by_name": True}


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
    # Notification channel settings loaded from agency.yaml
    notifications: dict[str, Any] = Field(
        default_factory=dict,
        description="Notification channel configs: telegram, email, webhook",
    )
    # Workflow storage directory
    workflows_dir: str = Field(default="./data/workflows")
    # Metrics retention window in hours
    metrics_retention_hours: int = Field(default=24)
    # Telegram bot settings loaded from agency.yaml
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    # LLM provider settings loaded from agency.yaml
    llm: LLMConfig | None = Field(default=None)
    # Security hardening settings
    security: SecurityConfig = Field(default_factory=SecurityConfig)


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
    entrypoint: list[list[str]] | list[str] | None = None
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


class TaskLogEntry(BaseModel):
    """A single structured log entry for a task lifecycle event."""

    timestamp: datetime = Field(..., description="UTC ISO-8601 timestamp")
    level: LogLevel = Field(..., description="Standard Python logging level name")
    task_id: str = Field(..., description="Task this entry belongs to")
    actor: str = Field(default="system", description="Component that emitted the log")
    message: str = Field(..., description="Human-readable log message")
    extra: dict[str, Any] = Field(default_factory=dict, description="Structured context")


class CostRecord(BaseModel):
    """A single cost event attributed to a tenant/project/task."""

    id: str = Field(default_factory=lambda: f"cost_{uuid.uuid4().hex[:12]}")
    tenant_id: str | None = Field(default=None, description="Owning tenant")
    project_id: str | None = Field(default=None, description="Owning project")
    task_id: str | None = Field(default=None, description="Related agency task")
    category: str = Field(..., description="Cost category, e.g. llm or execution")
    amount: float = Field(..., ge=0, description="Cost amount in the specified currency")
    currency: str = Field(default="USD", description="Currency code")
    description: str = Field(default="", description="Human-readable description")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkflowStatus(str, Enum):
    """Status of a workflow instance."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStepStatus(str, Enum):
    """Status of an individual workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep(BaseModel):
    """A single step inside a workflow definition."""

    id: str = Field(..., description="Unique step id within the workflow")
    name: str = Field(..., description="Human readable step name")
    action: Literal["dispatch", "wait", "approve", "notify", "webhook", "condition", "noop"] = Field(
        default="noop",
        description="Step action type",
    )
    target: str | None = Field(default=None, description="Module id or category for dispatch steps")
    intent_template: str | None = Field(default=None, description="Intent template for dispatch steps")
    payload: dict[str, Any] = Field(default_factory=dict, description="Static payload merged at runtime")
    requires_approval: bool = Field(default=False, description="Pause for human approval before this step")
    next_on_success: str | None = Field(default=None, description="Next step id on success")
    next_on_failure: str | None = Field(default=None, description="Next step id on failure")
    condition: str | None = Field(default=None, description="Simple expression for condition steps")


class WorkflowDefinition(BaseModel):
    """A reusable workflow template."""

    id: str = Field(..., description="Unique workflow id")
    name: str = Field(..., description="Human readable name")
    description: str = Field(default="")
    trigger: Literal["manual", "schedule", "webhook", "event"] = Field(default="manual")
    schedule: str | None = Field(default=None, description="Cron expression for scheduled workflows")
    event_topic: str | None = Field(default=None, description="Bus topic that triggers this workflow")
    steps: list[WorkflowStep] = Field(default_factory=list)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkflowStepState(BaseModel):
    """Runtime state of a workflow step."""

    step_id: str
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    task_id: str | None = None


class WorkflowInstance(BaseModel):
    """A running or completed workflow execution."""

    id: str = Field(..., description="Unique instance id")
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: dict[str, Any] = Field(default_factory=dict, description="Runtime variables")
    step_states: list[WorkflowStepState] = Field(default_factory=list)
    current_step_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class NotificationChannel(str, Enum):
    """Supported notification channels."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SSE = "sse"
    CONSOLE = "console"


class Notification(BaseModel):
    """A single notification message."""

    id: str = Field(..., description="Unique notification id")
    channel: NotificationChannel
    title: str
    body: str
    recipient: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: datetime | None = None
    status: str = "pending"  # pending, sent, failed
    error: str | None = None


class MetricPoint(BaseModel):
    """A single metric observation."""

    name: str
    value: float
    labels: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck(BaseModel):
    """A single health check result."""

    name: str
    status: HealthStatus
    latency_ms: float = 0.0
    message: str = ""
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WebhookPayload(BaseModel):
    """Incoming webhook payload."""

    source: str
    event: str
    payload: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LLMCallRecord(BaseModel):
    """A single recorded LLM call for cost tracking."""

    id: str = Field(...)
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float | None = None
    latency_ms: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MessageRole(str, Enum):
    """Role of a chat message."""

    USER = "user"
    AGENCY = "agency"


class ChatMessage(BaseModel):
    """A single message within a chat thread."""

    id: str = Field(..., description="Unique message id")
    role: MessageRole = Field(..., description="Who sent the message")
    content: str = Field(..., description="Message text")
    task_id: str | None = Field(default=None, description="Related agency task, if any")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatThread(BaseModel):
    """A persisted conversation with the agency."""

    id: str = Field(..., description="Unique thread id")
    title: str | None = Field(default=None, description="Optional thread title")
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

