"""Rich CLI for the One Person Agency."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import tomllib
from pathlib import Path
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
    AgencyTask,
    ModuleStatus,
    RepoCategory,
    TaskStatus,
)

app = typer.Typer(
    name="opa",
    help="One Person Agency — Unified AI orchestration for all repos",
    rich_markup_mode="rich",
)
scheduler_app = typer.Typer(
    name="scheduler",
    help="Registry auto-sync scheduler",
)
app.add_typer(scheduler_app, name="scheduler")
console = Console()


def _config_path() -> str:
    return os.environ.get("OPA_CONFIG", "./config/agency.yaml")


def _load_package_info() -> dict[str, str]:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    if tomllib is not None:
        data = tomllib.loads(content)
        return {
            "name": data["project"]["name"],
            "version": data["project"]["version"],
        }
    section_match = re.search(r"\[project\](.*?)(?=\n\[|\Z)", content, re.DOTALL)
    section = section_match.group(1) if section_match else content
    name_match = re.search(r'^\s*name\s*=\s*"([^"]+)"\s*$', section, re.MULTILINE)
    version_match = re.search(r'^\s*version\s*=\s*"([^"]+)"\s*$', section, re.MULTILINE)
    return {
        "name": name_match.group(1) if name_match else "unknown",
        "version": version_match.group(1) if version_match else "unknown",
    }


def _load_config() -> AgencyConfig:
    config_path = _config_path()
    if os.path.exists(config_path):
        import yaml

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return AgencyConfig.model_validate(data)
    return AgencyConfig(
        github_token=os.environ.get("GITHUB_TOKEN"),
        github_username=os.environ.get("GITHUB_USER", "sahiixx"),
    )


@app.command()
def sync(
    username: str = typer.Option("sahiixx", "--user", "-u", help="GitHub username to sync"),
) -> None:
    """Sync all GitHub repos into the agency registry."""
    engine = AgencyEngine(_load_config())
    with console.status("[bold green]Discovering repos..."):
        discovered = asyncio.run(engine.sync_repos(username))
    console.print(
        Panel(
            f"Synced [bold]{len(discovered)}[/bold] repos",
            title="Registry Sync",
            border_style="green",
        )
    )


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
        except ValueError as err:
            console.print(f"[red]Unknown category: {category}[/red]")
            raise typer.Exit(1) from err

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


@app.command()
def dispatch(
    intent: str = typer.Argument(..., help="Natural language intent to dispatch"),
    payload: str = typer.Option("{}", "--payload", "-p", help="JSON payload string"),
) -> None:
    """Dispatch a task through the agency."""
    engine = AgencyEngine(_load_config())
    data: dict[str, Any] = json.loads(payload)
    with console.status(f"[bold yellow]Routing: {intent}"):
        task = asyncio.run(engine.dispatch(intent, data))

    if task.module_id:
        console.print(
            Panel(
                f"Routed to [bold cyan]{task.module_id}[/bold cyan] "
                f"([italic]{task.category.value if task.category else 'N/A'}[/italic])\n"
                f"Result: {json.dumps(task.result, indent=2, default=str)}",
                title=f"Task {task.id}",
                border_style="green" if task.status.value == "completed" else "red",
            )
        )
    else:
        console.print(
            Panel(
                f"No module matched. Category: {task.category.value if task.category else 'N/A'}\n"
                f"Result: {json.dumps(task.result, indent=2, default=str)}",
                title=f"Task {task.id}",
                border_style="yellow",
            )
        )


@app.command()
def submit(
    intent: str = typer.Argument(..., help="Natural language intent to submit"),
    payload: str = typer.Option("{}", "--payload", "-p", help="JSON payload string"),
    module_id: str = typer.Option(None, "--module-id", "-m", help="Target module ID"),
    category: str = typer.Option(None, "--category", "-c", help="Target category"),
    timeout: int = typer.Option(120, "--timeout", "-t", help="Max seconds to wait for completion"),
) -> None:
    """Submit a task to the agency queue and wait for it to complete."""
    engine = AgencyEngine(_load_config())
    data: dict[str, Any] = json.loads(payload)
    cat: RepoCategory | None = None
    if category:
        try:
            cat = RepoCategory(category)
        except ValueError as err:
            console.print(f"[red]Unknown category: {category}[/red]")
            raise typer.Exit(1) from err

    async def _submit_and_wait() -> AgencyTask:
        await engine.start_worker()
        try:
            with console.status(f"[bold yellow]Submitting: {intent}"):
                task = await engine.submit_task(
                    intent,
                    payload=data,
                    module_id=module_id,
                    category=cat,
                )
            with console.status(f"[bold yellow]Running task {task.id}..."):
                for _ in range(timeout * 2):
                    if task.status.value in ("completed", "failed", "cancelled"):
                        break
                    await asyncio.sleep(0.5)
            return task
        finally:
            await engine.stop_worker()

    task = asyncio.run(_submit_and_wait())

    status_color = {
        TaskStatus.COMPLETED: "green",
        TaskStatus.FAILED: "red",
        TaskStatus.CANCELLED: "dim",
    }.get(task.status, "yellow")
    result_text = ""
    if task.result is not None:
        result_text = f"\nResult:\n{json.dumps(task.result, indent=2, default=str)}"
    error_text = f"\nError: [red]{task.error}[/red]" if task.error else ""
    console.print(
        Panel(
            f"Intent: [bold]{task.intent}[/bold]\n"
            f"Module: [bold cyan]{task.module_id or 'N/A'}[/bold cyan]\n"
            f"Category: {task.category.value if task.category else 'N/A'}\n"
            f"Status: [bold {status_color}]{task.status.value}[/bold {status_color}]"
            f"{result_text}{error_text}",
            title=f"Task {task.id}",
            border_style=status_color,
        )
    )


@app.command()
def tasks(
    limit: int = typer.Option(50, "--limit", "-n", help="Number of tasks to show"),
) -> None:
    """List recent agency tasks."""
    engine = AgencyEngine(_load_config())
    recent = engine.list_tasks(limit=limit)
    table = Table(title=f"Recent Tasks ({len(recent)})", box=box.ROUNDED)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Intent", style="white")
    table.add_column("Module", style="magenta")
    table.add_column("Category", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Created", style="dim")

    for t in recent:
        status_color = {
            TaskStatus.PENDING: "yellow",
            TaskStatus.ROUTING: "blue",
            TaskStatus.RUNNING: "bold yellow",
            TaskStatus.COMPLETED: "green",
            TaskStatus.FAILED: "red",
            TaskStatus.CANCELLED: "dim",
        }.get(t.status, "")
        table.add_row(
            t.id,
            t.intent,
            t.module_id or "N/A",
            t.category.value if t.category else "N/A",
            Text(t.status.value, style=status_color),
            t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else "N/A",
        )
    console.print(table)


@app.command("task")
def task_detail(
    task_id: str = typer.Argument(..., help="Task ID to look up"),
) -> None:
    """Show details for a single agency task."""
    engine = AgencyEngine(_load_config())
    t = engine.get_task(task_id)
    if t is None:
        console.print(f"[red]Task '{task_id}' not found.[/red]")
        raise typer.Exit(1)

    status_color = {
        TaskStatus.PENDING: "yellow",
        TaskStatus.ROUTING: "blue",
        TaskStatus.RUNNING: "bold yellow",
        TaskStatus.COMPLETED: "green",
        TaskStatus.FAILED: "red",
        TaskStatus.CANCELLED: "dim",
    }.get(t.status, "")
    result_text = ""
    if t.result is not None:
        result_text = f"\nResult:\n{json.dumps(t.result, indent=2, default=str)}"
    error_text = f"\nError: [red]{t.error}[/red]" if t.error else ""
    console.print(
        Panel(
            f"Intent: [bold]{t.intent}[/bold]\n"
            f"Module: [bold cyan]{t.module_id or 'N/A'}[/bold cyan]\n"
            f"Category: {t.category.value if t.category else 'N/A'}\n"
            f"Status: [bold {status_color}]{t.status.value}[/bold {status_color}]\n"
            f"Created: {t.created_at}\n"
            f"Started: {t.started_at or 'N/A'}\n"
            f"Completed: {t.completed_at or 'N/A'}"
            f"{result_text}{error_text}",
            title=f"Task {t.id}",
            border_style=status_color or "white",
        )
    )


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
def status() -> None:
    """Show agency package status."""
    info = _load_package_info()
    console.print(
        Panel(
            f"Agency Name: [bold cyan]{info['name']}[/bold cyan]\n"
            f"Version: [bold green]{info['version']}[/bold green]\n"
            f"Status: [bold]running[/bold]\n"
            f"Config path: [dim]{_config_path()}[/dim]",
            title="Agency Status",
            border_style="green",
        )
    )


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
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8080, "--port", "-p"),
    reload: bool = typer.Option(False, "--reload", "-r"),
) -> None:
    """Start the agency API server."""
    import uvicorn

    console.print(
        Panel(
            f"Starting API at [bold]http://{host}:{port}[/bold]",
            title="Agency Server",
            border_style="green",
        )
    )
    uvicorn.run("sahiixx_agency.api.main:app", host=host, port=port, reload=reload)


@app.command()
def exec(
    module_id: str = typer.Argument(..., help="Module name or repo identifier"),
    payload: str = typer.Option("{}", "--payload", "-p", help="JSON payload string"),
    timeout: int = typer.Option(120, "--timeout", "-t", help="Execution timeout in seconds"),
    skip_install: bool = typer.Option(False, "--skip-install", "-S", help="Skip dependency installation"),
) -> None:
    """Execute a module directly (clone, install, run)."""
    import asyncio

    from sahiixx_agency.core.runner import CloneManager, RepoRunner

    engine = AgencyEngine(_load_config())
    module = engine.registry.get(module_id)
    if not module:
        console.print(f"[red]Module '{module_id}' not found in registry.[/red]")
        raise typer.Exit(1)

    data: dict[str, Any] = json.loads(payload)
    data.setdefault("timeout", timeout)

    with console.status(f"[bold green]Cloning & running {module_id}..."):
        runner = RepoRunner(CloneManager())
        result = asyncio.run(
            runner.run(
                module,
                command=data.get("command", "run"),
                env=data.get("env"),
                timeout=timeout,
                skip_install=skip_install or data.get("skip_install", False),
            )
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
            f"\n[bold]stdout:[/bold]\n{result.get('stdout', 'N/A')[:2000]}\n"
            f"[bold]stderr:[/bold]\n{result.get('stderr', 'N/A')[:2000]}",
            title=f"Execution Result — {result.get('status', 'unknown')}",
            border_style=status,
        )
    )


@scheduler_app.command("start")
def scheduler_start(
    interval: int = typer.Option(60, "--interval", "-i", help="Sync interval in minutes (0 disables)")
) -> None:
    """Start the registry auto-sync scheduler and block until interrupted."""
    engine = AgencyEngine(_load_config())

    async def _run() -> None:
        await engine.start_scheduler(interval)
        status = engine.scheduler_status()
        console.print(
            Panel(
                f"Scheduler: [bold green]{'running' if status['running'] else 'stopped'}[/bold green]\n"
                f"Interval: [bold]{status['interval_minutes']}[/bold] minutes\n"
                f"Next sync: [dim]{status['next_sync_at'] or 'N/A'}[/dim]",
                title="Scheduler Started",
                border_style="green",
            )
        )
        if not status["running"]:
            return
        with contextlib.suppress(KeyboardInterrupt):
            while engine.scheduler_status()["running"]:
                await asyncio.sleep(1)
        await engine.stop_scheduler()

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_run())


@scheduler_app.command("stop")
def scheduler_stop() -> None:
    """Stop the scheduler in this process (CLI scheduler stops on exit anyway)."""
    console.print(
        Panel(
            "CLI scheduler runs only while the start command is active. "
            "Use Ctrl+C in the scheduler start process to stop it.",
            title="Scheduler Stop",
            border_style="yellow",
        )
    )


@scheduler_app.command("status")
def scheduler_status() -> None:
    """Show the scheduler status."""
    engine = AgencyEngine(_load_config())
    status = engine.scheduler_status()
    console.print(
        Panel(
            f"Scheduler: [bold]{'running' if status['running'] else 'stopped'}[/bold]\n"
            f"Interval: [bold]{status['interval_minutes']}[/bold] minutes\n"
            f"Last sync: [dim]{status['last_sync_at'] or 'N/A'}[/dim]\n"
            f"Next sync: [dim]{status['next_sync_at'] or 'N/A'}[/dim]",
            title="Scheduler Status",
            border_style="cyan" if status["running"] else "dim",
        )
    )


@app.callback()
def main() -> None:
    """One Person Agency CLI."""


if __name__ == "__main__":
    app()
