# Jarvis Device Control — Maxed-Out Design Spec

**Date:** 2026-07-11
**Status:** Approved (user: "you decide")
**Scope:** Phase 1 + Phase 2 (Core Monitoring + Process/Service Control)

---

## 1. Goal

Transform the basic Device Control panel into a full Windows system command center — real-time charts, deep process/service management, and comprehensive hardware monitoring. The user wants "Jarvis 100x" — autonomous, visual, and powerful.

## 2. Architecture

### Backend (FastAPI + PowerShell)
Extend existing `/device/*` endpoints. All responses are JSON, snake_case keys.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/device/info` | GET | System info + CPU/RAM/uptime |
| `/device/processes` | GET | Top processes by CPU |
| `/device/services` | GET | Windows services list |
| `/device/services/{name}/action` | POST | start/stop/restart service |
| `/device/startup` | GET | Startup apps |
| `/device/startup/{name}/toggle` | POST | Enable/disable startup |
| `/device/disk` | GET | Per-drive disk usage |
| `/device/network` | GET | Network adapter stats |
| `/device/battery` | GET | Battery status (laptops) |
| `/device/action` | POST | All device actions |

### Frontend (React + Tailwind + Recharts)
`DeviceControlPanel` becomes a tabbed interface with 4 sections:

| Tab | Content |
|-----|---------|
| **Overview** | Live charts (CPU/RAM area), disk bars, network cards, battery, uptime |
| **Processes** | Searchable/sortable table, kill button, CPU/RAM sparklines per process |
| **Services** | Filterable service list, start/stop/restart, status badges |
| **Terminal** | PowerShell command input, output history, quick commands |

## 3. Backend Changes

### `/device/info` — Enhanced
Add disk query: `Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID,Size,FreeSpace | ConvertTo-Json`

### `/device/disk` — New
Returns array of drives with `device_id`, `total_gb`, `free_gb`, `used_percent`.

### `/device/services` — New
Returns top 50 services: `Get-Service | Select-Object Name,Status,StartType | ConvertTo-Json`

### `/device/services/{name}/action` — New
Body: `{ "action": "start" | "stop" | "restart" }`
Runs: `Start-Service`, `Stop-Service`, `Restart-Service`

### `/device/startup` — New
Returns startup apps: `Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location | ConvertTo-Json`

### `/device/network` — New
Returns adapter info: `Get-NetAdapter | Select-Object Name,Status,LinkSpeed,MacAddress | ConvertTo-Json`

### `/device/battery` — New
Returns battery: `Get-CimInstance Win32_Battery | Select-Object EstimatedChargeRemaining,BatteryStatus | ConvertTo-Json`

## 4. Frontend Changes

### Overview Tab
- **CPU Chart**: Recharts AreaChart, 60-point history, cyan gradient
- **RAM Chart**: Recharts AreaChart, 60-point history, purple gradient
- **Disk Cards**: Per-drive horizontal progress bars with free/used labels
- **Network Cards**: Adapter name, status dot, link speed
- **Battery**: Icon + percentage + status (if present)
- **Uptime**: Large display with clock icon

### Processes Tab
- **Search bar**: Filter by name in real-time
- **Sortable columns**: Name, PID, CPU%, RAM, Status
- **Kill button**: Red X with confirmation
- **Auto-refresh**: Every 5s

### Services Tab
- **Filter**: Running / Stopped / All
- **Status badges**: Green (Running), Red (Stopped), Amber (Pending)
- **Action buttons**: Start/Stop/Restart per row
- **StartType**: Auto / Manual / Disabled indicator

### Terminal Tab
- **Input**: Command text box with PowerShell prefix
- **Output**: Scrollable log with ANSI color support (basic)
- **Quick commands**: Flush DNS, IP Config, Ping Google, Netstat, Tasklist
- **History**: Last 20 commands, clickable to re-run

## 5. Data Flow

```
Browser ←3s poll→ /device/info (charts + overview)
Browser ←5s poll→ /device/processes (process table)
Browser ←on demand→ /device/services, /device/startup, /device/network, /device/disk
Browser ←POST→ /device/action (all mutations)
Browser ←POST→ /device/services/{name}/action (service mutations)
```

## 6. Error Handling

- Backend: All PowerShell errors caught, returned as `{success: false, error: "..."}`
- Frontend: Toast notifications for all actions, red/green badges
- Network: Retry once on 500, then show offline indicator

## 7. Security

- Shutdown/restart still require `confirm=true` param
- Service actions limited to non-critical services (filter out Windows core)
- Process kill uses PID (not name) to avoid accidental mass-kill
- All endpoints gated by existing API key middleware for mutating ops

## 8. Testing

- Backend: Test each new endpoint with curl
- Frontend: Build passes TypeScript, screenshot verification
- Integration: Full device tab flow — load, switch tabs, execute actions

## 9. Files to Create/Modify

| File | Action |
|------|--------|
| `sahiixx_agency/api/main.py` | Add new endpoints, enhance existing |
| `dashboard/src/components/DeviceControlPanel.tsx` | Complete rewrite as tabbed interface |
| `dashboard/src/components/SystemCharts.tsx` | New — Recharts area charts |
| `dashboard/src/components/ProcessManager.tsx` | New — process table with search |
| `dashboard/src/components/ServiceManager.tsx` | New — service control panel |
| `dashboard/src/components/SystemTerminal.tsx` | New — PowerShell terminal |
| `dashboard/src/pages/Agency.tsx` | Update right panel title logic |

## 10. Out of Scope (Phase 3/4)

- Voice commands (Web Speech API)
- Display/resolution management
- Sound device switching
- Windows Update check
- Firewall toggle
- Event viewer
- Performance profiler (per-process history)

---

*Approved by user: "you decide"*
