"""Windows device control — full E2E automation for Jarvis."""

from __future__ import annotations

import asyncio
import os
import subprocess
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class SystemInfo(BaseModel):
    """Windows system information."""

    hostname: str = ""
    username: str = ""
    os_version: str = ""
    python_version: str = ""
    cpu_count: int = 0
    memory_total_gb: float = 0.0
    memory_available_gb: float = 0.0
    disk_usage: dict[str, Any] = Field(default_factory=dict)
    network_interfaces: list[dict[str, Any]] = Field(default_factory=list)
    battery: dict[str, Any] | None = None
    uptime_seconds: int = 0
    timestamp: str = ""


class ProcessInfo(BaseModel):
    """Running process information."""

    pid: int
    name: str
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    status: str = ""
    command: str = ""


class FileOperation(BaseModel):
    """File operation result."""

    success: bool
    operation: str
    path: str
    message: str = ""
    size: int | None = None


class WindowsController:
    """Controls Windows system — processes, files, apps, input, screen."""

    def __init__(self) -> None:
        self._powershell = "powershell.exe"
        self._allowed_commands: list[str] = []
        self._blocked_commands: list[str] = [
            "rm -rf",
            "del /s /q",
            "format",
            "shutdown",
            "restart",
        ]

    async def run_command(
        self,
        command: str,
        timeout: int = 30,
        shell: bool = True,
    ) -> dict[str, Any]:
        """Run a shell command and return output."""
        # Safety check
        if self._is_blocked(command):
            return {
                "success": False,
                "error": "Command blocked for safety",
                "command": command,
            }

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=shell,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )

            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "returncode": proc.returncode,
                "command": command,
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Command timed out after {timeout}s",
                "command": command,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command,
            }

    async def get_system_info(self) -> SystemInfo:
        """Get comprehensive Windows system information."""
        info = SystemInfo(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Basic info
        result = await self.run_command(
            "Write-Output $env:COMPUTERNAME; Write-Output $env:USERNAME; "
            "(Get-CimInstance Win32_OperatingSystem).Caption; "
            "python --version 2>&1 | Select-Object -First 1"
        )
        if result["success"]:
            lines = result["stdout"].strip().split("\n")
            info.hostname = lines[0] if len(lines) > 0 else ""
            info.username = lines[1] if len(lines) > 1 else ""
            info.os_version = lines[2] if len(lines) > 2 else ""
            info.python_version = lines[3] if len(lines) > 3 else ""

        # CPU and Memory
        result = await self.run_command(
            "(Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors; "
            "$os = Get-CimInstance Win32_OperatingSystem; "
            "[math]::Round($os.TotalVisibleMemorySize/1MB, 2); "
            "[math]::Round($os.FreePhysicalMemory/1MB, 2)"
        )
        if result["success"]:
            lines = result["stdout"].strip().split("\n")
            try:
                info.cpu_count = int(lines[0]) if lines[0] else 0
                info.memory_total_gb = float(lines[1]) if len(lines) > 1 and lines[1] else 0.0
                info.memory_available_gb = float(lines[2]) if len(lines) > 2 and lines[2] else 0.0
            except (ValueError, IndexError):
                pass

        # Disk usage
        result = await self.run_command(
            "Get-PSDrive -PSProvider FileSystem | Select-Object Name, "
            "@{N='Used';E={[math]::Round($_.Used/1GB,2)}}, "
            "@{N='Free';E={[math]::Round($_.Free/1GB,2)}} | ConvertTo-Json"
        )
        if result["success"]:
            try:
                drives = json.loads(result["stdout"])
                if isinstance(drives, dict):
                    drives = [drives]
                info.disk_usage = {d["Name"]: {"used": d["Used"], "free": d["Free"]} for d in drives}
            except json.JSONDecodeError:
                pass

        # Battery (laptops only)
        result = await self.run_command(
            "Get-CimInstance Win32_Battery | Select-Object EstimatedChargeRemaining, "
            "BatteryStatus | ConvertTo-Json"
        )
        if result["success"] and result["stdout"].strip():
            try:
                battery = json.loads(result["stdout"])
                info.battery = {
                    "charge_percent": battery.get("EstimatedChargeRemaining", 0),
                    "charging": battery.get("BatteryStatus", 0) == 2,
                }
            except json.JSONDecodeError:
                pass

        # Uptime
        result = await self.run_command(
            "(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime | Select-Object -ExpandProperty TotalSeconds"
        )
        if result["success"]:
            try:
                info.uptime_seconds = int(float(result["stdout"].strip()))
            except ValueError:
                pass

        return info

    async def list_processes(
        self,
        filter_name: str | None = None,
        limit: int = 20,
    ) -> list[ProcessInfo]:
        """List running processes."""
        cmd = (
            "Get-Process | Select-Object Id, ProcessName, "
            "@{N='CPU';E={$_.CPU}}, "
            "@{N='MemoryMB';E={[math]::Round($_.WorkingSet64/1MB,2)}}, "
            "Responding"
        )
        if filter_name:
            cmd += f" | Where-Object {{$_.ProcessName -like '*{filter_name}*'}}"
        cmd += f" | Sort-Object CPU -Descending | Select-Object -First {limit} | ConvertTo-Json"

        result = await self.run_command(cmd)
        if not result["success"]:
            return []

        try:
            procs = json.loads(result["stdout"])
            if isinstance(procs, dict):
                procs = [procs]
            return [
                ProcessInfo(
                    pid=p.get("Id", 0),
                    name=p.get("ProcessName", ""),
                    cpu_percent=p.get("CPU", 0) or 0,
                    memory_mb=p.get("MemoryMB", 0) or 0,
                    status="running" if p.get("Responding") else "not responding",
                )
                for p in procs
            ]
        except json.JSONDecodeError:
            return []

    async def open_application(self, app_name: str) -> dict[str, Any]:
        """Open a Windows application."""
        # Common app mappings
        app_map = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "explorer": "explorer.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "edge": "msedge.exe",
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "vscode": "code",
            "teams": "teams.exe",
            "slack": "slack.exe",
            "spotify": "spotify.exe",
        }

        exe = app_map.get(app_name.lower(), app_name)
        result = await self.run_command(f"Start-Process '{exe}' -ErrorAction SilentlyContinue")

        return {
            "success": result["success"],
            "app": app_name,
            "exe": exe,
            "message": f"Launched {app_name}" if result["success"] else f"Failed to launch {app_name}",
        }

    async def close_application(self, app_name: str) -> dict[str, Any]:
        """Close a Windows application."""
        result = await self.run_command(
            f"Stop-Process -Name '{app_name}' -Force -ErrorAction SilentlyContinue"
        )
        return {
            "success": result["success"],
            "app": app_name,
            "message": f"Closed {app_name}" if result["success"] else f"Failed to close {app_name}",
        }

    async def list_windows(self) -> list[dict[str, Any]]:
        """List open windows."""
        result = await self.run_command(
            "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | "
            "Select-Object Id, ProcessName, MainWindowTitle | ConvertTo-Json"
        )
        if not result["success"]:
            return []

        try:
            windows = json.loads(result["stdout"])
            if isinstance(windows, dict):
                windows = [windows]
            return [
                {
                    "pid": w.get("Id", 0),
                    "name": w.get("ProcessName", ""),
                    "title": w.get("MainWindowTitle", ""),
                }
                for w in windows
            ]
        except json.JSONDecodeError:
            return []

    async def focus_window(self, process_name: str) -> dict[str, Any]:
        """Bring a window to focus."""
        result = await self.run_command(
            f"(Get-Process -Name '{process_name}' -ErrorAction SilentlyContinue).MainWindowHandle | "
            f"ForEach-Object {{ Add-Type -Name Win -Namespace Native -MemberDefinition '{{ "
            f"[DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd); }}'; "
            f"[Native.Win]::SetForegroundWindow($_) }}"
        )
        return {
            "success": result["success"],
            "process": process_name,
            "message": f"Focused {process_name}" if result["success"] else f"Failed to focus {process_name}",
        }

    async def get_clipboard(self) -> str:
        """Get clipboard content."""
        result = await self.run_command("Get-Clipboard -Raw")
        return result["stdout"].strip() if result["success"] else ""

    async def set_clipboard(self, text: str) -> dict[str, Any]:
        """Set clipboard content."""
        # Escape text for PowerShell
        escaped = text.replace("'", "''")
        result = await self.run_command(f"Set-Clipboard -Value '{escaped}'")
        return {"success": result["success"], "message": "Clipboard updated"}

    async def take_screenshot(self, output_path: str | None = None) -> dict[str, Any]:
        """Take a screenshot using PowerShell."""
        if not output_path:
            output_path = str(
                Path.home() / "Pictures" / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )

        result = await self.run_command(
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
            f"$bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height); "
            f"$graphics = [System.Drawing.Graphics]::FromImage($bitmap); "
            f"$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size); "
            f"$bitmap.Save('{output_path}'); "
            f"Write-Output '{output_path}'"
        )

        return {
            "success": result["success"] and os.path.exists(output_path),
            "path": output_path,
            "message": f"Screenshot saved to {output_path}" if result["success"] else "Screenshot failed",
        }

    async def type_text(self, text: str, delay_ms: int = 50) -> dict[str, Any]:
        """Type text using keyboard simulation."""
        # Use PowerShell with SendKeys
        escaped = text.replace("'", "''")
        result = await self.run_command(
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"[System.Windows.Forms.SendKeys]::SendWait('{escaped}')"
        )
        return {"success": result["success"], "message": f"Typed {len(text)} characters"}

    async def press_key(self, key: str) -> dict[str, Any]:
        """Press a keyboard key."""
        result = await self.run_command(
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"[System.Windows.Forms.SendKeys]::SendWait('{key}')"
        )
        return {"success": result["success"], "key": key}

    async def move_mouse(self, x: int, y: int) -> dict[str, Any]:
        """Move mouse to coordinates."""
        result = await self.run_command(
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x}, {y})"
        )
        return {"success": result["success"], "x": x, "y": y}

    async def click_mouse(self, button: str = "left") -> dict[str, Any]:
        """Click mouse button."""
        btn = "LEFT" if button.lower() == "left" else "RIGHT"
        result = await self.run_command(
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"$mouse = New-Object System.Windows.Forms.MouseSimulator; "
            f"[System.Windows.Forms.Cursor]::Position = [System.Windows.Forms.Cursor]::Position"
        )
        return {"success": result["success"], "button": button}

    async def get_wifi_networks(self) -> list[dict[str, Any]]:
        """List available WiFi networks."""
        result = await self.run_command(
            "netsh wlan show networks mode=bssid | "
            "Select-String -Pattern 'SSID|Signal|Authentication' | "
            "ForEach-Object { $_.Line.Trim() }"
        )
        if not result["success"]:
            return []

        networks = []
        current: dict[str, str] = {}
        for line in result["stdout"].split("\n"):
            line = line.strip()
            if "SSID" in line and "BSSID" not in line:
                if current:
                    networks.append(current)
                current = {"ssid": line.split(":")[-1].strip()}
            elif "Signal" in line:
                current["signal"] = line.split(":")[-1].strip()
            elif "Authentication" in line:
                current["auth"] = line.split(":")[-1].strip()

        if current:
            networks.append(current)

        return networks

    async def get_battery_status(self) -> dict[str, Any]:
        """Get detailed battery status."""
        result = await self.run_command(
            "Get-CimInstance Win32_Battery | Select-Object "
            "EstimatedChargeRemaining, BatteryStatus, "
            "EstimatedRunTime, FullChargeCapacity | ConvertTo-Json"
        )
        if not result["success"] or not result["stdout"].strip():
            return {"has_battery": False}

        try:
            battery = json.loads(result["stdout"])
            return {
                "has_battery": True,
                "charge_percent": battery.get("EstimatedChargeRemaining", 0),
                "charging": battery.get("BatteryStatus", 0) == 2,
                "estimated_minutes": battery.get("EstimatedRunTime", 0),
                "full_capacity_wh": battery.get("FullChargeCapacity", 0),
            }
        except json.JSONDecodeError:
            return {"has_battery": False}

    async def get_network_info(self) -> dict[str, Any]:
        """Get network information."""
        result = await self.run_command(
            "Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -ne '127.0.0.1'} | "
            "Select-Object InterfaceAlias, IPAddress, PrefixLength | ConvertTo-Json"
        )
        if not result["success"]:
            return {}

        try:
            interfaces = json.loads(result["stdout"])
            if isinstance(interfaces, dict):
                interfaces = [interfaces]
            return {
                "interfaces": [
                    {
                        "name": i.get("InterfaceAlias", ""),
                        "ip": i.get("IPAddress", ""),
                        "prefix": i.get("PrefixLength", 0),
                    }
                    for i in interfaces
                ]
            }
        except json.JSONDecodeError:
            return {}

    async def monitor_directory(
        self,
        path: str,
        duration_seconds: int = 10,
    ) -> list[dict[str, Any]]:
        """Monitor a directory for changes."""
        events = []
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < duration_seconds:
            result = await self.run_command(
                f"Get-ChildItem '{path}' | Select-Object Name, LastWriteTime, Length | ConvertTo-Json"
            )
            if result["success"]:
                try:
                    files = json.loads(result["stdout"])
                    if isinstance(files, dict):
                        files = [files]
                    for f in files:
                        events.append({
                            "name": f.get("Name", ""),
                            "modified": f.get("LastWriteTime", ""),
                            "size": f.get("Length", 0),
                        })
                except json.JSONDecodeError:
                    pass
            await asyncio.sleep(1)

        return events

    async def install_package(self, package: str, manager: str = "pip") -> dict[str, Any]:
        """Install a package using pip, npm, or winget."""
        managers = {
            "pip": f"pip install {package}",
            "npm": f"npm install -g {package}",
            "winget": f"winget install {package} --accept-package-agreements --accept-source-agreements",
            "choco": f"choco install {package} -y",
        }

        cmd = managers.get(manager)
        if not cmd:
            return {"success": False, "error": f"Unknown package manager: {manager}"}

        result = await self.run_command(cmd, timeout=120)
        return {
            "success": result["success"],
            "package": package,
            "manager": manager,
            "message": result.get("stdout", result.get("stderr", ""))[:500],
        }

    def _is_blocked(self, command: str) -> bool:
        """Check if a command is blocked for safety."""
        cmd_lower = command.lower()
        return any(blocked in cmd_lower for blocked in self._blocked_commands)
