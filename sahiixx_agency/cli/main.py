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
from sahiixx_agency.core.models import AgencyConfig, ModuleStatus, RepoCategory

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
app.add_typer(task_app)
console = Console()


def _load_config() -> AgencyConfig:
    config_path = os.environ.get("OPA_CONFIG", "./config/agency.yaml")
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


@app.command()
def dispatch(
    intent: str = typer.Argument(..., help="Natural language intent to dispatch"),
    payload: str = typer.Option("{}", "--payload", "-p", help="JSON payload string"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Return immediately with the pending task id"),
) -> None:
    """Dispatch a task through the agency."""
    engine = AgencyEngine(_load_config())
    data: dict[str, Any] = json.loads(payload)

    async def _run() -> None:
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

            with console.status(f"[bold yellow]Executing: {intent}"):
                for _ in range(240):  # 2 minute max wait
                    current = engine.get_task(task.id)
                    if current.status.value in ("completed", "failed", "cancelled"):
                        break
                    await asyncio.sleep(0.5)

            final = engine.get_task(task.id)
            if final.module_id:
                console.print(
                    Panel(
                        f"Routed to [bold cyan]{final.module_id}[/bold cyan] ([italic]{final.category.value}[/italic])\n"
                        f"Status: [bold]{final.status.value}[/bold]\n"
                        f"Result: {json.dumps(final.result, indent=2, default=str)}",
                        title=f"Task {final.id}",
                        border_style="green" if final.status.value == "completed" else "red",
                    )
                )
            else:
                console.print(
                    Panel(
                        f"No module matched. Category: {final.category.value}\n"
                        f"Status: [bold]{final.status.value}[/bold]\n"
                        f"Result: {json.dumps(final.result, indent=2, default=str)}",
                        title=f"Task {final.id}",
                        border_style="yellow",
                    )
                )
        finally:
            await engine.stop_worker()

    asyncio.run(_run())


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
                result_preview = json.dumps(task.result, indent=2, default=str)[:2000]
            error_preview = task.error or ""

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
                    border_style="green"
                    if task.status.value == "completed"
                    else "red"
                    if task.status.value == "failed"
                    else "yellow",
                )
            )
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
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8080, "--port", "-p"),
    reload: bool = typer.Option(False, "--reload", "-r"),
) -> None:
    """Start the agency API server."""
    import uvicorn

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
            f"\n[bold]stdout:[/bold]\n{result.get('stdout', 'N/A')[:2000]}\n"
            f"[bold]stderr:[/bold]\n{result.get('stderr', 'N/A')[:2000]}",
            title=f"Execution Result — {result.get('status', 'unknown')}",
            border_style=status,
        )
    )


@app.callback()
def main() -> None:
    """One Person Agency CLI."""


if __name__ == "__main__":
    app()
