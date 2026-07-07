"""Pluggable LLM providers with unified cost tracking."""

from __future__ import annotations

import os
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

import httpx

from .memory import AgencyMemory
from .models import (
    AgencyTask,
    CostRecord,
    LLMCallRecord,
    LLMConfig,
    LLMMessage,
    LLMModelPricing,
    LLMProvider,
    LLMProviderConfig,
    LLMResponse,
    LLMUsage,
)

if TYPE_CHECKING:
    from .costs import CostLedger

# Known model pricing in USD per 1M tokens. Override via config.llm.pricing.
DEFAULT_PRICING: dict[str, LLMModelPricing] = {
    "gpt-4o": LLMModelPricing(input_per_1m_tokens=2.50, output_per_1m_tokens=10.00),
    "gpt-4o-mini": LLMModelPricing(input_per_1m_tokens=0.15, output_per_1m_tokens=0.60),
    "gpt-4-turbo": LLMModelPricing(input_per_1m_tokens=10.00, output_per_1m_tokens=30.00),
    "gpt-3.5-turbo": LLMModelPricing(input_per_1m_tokens=0.50, output_per_1m_tokens=1.50),
    "claude-3-5-sonnet": LLMModelPricing(input_per_1m_tokens=3.00, output_per_1m_tokens=15.00),
    "claude-3-5-sonnet-20241022": LLMModelPricing(input_per_1m_tokens=3.00, output_per_1m_tokens=15.00),
    "claude-3-opus": LLMModelPricing(input_per_1m_tokens=15.00, output_per_1m_tokens=75.00),
    "claude-3-opus-20240229": LLMModelPricing(input_per_1m_tokens=15.00, output_per_1m_tokens=75.00),
    "claude-3-haiku": LLMModelPricing(input_per_1m_tokens=0.25, output_per_1m_tokens=1.25),
    "claude-3-haiku-20240307": LLMModelPricing(input_per_1m_tokens=0.25, output_per_1m_tokens=1.25),
}

ENV_VAR_MAP: dict[str, str] = {
    LLMProvider.OPENAI.value: "OPENAI_API_KEY",
    LLMProvider.ANTHROPIC.value: "ANTHROPIC_API_KEY",
    LLMProvider.OPENROUTER.value: "OPENROUTER_API_KEY",
}

BASE_URL_MAP: dict[str, str] = {
    LLMProvider.OPENAI.value: "https://api.openai.com/v1",
    LLMProvider.ANTHROPIC.value: "https://api.anthropic.com/v1",
    LLMProvider.OPENROUTER.value: "https://openrouter.ai/api/v1",
    LLMProvider.OLLAMA.value: "http://localhost:11434",
}

DEFAULT_MODEL_MAP: dict[str, str] = {
    LLMProvider.OPENAI.value: "gpt-4o-mini",
    LLMProvider.ANTHROPIC.value: "claude-3-5-sonnet-20241022",
    LLMProvider.OPENROUTER.value: "openai/gpt-4o-mini",
    LLMProvider.OLLAMA.value: "llama3.1",
}


def _resolve_api_key(provider: str, config: LLMProviderConfig | None) -> str | None:
    """Return the API key for a provider from config or environment."""
    if config is not None and config.api_key:
        return config.api_key
    env_var = ENV_VAR_MAP.get(provider)
    if env_var:
        return os.environ.get(env_var) or None
    return None


def _resolve_base_url(provider: str, config: LLMProviderConfig | None) -> str:
    """Return the base URL for a provider from config or defaults."""
    if config is not None and config.base_url:
        return config.base_url
    default = BASE_URL_MAP.get(provider)
    if default:
        return default
    if provider == LLMProvider.GENERIC.value:
        return ""
    return BASE_URL_MAP[LLMProvider.OPENAI.value]


def _resolve_default_model(provider: str, config: LLMProviderConfig | None) -> str:
    """Return the default model for a provider."""
    if config is not None and config.default_model:
        return config.default_model
    return DEFAULT_MODEL_MAP.get(provider, "unknown")


def _normalise_model(model: str) -> str:
    """Strip common date suffixes and lower-case a model id for pricing lookup."""
    lower = model.lower().strip()
    return lower


def compute_cost(model: str, usage: LLMUsage, pricing_overrides: dict[str, LLMModelPricing]) -> float | None:
    """Compute the USD cost of a request using known or configured pricing."""
    key = _normalise_model(model)
    pricing = pricing_overrides.get(key) or DEFAULT_PRICING.get(key)
    if pricing is None:
        return None
    input_cost = usage.input_tokens * pricing.input_per_1m_tokens / 1_000_000
    output_cost = usage.output_tokens * pricing.output_per_1m_tokens / 1_000_000
    return round(input_cost + output_cost, 6)


class BaseLLMProvider(ABC):
    """Abstract LLM provider."""

    def __init__(self, name: str, api_key: str | None, base_url: str, default_model: str) -> None:
        self.name = name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: Sequence[LLMMessage],
        temperature: float,
        max_tokens: int | None,
    ) -> LLMResponse:
        """Send a chat completion request and return a normalised response."""

    async def _post(self, path: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Helper to POST JSON and parse the response."""
        merged_headers = {"Content-Type": "application/json"}
        if headers:
            merged_headers.update(headers)
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.base_url}{path}", json=payload, headers=merged_headers)
            resp.raise_for_status()
            return cast(dict[str, Any], resp.json())


class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI-compatible provider (OpenAI, OpenRouter, Generic)."""

    async def chat(
        self,
        model: str,
        messages: Sequence[LLMMessage],
        temperature: float,
        max_tokens: int | None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.name == LLMProvider.OPENROUTER.value:
            headers["HTTP-Referer"] = "https://github.com/sahiixx/sahiixx-agency"
            headers["X-Title"] = "One Person Agency"

        data = await self._post("/chat/completions", payload, headers)
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content") or ""
        usage_raw = data.get("usage") or {}
        usage = LLMUsage(
            input_tokens=usage_raw.get("prompt_tokens", 0),
            output_tokens=usage_raw.get("completion_tokens", 0),
            total_tokens=usage_raw.get("total_tokens", 0),
        )
        return LLMResponse(
            provider=self.name,
            model=model,
            content=content,
            usage=usage,
        )


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Messages API provider."""

    async def chat(
        self,
        model: str,
        messages: Sequence[LLMMessage],
        temperature: float,
        max_tokens: int | None,
    ) -> LLMResponse:
        # Anthropic requires max_tokens and separates system messages.
        system_message = ""
        chat_messages: list[dict[str, str]] = []
        for m in messages:
            if m.role == "system":
                system_message = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        payload: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens if max_tokens is not None else 4096,
        }
        if system_message:
            payload["system"] = system_message

        headers = {"x-api-key": self.api_key or "", "anthropic-version": "2023-06-01"}
        data = await self._post("/messages", payload, headers)
        content_blocks = data.get("content", [])
        content = ""
        if content_blocks:
            content = content_blocks[0].get("text", "")
        usage_raw = data.get("usage") or {}
        usage = LLMUsage(
            input_tokens=usage_raw.get("input_tokens", 0),
            output_tokens=usage_raw.get("output_tokens", 0),
            total_tokens=usage_raw.get("input_tokens", 0) + usage_raw.get("output_tokens", 0),
        )
        return LLMResponse(
            provider=self.name,
            model=model,
            content=content,
            usage=usage,
        )


class OllamaProvider(BaseLLMProvider):
    """Ollama local API provider."""

    async def chat(
        self,
        model: str,
        messages: Sequence[LLMMessage],
        temperature: float,
        max_tokens: int | None,
    ) -> LLMResponse:
        options: dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": options,
        }
        data = await self._post("/api/chat", payload)
        message = data.get("message", {})
        content = message.get("content") or ""
        input_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)
        usage = LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )
        return LLMResponse(
            provider=self.name,
            model=model,
            content=content,
            usage=usage,
        )


def create_provider(provider_name: str, config: LLMConfig | None) -> BaseLLMProvider:
    """Factory that builds a provider from configuration."""
    provider_name = provider_name.lower()
    provider_config: LLMProviderConfig | None = None
    if config is not None and config.providers:
        provider_config = config.providers.get(provider_name)

    api_key = _resolve_api_key(provider_name, provider_config)
    base_url = _resolve_base_url(provider_name, provider_config)
    default_model = _resolve_default_model(provider_name, provider_config)

    if provider_name == LLMProvider.ANTHROPIC.value:
        if not api_key:
            raise ValueError("Anthropic provider requires an API key (ANTHROPIC_API_KEY)")
        return AnthropicProvider(provider_name, api_key, base_url, default_model)

    if provider_name == LLMProvider.OLLAMA.value:
        return OllamaProvider(provider_name, None, base_url, default_model)

    if provider_name in {LLMProvider.OPENAI.value, LLMProvider.OPENROUTER.value, LLMProvider.GENERIC.value}:
        if provider_name == LLMProvider.GENERIC.value and not api_key:
            # Generic may be unauthenticated; do not enforce.
            pass
        elif not api_key and provider_name != LLMProvider.GENERIC.value:
            env_var = ENV_VAR_MAP.get(provider_name, "API_KEY")
            raise ValueError(f"{provider_name} provider requires an API key ({env_var})")
        return OpenAICompatibleProvider(provider_name, api_key, base_url, default_model)

    # Fallback: treat unknown provider as OpenAI-compatible.
    return OpenAICompatibleProvider(provider_name, api_key, base_url, default_model)


class LLMCostTracker:
    """Records and aggregates LLM usage through the agency memory store."""

    def __init__(self, memory: AgencyMemory, ledger: CostLedger | None = None) -> None:
        self.memory = memory
        self.ledger = ledger

    def record(
        self,
        response: LLMResponse,
        task: AgencyTask | None = None,
    ) -> LLMCallRecord:
        """Persist an LLM call record and optionally attribute its cost to a task."""
        record = LLMCallRecord(
            id=f"llm_{uuid.uuid4().hex[:12]}",
            provider=response.provider,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.total_tokens,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
            created_at=response.created_at,
        )
        self.memory.log_event("llm.call", record.model_dump(mode="json"))

        if self.ledger is not None:
            cost_record = CostRecord(
                tenant_id=task.tenant_id if task else None,
                project_id=task.project_id if task else None,
                task_id=task.id if task else None,
                category="llm",
                amount=response.cost_usd or 0.0,
                currency="USD",
                description=f"{response.provider}/{response.model} LLM call",
            )
            self.ledger.record(cost_record)

        return record

    def calls(
        self,
        provider: str | None = None,
        model: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 10_000,
    ) -> list[LLMCallRecord]:
        """Return recorded calls filtered by provider, model and time range."""
        events = self.memory.recent_events(topic="llm.call", limit=limit)
        records: list[LLMCallRecord] = []
        for event in events:
            payload = event.get("payload") or {}
            try:
                record = LLMCallRecord.model_validate(payload)
            except Exception:
                continue
            if provider and record.provider != provider:
                continue
            if model and record.model != model:
                continue
            if since and record.created_at < since:
                continue
            if until and record.created_at > until:
                continue
            records.append(record)
        return records

    def summary(
        self,
        provider: str | None = None,
        model: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> dict[str, Any]:
        """Aggregate cost and token usage for the selected filters."""
        records = self.calls(provider=provider, model=model, since=since, until=until)
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)
        total_tokens = sum(r.total_tokens for r in records)
        total_cost = sum(r.cost_usd for r in records if r.cost_usd is not None)
        unknown_cost = any(r.cost_usd is None for r in records)

        by_provider: dict[str, dict[str, Any]] = {}
        by_model: dict[str, dict[str, Any]] = {}
        for r in records:
            by_provider.setdefault(r.provider, {"calls": 0, "tokens": 0, "cost_usd": 0.0})
            by_provider[r.provider]["calls"] += 1
            by_provider[r.provider]["tokens"] += r.total_tokens
            if r.cost_usd is not None:
                by_provider[r.provider]["cost_usd"] += r.cost_usd

            by_model.setdefault(r.model, {"calls": 0, "tokens": 0, "cost_usd": 0.0})
            by_model[r.model]["calls"] += 1
            by_model[r.model]["tokens"] += r.total_tokens
            if r.cost_usd is not None:
                by_model[r.model]["cost_usd"] += r.cost_usd

        return {
            "total_calls": len(records),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "cost_estimated": unknown_cost,
            "by_provider": by_provider,
            "by_model": by_model,
            "calls": [r.model_dump(mode="json") for r in records[:500]],
        }


class LLMManager:
    """Unified interface to pluggable LLM providers with cost tracking."""

    def __init__(
        self,
        config: LLMConfig | None,
        memory: AgencyMemory,
        ledger: CostLedger | None = None,
    ) -> None:
        self.config = config or LLMConfig()
        self.memory = memory
        self.tracker = LLMCostTracker(memory, ledger=ledger)

    def _pricing_overrides(self) -> dict[str, LLMModelPricing]:
        return dict(self.config.pricing) if self.config.pricing else {}

    def list_providers(self) -> list[dict[str, Any]]:
        """Return metadata for all supported providers."""
        providers = []
        for provider in LLMProvider:
            provider_config = self.config.providers.get(provider.value) if self.config.providers else None
            default_model = _resolve_default_model(provider.value, provider_config)
            base_url = _resolve_base_url(provider.value, provider_config)
            env_var = ENV_VAR_MAP.get(provider.value)
            configured = bool(provider_config and provider_config.api_key)
            has_env = bool(env_var and os.environ.get(env_var))
            providers.append(
                {
                    "id": provider.value,
                    "name": provider.value.title(),
                    "default_model": default_model,
                    "base_url": base_url,
                    "env_var": env_var,
                    "ready": configured or has_env or provider == LLMProvider.OLLAMA or provider == LLMProvider.GENERIC,
                }
            )
        return providers

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        task: AgencyTask | None = None,
    ) -> LLMResponse:
        """Send a chat request to the configured provider and track cost."""
        provider_name = provider or self.config.default_provider.value
        provider_obj = create_provider(provider_name, self.config)
        chosen_model = model or _resolve_default_model(provider_name, self.config.providers.get(provider_name))

        start = time.perf_counter()
        response = await provider_obj.chat(
            model=chosen_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        response.latency_ms = round((time.perf_counter() - start) * 1000, 2)
        response.model = chosen_model
        response.cost_usd = compute_cost(chosen_model, response.usage, self._pricing_overrides())
        self.tracker.record(response, task=task)
        return response

    def cost_summary(
        self,
        provider: str | None = None,
        model: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> dict[str, Any]:
        """Return aggregated LLM usage and costs."""
        return self.tracker.summary(provider=provider, model=model, since=since, until=until)
