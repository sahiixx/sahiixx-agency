"""Core Jarvis agent — orchestrates voice, text, monitoring, and execution."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timezone
from typing import Any

from .models import (
    JarvisConfig,
    JarvisMessage,
    JarvisMode,
    JarvisResponse,
    JarvisState,
    MessageType,
    MonitorEvent,
)
from .windows_control import WindowsController

# Default system prompt for Jarvis
DEFAULT_SYSTEM_PROMPT = """You are Jarvis, a modern AI assistant inspired by Iron Man's JARVIS.
You are competent, proactive, and slightly witty. You help with:

1. Code and software engineering tasks
2. System monitoring and alerts
3. Research and analysis
4. Task automation
5. General knowledge and reasoning

Key traits:
- Be concise but thorough
- Proactively suggest improvements when you notice issues
- Take action when confident, ask when uncertain
- Reference the user's OPA (One Person Agency) ecosystem when relevant
- Maintain context across the conversation

When executing commands:
- Always verify before destructive operations
- Show what you're about to do before doing it
- Report results clearly
- Offer next steps

You have access to the user's full OPA stack: registry, tasks, workflows,
MCP tools, and all registered modules."""


class JarvisAgent:
    """The main Jarvis agent — coordinates all subsystems."""

    def __init__(self, config: JarvisConfig | None = None) -> None:
        self.config = config or JarvisConfig()
        self.state = JarvisState()
        self._monitor_task: asyncio.Task | None = None
        self._event_handlers: list[Any] = []
        self._windows = WindowsController()

        if not self.config.system_prompt:
            self.config.system_prompt = DEFAULT_SYSTEM_PROMPT

    async def start(self) -> None:
        """Start the Jarvis agent and monitoring loop."""
        self.state.mode = JarvisMode.IDLE
        self.state.session_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

        if self.config.proactive_monitoring:
            self._monitor_task = asyncio.create_task(self._monitoring_loop())

        await self._emit_event("system", "info", "Jarvis Online", f"Session {self.state.session_id} started")

    async def stop(self) -> None:
        """Stop the Jarvis agent and clean up."""
        if self._monitor_task:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task

        self.state.mode = JarvisMode.IDLE
        await self._emit_event("system", "info", "Jarvis Offline", "Session ended")

    async def process_message(self, message: JarvisMessage) -> JarvisResponse:
        """Process an incoming message and return a response."""
        self.state.mode = JarvisMode.THINKING
        self.state.turn_count += 1
        self.state.last_activity = datetime.now(timezone.utc)

        # Add to context
        self.state.context.append(message)
        if len(self.state.context) > self.config.max_context_turns:
            self.state.context = self.state.context[-self.config.max_context_turns:]

        # Route based on message type
        if message.message_type == MessageType.VOICE:
            response = await self._handle_voice(message)
        elif message.message_type == MessageType.PROACTIVE:
            response = await self._handle_proactive(message)
        elif message.message_type == MessageType.ALERT:
            response = await self._handle_alert(message)
        else:
            response = await self._handle_text(message)

        # Add response to context
        self.state.context.append(
            JarvisMessage(
                content=response.content,
                message_type=MessageType.SYSTEM,
                metadata={"response_to": message.id},
            )
        )

        self.state.mode = JarvisMode.IDLE
        return response

    async def _handle_text(self, message: JarvisMessage) -> JarvisResponse:
        """Handle text-based messages."""
        content = message.content.lower().strip()

        # Command detection: /command, "opa command", or bare command words
        known_commands = {"status", "stats", "health", "registry", "tasks", "dispatch",
                          "sync", "modules", "workflows", "clear", "context", "help", "?"}
        first_word = content.split()[0] if content.split() else ""

        if content.startswith("/") or content.startswith("opa ") or first_word in known_commands:
            return await self._handle_command(message)

        # System queries
        if any(word in content for word in ["status", "health", "stats"]):
            return await self._handle_status_query(message)

        # Task management
        if any(word in content for word in ["task", "dispatch", "run"]):
            return await self._handle_task_request(message)

        # Help
        if content in ("help", "?", "commands"):
            return await self._handle_help(message)

        # Default: general conversation
        return await self._handle_conversation(message)

    async def _handle_command(self, message: JarvisMessage) -> JarvisResponse:
        """Handle OPA commands."""
        content = message.content.strip()

        # Parse command
        if content.startswith("opa "):
            cmd = content[4:]
        elif content.startswith("/"):
            cmd = content[1:]
        else:
            cmd = content

        parts = cmd.split()
        if not parts:
            return JarvisResponse(content="Invalid command. Type 'help' for available commands.")

        action = parts[0]
        args = parts[1:]

        # Route commands
        handlers = {
            "status": self._cmd_status,
            "stats": self._cmd_stats,
            "health": self._cmd_health,
            "registry": self._cmd_registry,
            "tasks": self._cmd_tasks,
            "dispatch": self._cmd_dispatch,
            "sync": self._cmd_sync,
            "modules": self._cmd_modules,
            "workflows": self._cmd_workflows,
            "clear": self._cmd_clear,
            "context": self._cmd_context,
            "help": self._handle_help,
            "?": self._handle_help,
            # Windows control commands
            "system": self._cmd_system,
            "run": self._cmd_run,
            "open": self._cmd_open,
            "close": self._cmd_close,
            "windows": self._cmd_windows,
            "focus": self._cmd_focus,
            "clipboard": self._cmd_clipboard,
            "screenshot": self._cmd_screenshot,
            "type": self._cmd_type,
            "key": self._cmd_key,
            "mouse": self._cmd_mouse,
            "wifi": self._cmd_wifi,
            "battery": self._cmd_battery,
            "network": self._cmd_network,
            "processes": self._cmd_processes,
            "install": self._cmd_install,
            "files": self._cmd_files,
        }

        handler = handlers.get(action)
        if handler:
            return await handler(args)

        return JarvisResponse(
            content=f"Unknown command: {action}. Type 'help' for available commands."
        )

    async def _cmd_status(self, args: list[str]) -> JarvisResponse:
        """Show Jarvis status."""
        state = self.state
        return JarvisResponse(
            content=(
                f"**Jarvis Status**\n"
                f"- Mode: {state.mode.value}\n"
                f"- Session: {state.session_id}\n"
                f"- Turns: {state.turn_count}\n"
                f"- Context size: {len(state.context)} messages\n"
                f"- Active task: {state.active_task or 'None'}\n"
                f"- Monitoring: {'Active' if self._monitor_task else 'Inactive'}\n"
                f"- Events queued: {len(state.events)}"
            )
        )

    async def _cmd_stats(self, args: list[str]) -> JarvisResponse:
        """Show OPA statistics."""
        try:
            from sahiixx_agency.core.engine import AgencyEngine
            from sahiixx_agency.core.models import AgencyConfig

            config = AgencyConfig()
            engine = AgencyEngine(config)
            stats = engine.get_stats()

            lines = ["**OPA Statistics**"]
            for key, value in stats.items():
                lines.append(f"- {key}: {value}")

            return JarvisResponse(content="\n".join(lines))
        except Exception as e:
            return JarvisResponse(content=f"Could not retrieve stats: {e}")

    async def _cmd_health(self, args: list[str]) -> JarvisResponse:
        """Show health checks."""
        checks = []

        # Check API server
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("http://localhost:8082/health")
                if resp.status_code == 200:
                    checks.append("- API Server: Healthy")
                else:
                    checks.append("- API Server: Unhealthy")
        except Exception:
            checks.append("- API Server: Offline")

        # Check MCP server
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("http://localhost:8081/health")
                if resp.status_code == 200:
                    checks.append("- MCP Server: Healthy")
                else:
                    checks.append("- MCP Server: Unhealthy")
        except Exception:
            checks.append("- MCP Server: Offline")

        # Check dashboard
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("http://localhost:3000")
                if resp.status_code == 200:
                    checks.append("- Dashboard: Healthy")
                else:
                    checks.append("- Dashboard: Unhealthy")
        except Exception:
            checks.append("- Dashboard: Offline")

        return JarvisResponse(content="**Health Checks**\n" + "\n".join(checks))

    async def _cmd_registry(self, args: list[str]) -> JarvisResponse:
        """Show registry info."""
        try:
            from sahiixx_agency.core.registry import RepoRegistry

            registry = RepoRegistry()
            modules = registry.list_modules()
            categories = {}
            for m in modules:
                cat = m.category.value if hasattr(m, "category") else "unknown"
                categories[cat] = categories.get(cat, 0) + 1

            lines = [f"**Registry: {len(modules)} modules**"]
            for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
                lines.append(f"- {cat}: {count}")

            return JarvisResponse(content="\n".join(lines))
        except Exception as e:
            return JarvisResponse(content=f"Could not read registry: {e}")

    async def _cmd_tasks(self, args: list[str]) -> JarvisResponse:
        """Show recent tasks."""
        try:
            from sahiixx_agency.core.engine import AgencyEngine
            from sahiixx_agency.core.models import AgencyConfig

            config = AgencyConfig()
            engine = AgencyEngine(config)
            tasks = engine.list_tasks(limit=5)

            if not tasks:
                return JarvisResponse(content="No recent tasks.")

            lines = ["**Recent Tasks**"]
            for t in tasks[:5]:
                lines.append(f"- {t.id}: {t.status.value} — {t.intent[:50]}")

            return JarvisResponse(content="\n".join(lines))
        except Exception as e:
            return JarvisResponse(content=f"Could not list tasks: {e}")

    async def _cmd_dispatch(self, args: list[str]) -> JarvisResponse:
        """Dispatch a task."""
        if not args:
            return JarvisResponse(content="Usage: dispatch <intent>")

        intent = " ".join(args)
        self.state.mode = JarvisMode.EXECUTING
        self.state.active_task = intent

        try:
            from sahiixx_agency.core.engine import AgencyEngine
            from sahiixx_agency.core.models import AgencyConfig

            config = AgencyConfig()
            engine = AgencyEngine(config)
            task = await engine.dispatch(intent)

            self.state.active_task = None
            self.state.mode = JarvisMode.IDLE

            return JarvisResponse(
                content=f"Task dispatched: {task.id}\nStatus: {task.status.value}\nModule: {task.module_id}",
                action="task_dispatched",
                action_data={"task_id": task.id},
            )
        except Exception as e:
            self.state.active_task = None
            self.state.mode = JarvisMode.IDLE
            return JarvisResponse(content=f"Dispatch failed: {e}")

    async def _cmd_sync(self, args: list[str]) -> JarvisResponse:
        """Sync the registry."""
        self.state.mode = JarvisMode.EXECUTING
        try:
            from sahiixx_agency.core.engine import AgencyEngine
            from sahiixx_agency.core.models import AgencyConfig

            config = AgencyConfig()
            engine = AgencyEngine(config)
            result = await engine.sync_registry()

            self.state.mode = JarvisMode.IDLE
            return JarvisResponse(
                content=f"Registry synced: {result}",
                action="registry_synced",
            )
        except Exception as e:
            self.state.mode = JarvisMode.IDLE
            return JarvisResponse(content=f"Sync failed: {e}")

    async def _cmd_modules(self, args: list[str]) -> JarvisResponse:
        """List modules."""
        try:
            from sahiixx_agency.core.registry import RepoRegistry

            registry = RepoRegistry()
            modules = registry.list_modules()

            lines = [f"**Modules ({len(modules)})**"]
            for m in modules[:15]:
                stars = getattr(m, "stars", 0)
                lines.append(f"- {m.name} ({m.category.value}) — {stars} stars")

            if len(modules) > 15:
                lines.append(f"- ... and {len(modules) - 15} more")

            return JarvisResponse(content="\n".join(lines))
        except Exception as e:
            return JarvisResponse(content=f"Could not list modules: {e}")

    async def _cmd_workflows(self, args: list[str]) -> JarvisResponse:
        """List workflows."""
        return JarvisResponse(content="**Workflows**\n- No workflows defined yet. Use `opa workflow create` to add one.")

    async def _cmd_clear(self, args: list[str]) -> JarvisResponse:
        """Clear conversation context."""
        self.state.context.clear()
        return JarvisResponse(content="Context cleared.")

    async def _cmd_context(self, args: list[str]) -> JarvisResponse:
        """Show current context."""
        if not self.state.context:
            return JarvisResponse(content="No context yet.")

        lines = [f"**Context ({len(self.state.context)} messages)**"]
        for msg in self.state.context[-5:]:
            role = "You" if msg.message_type == MessageType.TEXT else "Jarvis"
            lines.append(f"- {role}: {msg.content[:80]}...")

        return JarvisResponse(content="\n".join(lines))

    async def _handle_status_query(self, message: JarvisMessage) -> JarvisResponse:
        """Handle status/health/stats queries."""
        return await self._cmd_status([])

    async def _handle_task_request(self, message: JarvisMessage) -> JarvisResponse:
        """Handle task-related requests."""
        content = message.content.lower()
        if "list" in content or "show" in content:
            return await self._cmd_tasks([])
        elif "dispatch" in content or "run" in content:
            # Extract intent from message
            intent = message.content
            for prefix in ["dispatch ", "run ", "task "]:
                if prefix in content:
                    intent = message.content[content.index(prefix) + len(prefix) :]
                    break
            return await self._cmd_dispatch([intent])
        return await self._cmd_tasks([])

    async def _handle_help(self, message: JarvisMessage) -> JarvisResponse:
        """Show help information."""
        return JarvisResponse(
            content=(
                "**Jarvis Commands**\n\n"
                "**System:**\n"
                "- `status` — Show Jarvis status\n"
                "- `health` — Check system health\n"
                "- `stats` — Show OPA statistics\n"
                "- `clear` — Clear conversation context\n"
                "- `context` — Show current context\n\n"
                "**OPA:**\n"
                "- `registry` — Show registry info\n"
                "- `modules` — List registered modules\n"
                "- `tasks` — Show recent tasks\n"
                "- `dispatch <intent>` — Dispatch a task\n"
                "- `sync` — Sync GitHub repos\n"
                "- `workflows` — List workflows\n\n"
                "**Natural Language:**\n"
                "Just type naturally — I'll understand what you need.\n"
                "Examples:\n"
                "- 'What's the status?'\n"
                "- 'Dispatch a task to scan for vulnerabilities'\n"
                "- 'Show me the registry'\n"
                "- 'What modules do we have?'\n\n"
                "**Device Control:**\n"
                "- `system` — System info (CPU, memory, disk, battery)\n"
                "- `run <command>` — Run any shell command\n"
                "- `open <app>` — Open an application\n"
                "- `close <app>` — Close an application\n"
                "- `windows` — List open windows\n"
                "- `focus <app>` — Focus a window\n"
                "- `clipboard` — Show clipboard content\n"
                "- `screenshot` — Take a screenshot\n"
                "- `type <text>` — Type text\n"
                "- `key <key>` — Press a key (e.g., key Enter, key ^c)\n"
                "- `processes` — List running processes\n"
                "- `wifi` — List WiFi networks\n"
                "- `battery` — Battery status\n"
                "- `network` — Network info\n"
                "- `install <pkg>` — Install a package\n"
                "- `files <path>` — List directory contents\n"
            )
        )

    async def _cmd_system(self, args: list[str]) -> JarvisResponse:
        """Show system information."""
        info = await self._windows.get_system_info()
        lines = [
            "**System Information**",
            f"- Hostname: {info.hostname}",
            f"- User: {info.username}",
            f"- OS: {info.os_version}",
            f"- Python: {info.python_version}",
            f"- CPU cores: {info.cpu_count}",
            f"- Memory: {info.memory_available_gb:.1f} GB / {info.memory_total_gb:.1f} GB free",
            f"- Uptime: {info.uptime_seconds // 3600}h {(info.uptime_seconds % 3600) // 60}m",
        ]
        if info.battery:
            lines.append(f"- Battery: {info.battery['charge_percent']}% ({'charging' if info.battery['charging'] else 'on battery'})")
        if info.disk_usage:
            for drive, usage in info.disk_usage.items():
                lines.append(f"- Disk {drive}: {usage['used']:.1f} GB used, {usage['free']:.1f} GB free")
        return JarvisResponse(content="\n".join(lines))

    async def _cmd_run(self, args: list[str]) -> JarvisResponse:
        """Run a shell command."""
        if not args:
            return JarvisResponse(content="Usage: run <command>")
        command = " ".join(args)
        result = await self._windows.run_command(command, timeout=60)
        if result["success"]:
            output = result.get("stdout", "").strip()
            return JarvisResponse(
                content=f"**Command:** `{command}`\n\n```\n{output[:2000]}\n```" if output else f"Command completed: `{command}`",
                action="command_executed",
            )
        else:
            error = result.get("error", result.get("stderr", "Unknown error"))
            return JarvisResponse(content=f"**Command failed:** `{command}`\n\n```\n{error[:1000]}\n```")

    async def _cmd_open(self, args: list[str]) -> JarvisResponse:
        """Open an application."""
        if not args:
            return JarvisResponse(content="Usage: open <app>\nExamples: open vscode, open chrome, open notepad")
        app = " ".join(args)
        result = await self._windows.open_application(app)
        return JarvisResponse(content=result["message"], action="app_opened", action_data={"app": app})

    async def _cmd_close(self, args: list[str]) -> JarvisResponse:
        """Close an application."""
        if not args:
            return JarvisResponse(content="Usage: close <app>")
        app = " ".join(args)
        result = await self._windows.close_application(app)
        return JarvisResponse(content=result["message"], action="app_closed", action_data={"app": app})

    async def _cmd_windows(self, args: list[str]) -> JarvisResponse:
        """List open windows."""
        windows = await self._windows.list_windows()
        if not windows:
            return JarvisResponse(content="No windows with visible titles found.")
        lines = ["**Open Windows**"]
        for w in windows[:20]:
            lines.append(f"- {w['name']}: {w['title'][:60]}")
        return JarvisResponse(content="\n".join(lines))

    async def _cmd_focus(self, args: list[str]) -> JarvisResponse:
        """Focus a window."""
        if not args:
            return JarvisResponse(content="Usage: focus <app>")
        app = " ".join(args)
        result = await self._windows.focus_window(app)
        return JarvisResponse(content=result["message"])

    async def _cmd_clipboard(self, args: list[str]) -> JarvisResponse:
        """Get or set clipboard."""
        if args and args[0] == "set":
            text = " ".join(args[1:])
            result = await self._windows.set_clipboard(text)
            return JarvisResponse(content=result["message"])
        content = await self._windows.get_clipboard()
        return JarvisResponse(content=f"**Clipboard:**\n```\n{content[:2000]}\n```" if content else "Clipboard is empty.")

    async def _cmd_screenshot(self, args: list[str]) -> JarvisResponse:
        """Take a screenshot."""
        path = args[0] if args else None
        result = await self._windows.take_screenshot(path)
        return JarvisResponse(
            content=result["message"],
            action="screenshot_taken",
            action_data={"path": result.get("path", "")},
        )

    async def _cmd_type(self, args: list[str]) -> JarvisResponse:
        """Type text."""
        if not args:
            return JarvisResponse(content="Usage: type <text>")
        text = " ".join(args)
        result = await self._windows.type_text(text)
        return JarvisResponse(content=result["message"])

    async def _cmd_key(self, args: list[str]) -> JarvisResponse:
        """Press a key."""
        if not args:
            return JarvisResponse(content="Usage: key <key>\nExamples: key Enter, key ^c, key {TAB}")
        key = args[0]
        await self._windows.press_key(key)
        return JarvisResponse(content=f"Pressed: {key}")

    async def _cmd_mouse(self, args: list[str]) -> JarvisResponse:
        """Move mouse."""
        if len(args) < 2:
            return JarvisResponse(content="Usage: mouse <x> <y>")
        try:
            x, y = int(args[0]), int(args[1])
            await self._windows.move_mouse(x, y)
            return JarvisResponse(content=f"Mouse moved to ({x}, {y})")
        except ValueError:
            return JarvisResponse(content="Invalid coordinates. Usage: mouse <x> <y>")

    async def _cmd_wifi(self, args: list[str]) -> JarvisResponse:
        """List WiFi networks."""
        networks = await self._windows.get_wifi_networks()
        if not networks:
            return JarvisResponse(content="No WiFi networks found.")
        lines = ["**WiFi Networks**"]
        for n in networks[:10]:
            signal = n.get("signal", "?")
            lines.append(f"- {n.get('ssid', 'Unknown')} — Signal: {signal}")
        return JarvisResponse(content="\n".join(lines))

    async def _cmd_battery(self, args: list[str]) -> JarvisResponse:
        """Battery status."""
        info = await self._windows.get_battery_status()
        if not info.get("has_battery"):
            return JarvisResponse(content="No battery detected (desktop or no battery).")
        lines = [
            "**Battery Status**",
            f"- Charge: {info['charge_percent']}%",
            f"- Status: {'Charging' if info['charging'] else 'On battery'}",
        ]
        if info.get("estimated_minutes"):
            lines.append(f"- Estimated time: {info['estimated_minutes']} minutes")
        return JarvisResponse(content="\n".join(lines))

    async def _cmd_network(self, args: list[str]) -> JarvisResponse:
        """Network info."""
        info = await self._windows.get_network_info()
        interfaces = info.get("interfaces", [])
        if not interfaces:
            return JarvisResponse(content="No network interfaces found.")
        lines = ["**Network Interfaces**"]
        for iface in interfaces:
            lines.append(f"- {iface['name']}: {iface['ip']}/{iface['prefix']}")
        return JarvisResponse(content="\n".join(lines))

    async def _cmd_processes(self, args: list[str]) -> JarvisResponse:
        """List processes."""
        filter_name = args[0] if args else None
        procs = await self._windows.list_processes(filter_name=filter_name, limit=15)
        if not procs:
            return JarvisResponse(content="No processes found.")
        lines = ["**Top Processes**"]
        for p in procs:
            lines.append(f"- {p.name} (PID {p.pid}): CPU {p.cpu_percent:.1f}, RAM {p.memory_mb:.0f}MB")
        return JarvisResponse(content="\n".join(lines))

    async def _cmd_install(self, args: list[str]) -> JarvisResponse:
        """Install a package."""
        if not args:
            return JarvisResponse(content="Usage: install <package> [manager]\nManagers: pip, npm, winget, choco")
        package = args[0]
        manager = args[1] if len(args) > 1 else "pip"
        result = await self._windows.install_package(package, manager)
        return JarvisResponse(
            content=f"**Installing {package} via {manager}**\n\n{result['message'][:1000]}",
            action="package_installed",
        )

    async def _cmd_files(self, args: list[str]) -> JarvisResponse:
        """List directory contents."""
        path = args[0] if args else "."
        result = await self._windows.run_command(
            f"Get-ChildItem '{path}' | Select-Object Mode, LastWriteTime, Length, Name | Format-Table -AutoSize"
        )
        if result["success"]:
            return JarvisResponse(content=f"**Contents of {path}:**\n```\n{result['stdout'][:2000]}\n```")
        return JarvisResponse(content=f"Could not list directory: {result.get('error', 'Unknown error')}")

    async def _handle_voice(self, message: JarvisMessage) -> JarvisResponse:
        """Handle voice input (transcribed text)."""
        self.state.mode = JarvisMode.THINKING

        # Voice messages are just transcribed text — process as text
        text_msg = JarvisMessage(
            content=message.content,
            message_type=MessageType.TEXT,
            metadata={"source": "voice", **message.metadata},
        )
        response = await self._handle_text(text_msg)

        # Mark as voice response
        response.metadata = {"voice": True, **response.metadata}
        return response

    async def _handle_proactive(self, message: JarvisMessage) -> JarvisResponse:
        """Handle proactive monitoring events."""
        return JarvisResponse(
            content=f"**Proactive Alert**\n{message.content}",
            action="proactive_alert",
        )

    async def _handle_alert(self, message: JarvisMessage) -> JarvisResponse:
        """Handle system alerts."""
        return JarvisResponse(
            content=f"**System Alert**\n{message.content}",
            action="system_alert",
        )

    async def _handle_conversation(self, message: JarvisMessage) -> JarvisResponse:
        """Handle general conversation."""
        # For now, provide a helpful response
        # In production, this would call the LLM
        return JarvisResponse(
            content=(
                f"I received your message: '{message.content}'\n\n"
                "I'm currently running in command mode. Try:\n"
                "- `help` — See available commands\n"
                "- `status` — Check system status\n"
                "- `dispatch <intent>` — Run a task\n\n"
                "Or just ask me something specific about the OPA ecosystem."
            )
        )

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.config.monitor_interval_seconds)
                await self._check_system_health()
            except asyncio.CancelledError:
                break
            except Exception:
                pass  # Don't crash the monitoring loop

    async def _check_system_health(self) -> None:
        """Check system health and emit events."""
        checks = {
            "api": "http://localhost:8082/health",
            "mcp": "http://localhost:8081/health",
            "dashboard": "http://localhost:3000",
        }

        for name, url in checks.items():
            try:
                import httpx

                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        await self._emit_event(
                            "health",
                            "warning",
                            f"{name.title()} unhealthy",
                            f"HTTP {resp.status_code} from {url}",
                        )
            except Exception:
                await self._emit_event(
                    "health",
                    "critical",
                    f"{name.title()} offline",
                    f"Could not connect to {url}",
                    suggested_action=f"Restart the {name} service",
                )

    async def _emit_event(
        self,
        event_type: str,
        severity: str,
        title: str,
        description: str,
        suggested_action: str | None = None,
    ) -> MonitorEvent:
        """Emit a monitoring event."""
        event = MonitorEvent(
            event_type=event_type,
            severity=severity,
            source="jarvis",
            title=title,
            description=description,
            suggested_action=suggested_action,
        )
        self.state.events.append(event)

        # Keep only last 100 events
        if len(self.state.events) > 100:
            self.state.events = self.state.events[-100:]

        return event

    def get_recent_events(self, limit: int = 10) -> list[MonitorEvent]:
        """Get recent monitoring events."""
        return self.state.events[-limit:]
