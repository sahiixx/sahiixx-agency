"""Rich CLI for the One Person Agency."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import (
    AgencyConfig,
    LLMMessage,
    ModuleStatus,
    NotificationChannel,
    RepoCategory,
    TaskStatus,
    TelegramConfig,
    WorkflowDefinition,
    WorkflowInstance,
)

DISPATCH_POLL_INTERVAL_S = 0.5
DISPATCH_MAX_WAIT_S = 120
OUTPUT_PREVIEW_LIMIT = 2000
WORDS_ARGUMENT = typer.Argument(
    ...,
    help="Natural language words describing what the agency should do",
)

app = typer.Typer(
    name="opa",
    help="One Person Agency — Unified AI orchestration for all repos",
    rich_markup_mode="rich",
)
task_app = typer.Typer(
    name="task",
    help="Inspect and manage agency tasks",
    rich_markup_mode="rich",
)
llm_app = typer.Typer(
    name="llm",
    help="Pluggable LLM providers with cost tracking",
    rich_markup_mode="rich",
)
app.add_typer(task_app)
app.add_typer(llm_app)
console = Console()


def _load_config() -> AgencyConfig:
    config_path = os.environ.get("OPA_CONFIG", "./config/agency.yaml")
    if os.path.exists(config_path):
        import yaml

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        data.setdefault("t3mp3st_approval_token", os.environ.get("T3MP3ST_APPROVAL_TOKEN"))
        telegram_data = data.setdefault("telegram", {})
        if os.environ.get("TELEGRAM_BOT_TOKEN"):
            telegram_data["token"] = os.environ.get("TELEGRAM_BOT_TOKEN")
        if os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS"):
            chat_ids = [
                int(x.strip())
                for x in os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")
                if x.strip()
            ]
            telegram_data.setdefault("allowed_chat_ids", chat_ids)
        return AgencyConfig.model_validate(data)
    return AgencyConfig(
        github_token=os.environ.get("GITHUB_TOKEN"),
        github_username=os.environ.get("GITHUB_USER", "sahiixx"),
        t3mp3st_approval_token=os.environ.get("T3MP3ST_APPROVAL_TOKEN"),
        telegram=TelegramConfig(
            token=os.environ.get("TELEGRAM_BOT_TOKEN"),
            allowed_chat_ids=[
                int(x.strip())
                for x in os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")
                if x.strip()
            ],
        ),
    )


def get_engine() -> AgencyEngine:
    """Return a configured AgencyEngine instance."""
    return AgencyEngine(_load_config())


@app.command()
def sync(
    username: str = typer.Option("sahiixx", "--user", "-u", help="GitHub username to sync"),
) -> None:
    """Sync all GitHub repos into the agency registry."""
    engine = AgencyEngine(_load_config())
    with console.status("[bold green]Discovering repos..."):
        discovered = asyncio.run(engine.sync_repos(username))
    console.print(Panel(f"Synced [bold]{len(discovered)}[/bold] repos", title="Registry Sync", border_style="green"))


@app.command()
def registry(
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
    sort: str = typer.Option("stars", "--sort", "-s", help="Sort by: stars, updated, name"),
    top: int = typer.Option(20, "--top", "-n", help="Limit results"),
) -> None:
    """Show the agency module registry."""
    engine = AgencyEngine(_load_config())
    modules = engine.registry.modules
    if category:
        try:
            cat = RepoCategory(category)
            modules = [m for m in modules if m.category == cat]
        except ValueError:
            console.print(f"[red]Unknown category: {category}[/red]")
            raise typer.Exit(1) from None

    if sort == "stars":
        modules.sort(key=lambda m: m.stars, reverse=True)
    elif sort == "updated":
        modules.sort(key=lambda m: m.updated_at or "", reverse=True)
    else:
        modules.sort(key=lambda m: m.name)

    table = Table(title=f"Agency Modules ({len(modules)})", box=box.ROUNDED)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Category", style="magenta")
    table.add_column("Lang", style="yellow")
    table.add_column("Stars", justify="right", style="green")
    table.add_column("Forks", justify="right", style="blue")
    table.add_column("Status", style="white")

    for m in modules[:top]:
        status_color = {
            ModuleStatus.ACTIVE: "green",
            ModuleStatus.INACTIVE: "dim",
            ModuleStatus.ERROR: "red",
        }.get(m.status, "")
        status_text = Text(m.status.value, style=status_color)
        table.add_row(
            Text(m.name),
            Text(m.category.value),
            Text(m.language or "N/A"),
            Text(str(m.stars)),
            Text(str(m.forks)),
            status_text,
        )
    console.print(table)


async def _run_dispatch(
    engine: AgencyEngine,
    intent: str,
    data: dict[str, Any],
    *,
    no_wait: bool = False,
) -> None:
    """Shared dispatch implementation used by ``dispatch`` and ``do``."""
    await engine.start_worker()
    try:
        task = await engine.dispatch(intent, data)
        if no_wait:
            console.print(
                Panel(
                    f"Task [bold cyan]{task.id}[/bold cyan] dispatched\nStatus: [bold]{task.status.value}[/bold]",
                    title="Dispatched",
                    border_style="yellow",
                )
            )
            return

        terminal_statuses = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
        max_polls = int(DISPATCH_MAX_WAIT_S / DISPATCH_POLL_INTERVAL_S)
        with console.status(f"[bold yellow]Executing: {intent}"):
            for _ in range(max_polls):
                current = engine.get_task(task.id)
                if current is None:
                    break
                if current.status in terminal_statuses:
                    break
                await asyncio.sleep(DISPATCH_POLL_INTERVAL_S)

        final = engine.get_task(task.id)
        if final is None:
            console.print(f"[red]Task '{task.id}' disappeared during execution.[/red]")
            raise typer.Exit(1)
        border = "green" if final.status == TaskStatus.COMPLETED else "red"
        category_value = final.category.value if final.category else "N/A"
        if final.module_id:
            console.print(
                Panel(
                    f"Routed to [bold cyan]{final.module_id}[/bold cyan] ([italic]{category_value}[/italic])\n"
                    f"Status: [bold]{final.status.value}[/bold]\n"
                    f"Result: {json.dumps(final.result, indent=2, default=str)}",
                    title=f"Task {final.id}",
                    border_style=border,
                )
            )
        else:
            console.print(
                Panel(
                    f"No module matched. Category: {category_value}\n"
                    f"Status: [bold]{final.status.value}[/bold]\n"
                    f"Result: {json.dumps(final.result, indent=2, default=str)}",
                    title=f"Task {final.id}",
                    border_style="yellow",
                )
            )
    finally:
        await engine.stop_worker()


@app.command()
def dispatch(
    intent: str = typer.Argument(..., help="Natural language intent to dispatch"),
    payload: str = typer.Option("{}", "--payload", "-p", help="JSON payload string"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Return immediately with the pending task id"),
) -> None:
    """Dispatch a task through the agency."""
    try:
        data: dict[str, Any] = json.loads(payload)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON payload: {e}[/red]")
        raise typer.Exit(1) from e

    engine = AgencyEngine(_load_config())
    asyncio.run(_run_dispatch(engine, intent, data, no_wait=no_wait))


@app.command()
def do(
    words: list[str] = WORDS_ARGUMENT,
    payload: str = typer.Option("{}", "--payload", "-p", help="JSON payload string"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Return immediately with the pending task id"),
) -> None:
    """Natural-language shorthand for ``opa dispatch``.\n
    Example: ``opa do run voice assistant`` is equivalent to ``opa dispatch 'run voice assistant'``.
    """
    try:
        data: dict[str, Any] = json.loads(payload)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON payload: {e}[/red]")
        raise typer.Exit(1) from e

    intent = " ".join(words)
    engine = AgencyEngine(_load_config())
    asyncio.run(_run_dispatch(engine, intent, data, no_wait=no_wait))


@task_app.command("status")
def task_status(
    task_id: str = typer.Argument(..., help="Task id to look up"),
) -> None:
    """Show the current status of a dispatched task."""
    engine = AgencyEngine(_load_config())

    async def _run() -> None:
        await engine.start_worker()
        try:
            task = engine.get_task(task_id)
            if task is None:
                console.print(f"[red]Task '{task_id}' not found.[/red]")
                raise typer.Exit(1)

            result_preview = ""
            if task.result:
                result_preview = json.dumps(task.result, indent=2, default=str)[:OUTPUT_PREVIEW_LIMIT]
            error_preview = task.error or ""

            border_style = {
                TaskStatus.COMPLETED: "green",
                TaskStatus.FAILED: "red",
            }.get(task.status, "yellow")

            console.print(
                Panel(
                    f"Status: [bold]{task.status.value}[/bold]\n"
                    f"Created: {task.created_at}\n"
                    f"Started: {task.started_at or 'N/A'}\n"
                    f"Completed: {task.completed_at or 'N/A'}\n"
                    f"Module: {task.module_id or 'N/A'}\n"
                    f"Category: {task.category.value if task.category else 'N/A'}\n"
                    f"\n[bold]Result:[/bold]\n{result_preview}\n"
                    f"[bold]Error:[/bold]\n{error_preview}",
                    title=f"Task {task.id}",
                    border_style=border_style,
                )
            )
        finally:
            await engine.stop_worker()

    asyncio.run(_run())


@task_app.command("list")
def task_list(
    status: str = typer.Option(None, "--status", "-s", help="Filter by status: pending, running, completed, failed, cancelled"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum tasks to show"),
) -> None:
    """List recent agency tasks."""
    engine = AgencyEngine(_load_config())

    async def _run() -> None:
        await engine.start_worker()
        try:
            tasks = engine.list_tasks(limit=limit)
            if status:
                tasks = [t for t in tasks if t.status.value.lower() == status.lower()]
            tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)[:limit]

            if not tasks:
                console.print("[dim]No tasks found.[/dim]")
                return

            table = Table(title=f"Recent Tasks (last {limit})", box=box.ROUNDED)
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Status", style="bold")
            table.add_column("Module", style="magenta")
            table.add_column("Created", style="dim")
            table.add_column("Intent", style="green")

            status_colors = {
                TaskStatus.COMPLETED: "green",
                TaskStatus.FAILED: "red",
                TaskStatus.RUNNING: "blue",
                TaskStatus.PENDING: "yellow",
                TaskStatus.CANCELLED: "dim",
            }

            for task in tasks:
                color = status_colors.get(task.status, "white")
                table.add_row(
                    task.id[:12],
                    f"[{color}]{task.status.value}[/{color}]",
                    task.module_id or "—",
                    str(task.created_at)[:19] if task.created_at else "—",
                    (task.intent or "—")[:60],
                )
            console.print(table)
        finally:
            await engine.stop_worker()

    asyncio.run(_run())


@app.command()
def stats() -> None:
    """Show agency statistics."""
    engine = AgencyEngine(_load_config())
    s = engine.stats()
    reg = s["registry"]

    console.print(
        Panel(
            f"Modules: [bold]{reg['total_modules']}[/bold]\n"
            f"Active: [bold green]{reg['active']}[/bold green]\n"
            f"Total Stars: [bold yellow]{reg['total_stars']}[/bold yellow]\n"
            f"Memory Events: [bold blue]{s['memory_events']}[/bold blue]",
            title="Agency Stats",
            border_style="cyan",
        )
    )

    if reg["by_category"]:
        tree = Tree("[bold]Categories[/bold]")
        for cat, count in sorted(reg["by_category"].items(), key=lambda x: x[1], reverse=True):
            tree.add(f"{cat}: [bold]{count}[/bold]")
        console.print(tree)

    if reg["by_language"]:
        tree = Tree("[bold]Languages[/bold]")
        for lang, count in sorted(reg["by_language"].items(), key=lambda x: x[1], reverse=True)[:10]:
            tree.add(f"{lang or 'N/A'}: [bold]{count}[/bold]")
        console.print(tree)


@app.command()
def intel(
    report_type: str = typer.Option("trending", "--type", "-t", help="trending | velocity | hidden_gems"),
) -> None:
    """Run the GitHub intelligence scout."""
    engine = AgencyEngine(_load_config())
    with console.status(f"[bold blue]Running {report_type} scout..."):
        report = asyncio.run(engine.run_intel_scout(report_type))
    console.print(
        Panel(
            f"Found [bold]{len(report.repos)}[/bold] repos\nQueries: {', '.join(report.raw_queries)}",
            title=f"Intel Report: {report.id}",
            border_style="blue",
        )
    )
    table = Table(box=box.SIMPLE)
    table.add_column("Repo", style="cyan")
    table.add_column("Stars", justify="right")
    table.add_column("Language", style="yellow")
    table.add_column("Description")
    for r in report.repos[:15]:
        table.add_row(r.name, str(r.stars), r.language or "N/A", (r.description or "")[:60])
    console.print(table)


@app.command()
def telegram_career_bot(
    token: str = typer.Option(None, "--token", "-t", help="Telegram bot token (or TELEGRAM_BOT_TOKEN env var)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print commands instead of running them"),
    claude: bool = typer.Option(False, "--claude", help="Use Claude Code instead of the cops CLI"),
) -> None:
    """Start a Telegram bot that dispatches job URLs to Career-Ops."""
    from sahiixx_agency.adapters.career import run_bot

    try:
        run_bot(token=token, dry_run=dry_run, use_claude=claude)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def telegram_bot(
    token: str = typer.Option(None, "--token", "-t", help="Telegram bot token (or TELEGRAM_BOT_TOKEN env var)"),
) -> None:
    """Start the general agency Telegram bot (tasks, approvals, stats)."""
    from sahiixx_agency.telegram import run_bot

    try:
        run_bot(token=token, config=_load_config())
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(0, "--port", "-p", help="API port (default: config api_port or 8082)"),
    reload: bool = typer.Option(False, "--reload", "-r"),
) -> None:
    """Start the agency API server."""
    import uvicorn

    if not port:
        port = _load_config().api_port or 8082
    console.print(
        Panel(f"Starting API at [bold]http://{host}:{port}[/bold]", title="Agency Server", border_style="green")
    )
    uvicorn.run("sahiixx_agency.api.main:app", host=host, port=port, reload=reload)


@app.command()
def exec(
    module_id: str = typer.Argument(..., help="Module name or repo identifier"),
    payload: str = typer.Option("{}", "--payload", "-p", help="JSON payload string"),
    timeout: int = typer.Option(120, "--timeout", "-t", help="Execution timeout in seconds"),
) -> None:
    """Execute a module directly (clone, install, run)."""
    from sahiixx_agency.core.runner import CloneManager, RepoRunner

    engine = AgencyEngine(_load_config())
    module = engine.registry.get(module_id)
    if not module:
        console.print(f"[red]Module '{module_id}' not found in registry.[/red]")
        raise typer.Exit(1)

    try:
        data: dict[str, Any] = json.loads(payload)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON payload: {e}[/red]")
        raise typer.Exit(1) from e

    data.setdefault("timeout", timeout)

    with console.status(f"[bold green]Cloning & running {module_id}..."):
        runner = RepoRunner(CloneManager())
        result = asyncio.run(
            runner.run(module, command=data.get("command", "run"), env=data.get("env"), timeout=timeout)
        )

    status = "green" if result.get("status") == "success" else "red"
    inspection = result.get("inspection", {})
    console.print(
        Panel(
            f"Module: [bold]{module_id}[/bold]\n"
            f"Category: {module.category.value}\n"
            f"Entrypoint: {inspection.get('entrypoint', 'N/A')}\n"
            f"Type: {inspection.get('type', 'N/A')}\n"
            f"Return code: {result.get('returncode', 'N/A')}\n"
            f"Command: {result.get('command', 'N/A')}\n"
            f"\n[bold]stdout:[/bold]\n{result.get('stdout', 'N/A')[:OUTPUT_PREVIEW_LIMIT]}\n"
            f"[bold]stderr:[/bold]\n{result.get('stderr', 'N/A')[:OUTPUT_PREVIEW_LIMIT]}",
            title=f"Execution Result — {result.get('status', 'unknown')}",
            border_style=status,
        )
    )


# ---------- LLM Commands ----------


@llm_app.command("providers")
def llm_providers() -> None:
    """List configured LLM providers and their readiness."""
    engine = AgencyEngine(_load_config())
    providers = engine.llm_manager.list_providers()

    table = Table(title="LLM Providers", box=box.ROUNDED)
    table.add_column("Provider", style="cyan")
    table.add_column("Default Model", style="yellow")
    table.add_column("Env Var", style="white")
    table.add_column("Ready", justify="center")

    for p in providers:
        ready_text = Text("✓" if p["ready"] else "✗", style="green" if p["ready"] else "red")
        table.add_row(p["id"], p["default_model"], p["env_var"] or "-", ready_text)
    console.print(table)


@llm_app.command("chat")
def llm_chat(
    prompt: str = typer.Argument(..., help="User prompt to send to the LLM"),
    provider: str = typer.Option(None, "--provider", "-p", help="Provider id (openai, anthropic, ollama, openrouter)"),
    model: str = typer.Option(None, "--model", "-m", help="Model id"),
    system: str = typer.Option("You are a helpful assistant.", "--system", "-s", help="System message"),
    temperature: float = typer.Option(0.7, "--temperature", "-t", help="Sampling temperature", min=0.0, max=2.0),
    max_tokens: int = typer.Option(None, "--max-tokens", "-n", help="Maximum tokens to generate"),
    tenant_id: str = typer.Option(None, "--tenant", "-T", help="Tenant id for cost attribution"),
    project_id: str = typer.Option(None, "--project", "-P", help="Project id for cost attribution"),
) -> None:
    """Send a chat request through a pluggable LLM provider."""
    import uuid

    from sahiixx_agency.core.models import AgencyTask

    engine = AgencyEngine(_load_config())
    messages = [LLMMessage(role="system", content=system), LLMMessage(role="user", content=prompt)]

    task = AgencyTask(
        id=f"llm_chat_{uuid.uuid4().hex[:12]}",
        intent="Ad-hoc LLM chat",
        tenant_id=tenant_id,
        project_id=project_id,
    )

    async def _run() -> None:
        with console.status(f"[bold cyan]Asking {provider or 'default'}..."):
            response = await engine.llm_manager.chat(
                messages=messages,
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                task=task,
            )
        cost = f"${response.cost_usd:.6f}" if response.cost_usd is not None else "unknown"
        console.print(
            Panel(
                f"{response.content}\n\n"
                f"[dim]Provider:[/dim] {response.provider}  [dim]Model:[/dim] {response.model}\n"
                f"[dim]Tokens:[/dim] {response.usage.total_tokens} "
                f"([dim]in {response.usage.input_tokens}, out {response.usage.output_tokens}[/dim])  "
                f"[dim]Cost:[/dim] {cost}  [dim]Latency:[/dim] {response.latency_ms}ms",
                title="LLM Response",
                border_style="cyan",
            )
        )

    asyncio.run(_run())


@llm_app.command("costs")
def llm_costs(
    provider: str = typer.Option(None, "--provider", "-p", help="Filter by provider"),
    model: str = typer.Option(None, "--model", "-m", help="Filter by model"),
    days: int = typer.Option(7, "--days", "-d", help="Aggregate costs for the last N days"),
) -> None:
    """Show aggregated LLM usage and cost records."""
    from datetime import datetime, timedelta, timezone

    engine = AgencyEngine(_load_config())
    since = datetime.now(timezone.utc) - timedelta(days=days)
    summary = engine.llm_manager.cost_summary(provider=provider, model=model, since=since)

    console.print(
        Panel(
            f"Calls: [bold]{summary['total_calls']}[/bold]\n"
            f"Tokens: [bold]{summary['total_tokens']}[/bold] "
            f"([dim]in {summary['total_input_tokens']}, out {summary['total_output_tokens']}[/dim])\n"
            f"Total Cost: [bold]{'$' + str(summary['total_cost_usd']) if not summary['cost_estimated'] else '$' + str(summary['total_cost_usd']) + ' (partially estimated)'}[/bold]",
            title=f"LLM Costs (last {days}d)",
            border_style="green",
        )
    )

    if summary["by_provider"]:
        table = Table(title="By Provider", box=box.SIMPLE)
        table.add_column("Provider", style="cyan")
        table.add_column("Calls", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost", justify="right")
        for name, data in sorted(summary["by_provider"].items(), key=lambda x: x[1]["cost_usd"], reverse=True):
            table.add_row(name, str(data["calls"]), str(data["tokens"]), f"${data['cost_usd']:.6f}")
        console.print(table)

    if summary["by_model"]:
        table = Table(title="By Model", box=box.SIMPLE)
        table.add_column("Model", style="magenta")
        table.add_column("Calls", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost", justify="right")
        for name, data in sorted(summary["by_model"].items(), key=lambda x: x[1]["cost_usd"], reverse=True):
            table.add_row(name, str(data["calls"]), str(data["tokens"]), f"${data['cost_usd']:.6f}")
        console.print(table)


# ---------- Workflows ----------

workflow_app = typer.Typer(
    name="workflow",
    help="Manage agency workflows",
    rich_markup_mode="rich",
)
app.add_typer(workflow_app)


@workflow_app.command("list")
def workflow_list() -> None:
    """List workflow definitions."""
    engine = AgencyEngine(_load_config())
    workflows = engine.workflows.list_definitions()
    table = Table(title=f"Workflows ({len(workflows)})", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Trigger", style="yellow")
    table.add_column("Steps", justify="right")
    table.add_column("Enabled", style="white")
    for w in workflows:
        table.add_row(w.id, w.name, w.trigger, str(len(w.steps)), "yes" if w.enabled else "no")
    console.print(table)


@workflow_app.command("create")
def workflow_create(
    path: str = typer.Argument(..., help="Path to workflow JSON file"),
) -> None:
    """Create a workflow definition from a JSON file."""
    engine = AgencyEngine(_load_config())
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    definition = WorkflowDefinition.model_validate(data)
    engine.workflows.create_definition(definition)
    console.print(Panel(f"Created workflow [bold]{definition.id}[/bold]", title="Workflow", border_style="green"))


@workflow_app.command("run")
def workflow_run(
    workflow_id: str = typer.Argument(..., help="Workflow id to run"),
    context: str = typer.Option("{}", "--context", "-c", help="JSON context string"),
) -> None:
    """Run a workflow instance."""
    try:
        ctx: dict[str, Any] = json.loads(context)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON context: {e}[/red]")
        raise typer.Exit(1) from e

    engine = AgencyEngine(_load_config())

    async def _run() -> WorkflowInstance | None:
        await engine.start_worker()
        try:
            instance = engine.workflows.create_instance(workflow_id, ctx)
            if instance is None:
                return None
            return await engine.workflows.run_instance(instance.id, dispatch=engine.dispatch, notify=engine.notify)
        finally:
            await engine.stop_worker()

    result = asyncio.run(_run())
    if result is None:
        console.print(f"[red]Workflow '{workflow_id}' not found or disabled.[/red]")
        raise typer.Exit(1)
    console.print(
        Panel(
            f"Workflow [bold]{workflow_id}[/bold] finished with status [bold]{result.status.value}[/bold]",
            title=f"Instance {result.id}",
            border_style="green" if result.status.value == "completed" else "yellow",
        )
    )


@workflow_app.command("instances")
def workflow_instances(
    workflow_id: str = typer.Argument(..., help="Workflow id"),
    limit: int = typer.Option(20, "--limit", "-n"),
) -> None:
    """List recent workflow instances."""
    engine = AgencyEngine(_load_config())
    instances = engine.workflows.list_instances(workflow_id, limit=limit)
    table = Table(title=f"Instances ({len(instances)})", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Created", style="dim")
    for inst in instances:
        table.add_row(inst.id, inst.status.value, str(inst.created_at))
    console.print(table)


@workflow_app.command("resume")
def workflow_resume(
    instance_id: str = typer.Argument(..., help="Workflow instance id to resume"),
) -> None:
    """Resume a paused workflow instance."""
    engine = AgencyEngine(_load_config())

    async def _run() -> WorkflowInstance | None:
        await engine.start_worker()
        try:
            return await engine.workflows.resume_instance(instance_id, dispatch=engine.dispatch, notify=engine.notify)
        finally:
            await engine.stop_worker()

    result = asyncio.run(_run())
    if result is None:
        console.print(f"[red]Instance '{instance_id}' not found or not paused.[/red]")
        raise typer.Exit(1)
    console.print(
        Panel(
            f"Instance [bold]{instance_id}[/bold] resumed and finished with status [bold]{result.status.value}[/bold]",
            title="Workflow Resumed",
            border_style="green" if result.status.value == "completed" else "yellow",
        )
    )


# ---------- Notifications ----------

notify_app = typer.Typer(
    name="notify",
    help="Send agency notifications",
    rich_markup_mode="rich",
)
app.add_typer(notify_app)


@notify_app.command("send")
def notify_send(
    title: str = typer.Argument(..., help="Notification title"),
    body: str = typer.Argument(..., help="Notification body"),
    channel: str = typer.Option("sse", "--channel", "-c", help="Channel: sse, telegram, email, webhook"),
    recipient: str = typer.Option(None, "--recipient", "-r", help="Recipient override"),
) -> None:
    """Send a notification through the configured channel."""
    try:
        ch = NotificationChannel(channel)
    except ValueError:
        console.print(f"[red]Unknown channel: {channel}[/red]")
        raise typer.Exit(1) from None

    engine = AgencyEngine(_load_config())
    notification = asyncio.run(engine.notify(ch, title, body, recipient))
    console.print(
        Panel(
            f"Channel: [bold]{notification.channel.value}[/bold]\n"
            f"Status: [bold]{notification.status}[/bold]",
            title=f"Notification {notification.id}",
            border_style="green" if notification.status == "sent" else "yellow",
        )
    )


# ---------- Observability ----------


@app.command()
def costs(
    tenant_id: str | None = typer.Option(None, "--tenant", "-t", help="Filter by tenant id"),
    project_id: str | None = typer.Option(None, "--project", "-p", help="Filter by project id"),
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by cost category"),
    summary: bool = typer.Option(False, "--summary", "-s", help="Show aggregate summary instead of records"),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum records to show"),
) -> None:
    """Show agency cost records, optionally filtered by tenant/project."""
    from datetime import datetime

    engine = AgencyEngine(_load_config())

    if summary:
        agg = engine.cost_ledger.summary(tenant_id=tenant_id, project_id=project_id)
        console.print(
            Panel(
                f"Total: [bold]${agg['total']:.6f}[/bold] {agg['currency']}\n"
                f"Records: [bold]{agg['record_count']}[/bold]\n"
                f"By Category: {agg['by_category']}",
                title="Cost Summary",
                border_style="green",
            )
        )
        return

    records = engine.cost_ledger.list_records(
        tenant_id=tenant_id,
        project_id=project_id,
        category=category,
        limit=limit,
    )

    if not records:
        console.print("[dim]No cost records found.[/dim]")
        return

    table = Table(title=f"Cost Records ({len(records)})", box=box.ROUNDED)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Tenant", style="magenta")
    table.add_column("Project", style="magenta")
    table.add_column("Task", style="dim")
    table.add_column("Category", style="yellow")
    table.add_column("Amount", justify="right", style="green")
    table.add_column("Description", style="white")
    table.add_column("Timestamp", style="dim")

    for r in records:
        table.add_row(
            r.id[:12],
            r.tenant_id or "—",
            r.project_id or "—",
            r.task_id[:12] if r.task_id else "—",
            r.category,
            f"${r.amount:.6f}",
            r.description[:40] or "—",
            r.timestamp.strftime("%Y-%m-%d %H:%M:%S") if isinstance(r.timestamp, datetime) else str(r.timestamp)[:19],
        )
    console.print(table)


@app.command()
def metrics() -> None:
    """Show agency metrics summary."""
    engine = AgencyEngine(_load_config())
    summary = engine.metrics.summary()
    console.print(Panel(json.dumps(summary, indent=2, default=str), title="Metrics", border_style="cyan"))


@app.command()
def health() -> None:
    """Show agency health checks."""
    engine = AgencyEngine(_load_config())

    async def _run() -> None:
        await engine.start_worker()
        try:
            checks = engine.metrics.health()
            table = Table(title="Health Checks", box=box.ROUNDED)
            table.add_column("Name", style="cyan")
            table.add_column("Status", style="white")
            table.add_column("Latency (ms)", justify="right")
            table.add_column("Message")
            for check in checks:
                color = {"healthy": "green", "degraded": "yellow", "unhealthy": "red"}.get(check.status.value, "white")
                table.add_row(check.name, f"[{color}]{check.status.value}[/{color}]", str(check.latency_ms), check.message)
            console.print(table)
        finally:
            await engine.stop_worker()

    asyncio.run(_run())


# ---------- Marketplace ----------


marketplace_app = typer.Typer(
    name="marketplace",
    help="Discover and install agency modules",
    rich_markup_mode="rich",
)
app.add_typer(marketplace_app)


def _print_marketplace_list(
    project: str | None = None,
    category: str | None = None,
    query: str = "",
) -> None:
    engine = get_engine()
    cat: RepoCategory | None = None
    if category:
        try:
            cat = RepoCategory(category)
        except ValueError:
            console.print(f"[red]Unknown category: {category}[/red]")
            raise typer.Exit(1) from None
    listings = asyncio.run(engine.marketplace.list_modules(project_id=project, query=query, category=cat))
    table = Table(title="Marketplace Modules")
    table.add_column("ID")
    table.add_column("Category")
    table.add_column("Rating")
    table.add_column("Installs")
    table.add_column("Enabled")
    for listing in listings:
        enabled = "✓" if (project and project in listing.enabled_projects) else ""
        table.add_row(
            listing.module.id,
            listing.module.category.value,
            f"{listing.average_rating:.1f} ({listing.rating_count})",
            str(listing.install_count),
            enabled,
        )
    console.print(table)


@marketplace_app.callback(invoke_without_command=True)
def marketplace_callback(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project", help="Filter by project enablement"),
    category: str | None = typer.Option(None, "--category", help="Filter by category"),
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
) -> None:
    """Marketplace commands."""
    if ctx.invoked_subcommand is None:
        _print_marketplace_list(project=project, category=category, query=query or "")


@marketplace_app.command("list")
def marketplace_list(
    project: str | None = typer.Option(None, "--project", help="Filter by project enablement"),
    category: str | None = typer.Option(None, "--category", help="Filter by category"),
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
) -> None:
    """List marketplace modules."""
    _print_marketplace_list(project=project, category=category, query=query or "")


@marketplace_app.command("install")
def marketplace_install(module_id: str) -> None:
    """Install a marketplace module."""
    engine = get_engine()
    listing = asyncio.run(engine.marketplace.install_module(module_id))
    console.print(f"Installed [bold]{module_id}[/bold] (global install count: {listing.install_count})")


@marketplace_app.command("enable")
def marketplace_enable(
    module_id: str,
    project: str = typer.Option(..., "--project", help="Project ID to enable for"),
) -> None:
    """Enable a module for a project."""
    engine = get_engine()
    asyncio.run(engine.marketplace.enable_module(module_id, project))
    console.print(f"Enabled [bold]{module_id}[/bold] for project {project}")


@marketplace_app.command("disable")
def marketplace_disable(
    module_id: str,
    project: str = typer.Option(..., "--project", help="Project ID to disable for"),
) -> None:
    """Disable a module for a project."""
    engine = get_engine()
    asyncio.run(engine.marketplace.disable_module(module_id, project))
    console.print(f"Disabled [bold]{module_id}[/bold] for project {project}")


@marketplace_app.command("rate")
def marketplace_rate(
    module_id: str,
    score: float = typer.Argument(..., help="Rating from 1 to 5", min=1.0, max=5.0),
    user: str = typer.Option("operator", "--user", help="User ID"),
    review: str | None = typer.Option(None, "--review", help="Optional review text"),
) -> None:
    """Rate a marketplace module."""
    engine = get_engine()
    listing = asyncio.run(engine.marketplace.rate_module(module_id, user, score, review or ""))
    console.print(f"Rated [bold]{module_id}[/bold]: {listing.average_rating:.1f} ({listing.rating_count} ratings)")


@app.callback()
def main() -> None:
    """One Person Agency CLI."""


if __name__ == "__main__":
    app()
