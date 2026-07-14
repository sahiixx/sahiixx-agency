"""Ollama adapter.

Connects the promoted ``ollama`` ecosystem module (local LLM runtime) to the
execution pipeline. Scaffolds and runs ``ollama run <model>`` / ``ollama pull``
when the daemon is reachable, otherwise returns a deterministic simulation so
the dispatch chain stays green offline.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"


@dataclass
class OllamaResult:
    ok: bool
    brief: str
    model: str
    command: str
    returncode: int
    stdout: str
    stderr: str
    cwd: str
    status: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.status:
            self.status = "success" if self.ok else "failed"


class OllamaAdapter:
    """Adapter that runs a local LLM via Ollama from a brief."""

    def __init__(
        self,
        host: str = DEFAULT_OLLAMA_HOST,
        timeout: int = 300,
        fallback_on_failure: bool = True,
        network_policy: NetworkPolicy | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.host = host
        self.timeout = timeout
        self.fallback_on_failure = fallback_on_failure
        self.network_policy = network_policy
        self.audit_logger = audit_logger

    def _check_network_policy(self, node: RepoNode) -> None:
        policy = self.network_policy
        if policy is None or policy.allow_all:
            return
        hosts = node.external_hosts or []
        if not hosts:
            return
        blocked = [host for host in hosts if not policy.is_allowed(host)]
        if blocked:
            message = (
                f"Network policy blocks outbound hosts for module {node.full_name}: "
                f"{', '.join(blocked)}"
            )
            if self.audit_logger is not None:
                self.audit_logger.log(
                    "network_policy_violation",
                    "OllamaAdapter",
                    node.id,
                    {"blocked_hosts": blocked, "allowlist": sorted(policy.allowlist)},
                )
            raise RuntimeError(message)

    def _run_subprocess(self, command: list[str]) -> OllamaResult:
        command_str = " ".join(command)
        run_env = {**os.environ, "OLLAMA_HOST": self.host.replace("http://", "")}
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=run_env,
                check=False,
            )
            return OllamaResult(
                ok=proc.returncode == 0,
                brief="",
                model="",
                command=command_str,
                returncode=proc.returncode,
                stdout=proc.stdout[:8000] if proc.stdout else "",
                stderr=proc.stderr[:4000] if proc.stderr else "",
                cwd=os.getcwd(),
                status="success" if proc.returncode == 0 else "error",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except subprocess.TimeoutExpired as exc:
            return OllamaResult(
                ok=False, brief="", model="", command=command_str, returncode=-1,
                stdout=str(exc.stdout or ""), stderr=f"Timeout after {self.timeout}s",
                cwd=os.getcwd(), status="timeout",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except Exception as exc:  # noqa: BLE001
            return OllamaResult(
                ok=False, brief="", model="", command=command_str, returncode=-1,
                stdout="", stderr=str(exc), cwd=os.getcwd(), status="exception",
                metadata={"timeout": self.timeout, "fallback": False},
            )

    def _simulate(self, brief: str, model: str) -> OllamaResult:
        return OllamaResult(
            ok=True,
            brief=brief,
            model=model,
            command=f"ollama run {model} <simulated>",
            returncode=0,
            stdout=(
                f"[SIMULATED] Ollama local LLM run\n"
                f"model: {model}\n"
                f"prompt: {brief}\n"
                f"next_step: ollama pull {model} && ollama run {model} \"{brief}\"\n"
            ),
            stderr="",
            cwd=os.getcwd(),
            status="simulated",
            metadata={"timeout": self.timeout, "fallback": True, "note": "ollama not reachable"},
        )

    def dispatch(self, brief: str, model: str | None = None, project_name: str | None = None) -> OllamaResult:
        if not brief:
            return OllamaResult(
                ok=False, brief="", model="", command="", returncode=-1, stdout="",
                stderr="No brief provided", cwd=os.getcwd(), status="failed",
            )
        model = model or _infer_model(brief)
        if shutil.which("ollama") is None:
            return self._simulate(brief, model)

        # Prefer a non-interactive generation via the REST API.
        try:
            import httpx

            resp = httpx.post(
                f"{self.host}/api/generate",
                json={"model": model, "prompt": brief, "stream": False},
                timeout=self.timeout,
            )
            if resp.status_code < 300:
                return OllamaResult(
                    ok=True, brief=brief, model=model,
                    command=f"POST {self.host}/api/generate",
                    returncode=0, stdout=resp.json().get("response", "")[:8000],
                    stderr="", cwd=os.getcwd(), status="success",
                    metadata={"timeout": self.timeout, "fallback": False},
                )
        except Exception:  # noqa: BLE001
            pass

        result = self._run_subprocess(["ollama", "run", model, brief])
        if not result.ok and self.fallback_on_failure:
            simulated = self._simulate(brief, model)
            simulated.metadata["original_error"] = result.stderr[:500]
            return simulated
        return result

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        self._check_network_policy(node)
        brief = payload.get("brief") or payload.get("intent") or ""
        if payload.get("simulate"):
            model = payload.get("model") or _infer_model(brief)
            result = self._simulate(brief, model)
        else:
            result = self.dispatch(brief=brief, model=payload.get("model"), project_name=payload.get("project_name"))
        return result.metadata | {
            "module": node.name,
            "status": result.status,
            "brief": result.brief,
            "model": result.model,
            "command": result.command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": result.cwd,
        }


def _infer_model(text: str) -> str:
    lowered = text.lower()
    for key, model in (
        ("qwen", "qwen2.5"),
        ("llama", "llama3.1"),
        ("mistral", "mistral"),
        ("deepseek", "deepseek-coder"),
        ("gemma", "gemma2"),
    ):
        if key in lowered:
            return model
    return "llama3.1"


def _make_ollama(config, network_policy, audit_logger, task):
    from sahiixx_agency.adapters.model.ollama_adapter import OllamaAdapter

    adapter = OllamaAdapter(
        host=os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_HOST),
        network_policy=network_policy,
        audit_logger=audit_logger,
    )
    payload = dict(task.payload)
    payload.setdefault("brief", task.intent)
    return adapter, payload
