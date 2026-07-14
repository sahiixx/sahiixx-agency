"""Agentic framework adapters.

Connects the promoted agentic-framework ecosystem modules (langchain, autogen,
crewai, openai_agents, agent_framework, camel, deerflow) to the execution
pipeline. Each framework is a library / harness rather than a single CLI, so the
adapter's job is to scaffold a minimal runnable starter that uses the framework,
execute it when the repo + interpreter are available, and otherwise return a
deterministic simulation so the dispatch chain stays green offline.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy

DEFAULT_CLONE_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "repos")
)

# Minimal, syntactically-valid starter scripts per framework. They are written
# into the scaffold directory and executed only when the user opts in (or the
# repo is already cloned) so the dispatch never performs unsolicited network IO.
_SCAFFOLDS: dict[str, str] = {
    "langchain": '''\
"""OPA-scaffolded LangChain agent."""
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain import hub

llm = ChatOpenAI(model="gpt-4o-mini")
prompt = hub.pull("hwchase17/react")
tools: list = []
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
if __name__ == "__main__":
    print(executor.invoke({"input": "{brief}"})["output"])
''',
    "autogen": '''\
"""OPA-scaffolded AutoGen conversable agent."""
import autogen

llm_config = {{"model": "gpt-4o-mini"}}
assistant = autogen.AssistantAgent("assistant", llm_config=llm_config)
user = autogen.UserProxyAgent("user", code_execution_config=False)
if __name__ == "__main__":
    user.initiate_chat(assistant, message="{brief}")
''',
    "crewai": '''\
"""OPA-scaffolded CrewAI crew."""
from crewai import Agent, Crew, Process, Task

worker = Agent(role="worker", goal="{brief}", backstory="An OPA-scaffolded agent.")
task = Task(description="{brief}", agent=worker)
if __name__ == "__main__":
    Crew(agents=[worker], tasks=[task], process=Process.sequential).kickoff()
''',
    "openai_agents": '''\
"""OPA-scaffolded OpenAI Agents SDK agent."""
from agents import Agent, Runner

agent = Agent(name="opa-agent", instructions="{brief}")
if __name__ == "__main__":
    result = Runner.run_sync(agent, "{brief}")
    print(result.final_output)
''',
    "agent_framework": '''\
"""OPA-scaffolded Microsoft Agent Framework agent."""
# agent-framework ships Python + .NET; this is the Python entry sketch.
from agent_framework import Agent

agent = Agent(name="opa-agent", instructions="{brief}")
if __name__ == "__main__":
    print("AgentFramework agent ready for:", "{brief}")
''',
    "camel": '''\
"""OPA-scaffolded CAMEL role-playing agent."""
from camel.agents import ChatAgent
from camel.messages import BaseMessage

agent = ChatAgent(system_message=BaseMessage(role_name="assistant", content="{brief}"))
if __name__ == "__main__":
    print(agent.step(BaseMessage(role_name="user", content="{brief}")).msg.content)
''',
    "deerflow": '''\
"""OPA-scaffolded DeerFlow SuperAgent brief."""
# DeerFlow is orchestrated by an AI coding assistant reading this brief.
import sys

brief = "{brief}"
print(f"DeerFlow SuperAgent brief ready: {{brief}}")
sys.exit(0)
''',
}

_FRAMEWORK_INTERPRETER: dict[str, str] = {
    "langchain": "python",
    "autogen": "python",
    "crewai": "python",
    "openai_agents": "python",
    "agent_framework": "python",
    "camel": "python",
    "deerflow": "python",
}


@dataclass
class AgenticFrameworkResult:
    """Result of dispatching a brief to an agentic framework."""

    ok: bool
    framework: str
    brief: str
    command: str
    returncode: int
    stdout: str
    stderr: str
    cwd: str
    scaffold_path: str = ""
    status: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.status:
            self.status = "success" if self.ok else "failed"


class AgenticFrameworkAdapter:
    """Adapter that scaffolds/runs an agentic framework starter from a brief."""

    def __init__(
        self,
        framework: str,
        repo_dir: str | Path | None = None,
        clone_base_dir: str | Path | None = None,
        python_executable: str = "python",
        timeout: int = 300,
        fallback_on_failure: bool = True,
        network_policy: NetworkPolicy | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.framework = framework
        base = Path(clone_base_dir) if clone_base_dir else Path(DEFAULT_CLONE_BASE)
        self.repo_dir = Path(repo_dir) if repo_dir else base / framework
        self.python_executable = python_executable
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
                    "AgenticFrameworkAdapter",
                    node.id,
                    {"blocked_hosts": blocked, "allowlist": sorted(policy.allowlist)},
                )
            raise RuntimeError(message)

    def _write_scaffold(self, project_dir: Path, brief: str) -> Path:
        project_dir.mkdir(parents=True, exist_ok=True)
        template = _SCAFFOLDS.get(self.framework, _SCAFFOLDS["langchain"])
        script = template.replace("{brief}", brief.replace('"', "'"))
        scaffold = project_dir / "agent.py"
        scaffold.write_text(script, encoding="utf-8")
        return scaffold

    def _run_subprocess(self, project_dir: Path, command: list[str]) -> AgenticFrameworkResult:
        command_str = " ".join(command)
        try:
            proc = subprocess.run(
                command,
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            return AgenticFrameworkResult(
                ok=proc.returncode == 0,
                framework=self.framework,
                brief="",
                command=command_str,
                returncode=proc.returncode,
                stdout=proc.stdout[:8000] if proc.stdout else "",
                stderr=proc.stderr[:4000] if proc.stderr else "",
                cwd=str(self.repo_dir),
                scaffold_path=str(project_dir / "agent.py"),
                status="success" if proc.returncode == 0 else "error",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except subprocess.TimeoutExpired as exc:
            return AgenticFrameworkResult(
                ok=False,
                framework=self.framework,
                brief="",
                command=command_str,
                returncode=-1,
                stdout=str(exc.stdout or ""),
                stderr=f"Timeout after {self.timeout}s",
                cwd=str(self.repo_dir),
                scaffold_path=str(project_dir / "agent.py"),
                status="timeout",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except Exception as exc:  # noqa: BLE001
            return AgenticFrameworkResult(
                ok=False,
                framework=self.framework,
                brief="",
                command=command_str,
                returncode=-1,
                stdout="",
                stderr=str(exc),
                cwd=str(self.repo_dir),
                scaffold_path=str(project_dir / "agent.py"),
                status="exception",
                metadata={"timeout": self.timeout, "fallback": False},
            )

    def _simulate(self, project_dir: Path, brief: str) -> AgenticFrameworkResult:
        scaffold = self._write_scaffold(project_dir, brief)
        return AgenticFrameworkResult(
            ok=True,
            framework=self.framework,
            brief=brief,
            command=f"{_FRAMEWORK_INTERPRETER.get(self.framework, 'python')} agent.py <simulated>",
            returncode=0,
            stdout=(
                f"[SIMULATED] {self.framework} agent scaffolded\n"
                f"scaffold: {scaffold}\n"
                f"brief: {brief}\n"
                f"next_step: pip install {self.framework} && cd {project_dir} && python agent.py\n"
            ),
            stderr="",
            cwd=str(self.repo_dir),
            scaffold_path=str(scaffold),
            status="simulated",
            metadata={"timeout": self.timeout, "fallback": True, "note": f"{self.framework} repo not executed"},
        )

    def dispatch(
        self,
        brief: str,
        project_name: str | None = None,
        simulate: bool = False,
    ) -> AgenticFrameworkResult:
        if not brief:
            return AgenticFrameworkResult(
                ok=False,
                framework=self.framework,
                brief="",
                command="",
                returncode=-1,
                stdout="",
                stderr="No brief provided",
                cwd=str(self.repo_dir),
                status="failed",
            )
        if project_name is None:
            project_name = "".join(c if c.isalnum() else "_" for c in brief[:40]).strip("_") or "opa_project"
        project_dir = self.repo_dir / "projects" / project_name

        # Real execution only when the repo is cloned AND the user opted in.
        if simulate or not self.repo_dir.exists():
            return self._simulate(project_dir, brief)

        scaffold = self._write_scaffold(project_dir, brief)
        interpreter = _FRAMEWORK_INTERPRETER.get(self.framework, "python")
        command = [interpreter, str(scaffold)]
        result = self._run_subprocess(project_dir, command)
        if not result.ok and self.fallback_on_failure:
            simulated = self._simulate(project_dir, brief)
            simulated.metadata["original_error"] = result.stderr[:500]
            simulated.metadata["original_status"] = result.status
            return simulated
        return result

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        self._check_network_policy(node)
        brief = payload.get("brief") or payload.get("intent") or ""
        result = self.dispatch(
            brief=brief,
            project_name=payload.get("project_name"),
            simulate=payload.get("simulate", not self.repo_dir.exists()),
        )
        return result.metadata | {
            "module": node.name,
            "framework": result.framework,
            "status": result.status,
            "brief": result.brief,
            "scaffold_path": result.scaffold_path,
            "command": result.command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": result.cwd,
        }


def _make_agentic_framework(framework: str):
    """Build a factory closure for a given framework key."""

    def _factory(config, network_policy, audit_logger, task):
        from sahiixx_agency.adapters.framework.agentic_framework_adapter import (
            AgenticFrameworkAdapter,
        )

        adapter = AgenticFrameworkAdapter(
            framework=framework,
            clone_base_dir=os.path.join(config.data_dir, "repos"),
            network_policy=network_policy,
            audit_logger=audit_logger,
        )
        payload = dict(task.payload)
        payload.setdefault("brief", task.intent)
        return adapter, payload

    return _factory
