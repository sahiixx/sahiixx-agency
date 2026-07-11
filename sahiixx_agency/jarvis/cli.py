"""Jarvis CLI — interactive terminal interface."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from typer import Typer

if TYPE_CHECKING:
    from .agent import JarvisAgent

app = Typer(help="Jarvis 100x — Your AI Assistant")
console = Console()

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   █████╗ ██████╗ ████████╗██╗ ██████╗ ███╗   ██╗           ║
║  ██╔══██╗██╔══██╗╚══██╔══╝██║██╔═══██╗████╗  ██║           ║
║  ███████║██████╔╝   ██║   ██║██║   ██║██╔██╗ ██║           ║
║  ██╔══██║██╔══██╗   ██║   ██║██║   ██║██║╚██╗██║           ║
║  ██║  ██║██████╔╝   ██║   ██║╚██████╔╝██║ ╚████║           ║
║  ╚═╝  ╚═╝╚═════╝    ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝           ║
║                                                              ║
║   100x — Modern AI Assistant for OPA                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""


async def _run_interactive(agent: "JarvisAgent") -> None:
    """Run interactive chat loop."""
    from .models import JarvisMessage, MessageType

    console.print(Markdown("# Jarvis 100x — Interactive Mode"))
    console.print("Type your message or `/help` for commands. Type `exit` to quit.\n")

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Goodbye![/yellow]")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[yellow]Goodbye![/yellow]")
            break

        if not user_input.strip():
            continue

        # Create message
        message = JarvisMessage(
            content=user_input,
            message_type=MessageType.TEXT,
        )

        # Show thinking
        with console.status("[bold green]Thinking...[/bold green]"):
            response = await agent.process_message(message)

        # Display response
        console.print()
        console.print(Panel(
            Markdown(response.content),
            title="[bold green]Jarvis[/bold green]",
            border_style="green",
        ))
        console.print()


@app.command()
def chat(
    voice: bool = False,
    monitoring: bool = True,
) -> None:
    """Start interactive chat with Jarvis."""
    from .agent import JarvisAgent
    from .models import JarvisConfig

    console.print(BANNER, style="bold cyan")

    config = JarvisConfig(
        voice_enabled=voice,
        proactive_monitoring=monitoring,
    )

    agent = JarvisAgent(config)

    async def run() -> None:
        await agent.start()
        try:
            await _run_interactive(agent)
        finally:
            await agent.stop()

    asyncio.run(run())


@app.command()
def status() -> None:
    """Show Jarvis status."""
    from .agent import JarvisAgent

    agent = JarvisAgent()

    async def run() -> None:
        await agent.start()
        try:
            response = await agent._cmd_status([])
            console.print(Markdown(response.content))
        finally:
            await agent.stop()

    asyncio.run(run())


@app.command()
def health() -> None:
    """Check system health."""
    from .agent import JarvisAgent

    agent = JarvisAgent()

    async def run() -> None:
        response = await agent._cmd_health([])
        console.print(Markdown(response.content))

    asyncio.run(run())


@app.command()
def dispatch(
    intent: str,
) -> None:
    """Dispatch a task through Jarvis."""
    from .agent import JarvisAgent

    agent = JarvisAgent()

    async def run() -> None:
        await agent.start()
        try:
            with console.status("[bold green]Dispatching...[/bold green]"):
                response = await agent._cmd_dispatch([intent])
            console.print(Markdown(response.content))
        finally:
            await agent.stop()

    asyncio.run(run())


@app.command()
def monitor(
    interval: int = 300,
) -> None:
    """Start monitoring mode (proactive alerts)."""
    from .agent import JarvisAgent
    from .models import JarvisConfig

    config = JarvisConfig(
        proactive_monitoring=True,
        monitor_interval_seconds=interval,
    )
    agent = JarvisAgent(config)

    console.print("[bold green]Starting monitoring mode...[/bold green]")
    console.print(f"Checking every {interval} seconds. Press Ctrl+C to stop.\n")

    async def run() -> None:
        await agent.start()
        try:
            while True:
                await asyncio.sleep(interval)
                events = agent.get_recent_events(limit=5)
                if events:
                    console.print("[bold yellow]Recent events:[/bold yellow]")
                    for event in events:
                        icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴"}.get(
                            event.severity, "•"
                        )
                        console.print(f"  {icon} {event.title}: {event.description}")
                    console.print()
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped.[/yellow]")
        finally:
            await agent.stop()

    asyncio.run(run())


if __name__ == "__main__":
    app()
