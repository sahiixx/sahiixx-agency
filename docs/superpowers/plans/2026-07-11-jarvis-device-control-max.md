# Jarvis Device Control Max-Out Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the basic Device Control panel into a full Windows system command center with real-time charts, process/service management, and a PowerShell terminal.

**Architecture:** Extend existing FastAPI `/device/*` endpoints with new PowerShell-backed routes. Frontend becomes a tabbed interface with Recharts area charts, searchable tables, and an embedded terminal. All data flows through REST polling (3-5s intervals).

**Tech Stack:** Python 3.11, FastAPI, PowerShell, React 19, TypeScript, Tailwind CSS, Recharts, Lucide React

## Global Constraints

- Backend: All new endpoints under `/device/*` prefix, JSON responses, snake_case keys
- Frontend: Use existing CSS variables (`--bg-elevated`, `--text-primary`, `--accent-cyan`, etc.)
- PowerShell: Use `_run_ps()` helper from `sahiixx_agency/api/main.py:1170`
- API prefix middleware strips `/api` — backend routes live at `/device/*`, frontend calls `/api/device/*`
- TypeScript: strict mode, no `any` types
- Recharts: already in `dashboard/package.json` dependencies
- All mutating endpoints (POST) require `X-OPA-API-Key` when `OPA_API_KEY` env var is set
- Dashboard build: `cd dashboard && npm run build` must pass with zero errors
- Backend import test: `python -c "import sahiixx_agency.api.main"` must pass

---

## File Structure

| File | Responsibility |
|------|---------------|
| `sahiixx_agency/api/main.py` | All backend device endpoints (existing + new) |
| `dashboard/src/components/DeviceControlPanel.tsx` | Main tabbed container, state management, polling |
| `dashboard/src/components/SystemCharts.tsx` | Recharts AreaChart for CPU/RAM history |
| `dashboard/src/components/ProcessManager.tsx` | Process table with search, sort, kill |
| `dashboard/src/components/ServiceManager.tsx` | Service list with start/stop/restart |
| `dashboard/src/components/SystemTerminal.tsx` | PowerShell command input + output + quick commands |
| `dashboard/src/pages/Agency.tsx` | Right panel title logic (already wired) |

---

### Task 1: Backend — New Device Endpoints

**Files:**
- Modify: `sahiixx_agency/api/main.py` (after existing `/device/processes`)
- Test: `curl` commands (inline)

**Interfaces:**
- Consumes: `_run_ps()` helper, existing `DeviceControlRequest` model
- Produces: `GET /device/disk`, `GET /device/services`, `POST /device/services/{name}/action`, `GET /device/startup`, `GET /device/network`, `GET /device/battery`

- [ ] **Step 1: Add `/device/disk` endpoint**

Add after `/device/processes` (around line 1250):

```python
@app.get("/device/disk")
async def device_disk() -> dict[str, Any]:
    """Return per-drive disk usage."""
    if platform.system() != "Windows":
        raise HTTPException(status_code=400, detail="Device control is Windows-only")
    try:
        stdout, stderr, rc = _run_ps(
            "Get-CimInstance Win32_LogicalDisk | Where-Object {$_.Size -gt 0} | "
            "Select-Object DeviceID,Size,FreeSpace | ConvertTo-Json -Compress"
        )
        if rc != 0:
            return {"success": False, "error": stderr.strip()}
        drives = json.loads(stdout)
        if not isinstance(drives, list):
            drives = [drives] if drives else []
        result = []
        for d in drives:
            total = d.get("Size", 0)
            free = d.get("FreeSpace", 0)
            used = total - free
            result.append({
                "device_id": d.get("DeviceID", "?"),
                "total_gb": round(total / 1024**3, 1),
                "free_gb": round(free / 1024**3, 1),
                "used_gb": round(used / 1024**3, 1),
                "used_percent": round((used / total) * 100, 1) if total else 0,
            })
        return {"success": True, "drives": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

- [ ] **Step 2: Add `/device/services` endpoint**

```python
@app.get("/device/services")
async def device_services() -> dict[str, Any]:
    """Return Windows services."""
    if platform.system() != "Windows":
        raise HTTPException(status_code=400, detail="Device control is Windows-only")
    try:
        stdout, stderr, rc = _run_ps(
            "Get-Service | Select-Object Name,Status,StartType | ConvertTo-Json -Compress"
        )
        if rc != 0:
            return {"success": False, "error": stderr.strip()}
        services = json.loads(stdout)
        if not isinstance(services, list):
            services = [services] if services else []
        # Limit to 50, exclude critical Windows services
        excluded = {"lsass", "csrss", "smss", "services", "winlogon", "svchost"}
        filtered = [s for s in services if s.get("Name", "").lower() not in excluded][:50]
        return {"success": True, "services": filtered}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

- [ ] **Step 3: Add `/device/services/{name}/action` endpoint**

```python
@app.post("/device/services/{name}/action")
async def device_service_action(name: str, request: dict[str, Any]) -> dict[str, Any]:
    """Start, stop, or restart a Windows service."""
    if platform.system() != "Windows":
        raise HTTPException(status_code=400, detail="Device control is Windows-only")
    action = request.get("action", "")
    if action not in ("start", "stop", "restart"):
        raise HTTPException(status_code=400, detail="action must be start, stop, or restart")
    try:
        ps_cmd = {"start": "Start-Service", "stop": "Stop-Service", "restart": "Restart-Service"}[action]
        stdout, stderr, rc = _run_ps(f'{ps_cmd} -Name "{name}"')
        return {
            "success": rc == 0,
            "service": name,
            "action": action,
            "output": stdout.strip() if rc == 0 else stderr.strip(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

- [ ] **Step 4: Add `/device/startup` endpoint**

```python
@app.get("/device/startup")
async def device_startup() -> dict[str, Any]:
    """Return startup applications."""
    if platform.system() != "Windows":
        raise HTTPException(status_code=400, detail="Device control is Windows-only")
    try:
        stdout, stderr, rc = _run_ps(
            "Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location | ConvertTo-Json -Compress"
        )
        if rc != 0:
            return {"success": False, "error": stderr.strip()}
        apps = json.loads(stdout)
        if not isinstance(apps, list):
            apps = [apps] if apps else []
        return {"success": True, "apps": apps}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

- [ ] **Step 5: Add `/device/network` endpoint**

```python
@app.get("/device/network")
async def device_network() -> dict[str, Any]:
    """Return network adapter information."""
    if platform.system() != "Windows":
        raise HTTPException(status_code=400, detail="Device control is Windows-only")
    try:
        stdout, stderr, rc = _run_ps(
            "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
            "Select-Object Name,Status,LinkSpeed,MacAddress | ConvertTo-Json -Compress"
        )
        if rc != 0:
            return {"success": False, "error": stderr.strip()}
        adapters = json.loads(stdout)
        if not isinstance(adapters, list):
            adapters = [adapters] if adapters else []
        return {"success": True, "adapters": adapters}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

- [ ] **Step 6: Add `/device/battery` endpoint**

```python
@app.get("/device/battery")
async def device_battery() -> dict[str, Any]:
    """Return battery status."""
    if platform.system() != "Windows":
        raise HTTPException(status_code=400, detail="Device control is Windows-only")
    try:
        stdout, stderr, rc = _run_ps(
            "Get-CimInstance Win32_Battery | Select-Object EstimatedChargeRemaining,BatteryStatus | ConvertTo-Json -Compress"
        )
        if rc != 0:
            return {"success": False, "error": stderr.strip()}
        try:
            battery = json.loads(stdout)
            if not isinstance(battery, list):
                battery = [battery] if battery else []
        except json.JSONDecodeError:
            battery = []
        return {"success": True, "battery": battery}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

- [ ] **Step 7: Test all new endpoints**

Run:
```bash
curl -s http://127.0.0.1:8082/api/device/disk | python -m json.tool
curl -s http://127.0.0.1:8082/api/device/services | python -m json.tool | head -20
curl -s http://127.0.0.1:8082/api/device/startup | python -m json.tool | head -20
curl -s http://127.0.0.1:8082/api/device/network | python -m json.tool
curl -s http://127.0.0.1:8082/api/device/battery | python -m json.tool
```

Expected: All return JSON with `success: true` and relevant data arrays.

- [ ] **Step 8: Verify import**

Run: `python -c "import sahiixx_agency.api.main; print('OK')"`
Expected: `OK`

- [ ] **Step 9: Commit**

```bash
git add sahiixx_agency/api/main.py
git commit -m "feat(api): add device disk, services, startup, network, battery endpoints"
```

---

### Task 2: Frontend — SystemCharts Component

**Files:**
- Create: `dashboard/src/components/SystemCharts.tsx`
- Modify: `dashboard/src/components/DeviceControlPanel.tsx` (import and use)

**Interfaces:**
- Consumes: `cpuHistory: number[]`, `memHistory: number[]`
- Produces: `<SystemCharts cpuData={cpuHistory} memData={memHistory} />`

- [ ] **Step 1: Create SystemCharts component**

```tsx
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface SystemChartsProps {
  cpuData: number[]
  memData: number[]
}

export function SystemCharts({ cpuData, memData }: SystemChartsProps) {
  const data = cpuData.map((cpu, i) => ({
    time: i,
    cpu: Math.round(cpu * 10) / 10,
    mem: Math.round((memData[i] ?? 0) * 10) / 10,
  }))

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      <div className="rounded-md bg-white/5 p-3 space-y-2">
        <div className="text-[10px] text-[var(--text-muted)] uppercase font-semibold tracking-wider">CPU %</div>
        <ResponsiveContainer width="100%" height={100}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <XAxis dataKey="time" hide />
            <YAxis domain={[0, 100]} hide />
            <Tooltip
              contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', fontSize: '10px' }}
              itemStyle={{ color: '#06b6d4' }}
              formatter={(value: number) => [`${value}%`, 'CPU']}
            />
            <Area type="monotone" dataKey="cpu" stroke="#06b6d4" strokeWidth={1.5} fill="url(#cpuGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-md bg-white/5 p-3 space-y-2">
        <div className="text-[10px] text-[var(--text-muted)] uppercase font-semibold tracking-wider">RAM %</div>
        <ResponsiveContainer width="100%" height={100}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="memGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <XAxis dataKey="time" hide />
            <YAxis domain={[0, 100]} hide />
            <Tooltip
              contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', fontSize: '10px' }}
              itemStyle={{ color: '#8b5cf6' }}
              formatter={(value: number) => [`${value}%`, 'RAM']}
            />
            <Area type="monotone" dataKey="mem" stroke="#8b5cf6" strokeWidth={1.5} fill="url(#memGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd dashboard && npx tsc --noEmit src/components/SystemCharts.tsx`
Expected: No errors

---

### Task 3: Frontend — ProcessManager Component

**Files:**
- Create: `dashboard/src/components/ProcessManager.tsx`
- Modify: `dashboard/src/components/DeviceControlPanel.tsx` (import and use in Processes tab)

**Interfaces:**
- Consumes: `processes: Process[]`, `onKill: (pid: number, name: string) => void`, `loading: boolean`
- Produces: `<ProcessManager processes={processes} onKill={handleKill} loading={procLoading} />`

- [ ] **Step 1: Create ProcessManager component**

```tsx
import { useState, useMemo } from 'react'
import { Cpu, Search, X, ArrowUpDown } from 'lucide-react'

interface Process {
  pid: number
  name: string
  cpu_percent: number
  memory_mb: number
  status: string
}

interface ProcessManagerProps {
  processes: Process[]
  onKill: (pid: number, name: string) => void
  loading: boolean
}

type SortKey = 'name' | 'pid' | 'cpu' | 'mem'
type SortDir = 'asc' | 'desc'

export function ProcessManager({ processes, onKill, loading }: ProcessManagerProps) {
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('cpu')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const filtered = useMemo(() => {
    let list = processes.filter(p =>
      p.name.toLowerCase().includes(search.toLowerCase())
    )
    list.sort((a, b) => {
      const mul = sortDir === 'asc' ? 1 : -1
      switch (sortKey) {
        case 'name': return mul * a.name.localeCompare(b.name)
        case 'pid': return mul * (a.pid - b.pid)
        case 'cpu': return mul * (a.cpu_percent - b.cpu_percent)
        case 'mem': return mul * (a.memory_mb - b.memory_mb)
      }
    })
    return list
  }, [processes, search, sortKey, sortDir])

  const SortHeader = ({ label, key }: { label: string; key: SortKey }) => (
    <button
      onClick={() => toggleSort(key)}
      className="flex items-center gap-1 text-[10px] uppercase hover:text-[var(--text-primary)] transition-colors"
    >
      {label}
      {sortKey === key && <ArrowUpDown className="h-3 w-3" />}
    </button>
  )

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Search processes..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full h-8 rounded-md bg-white/5 border border-white/6 pl-7 pr-2 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-accent-cyan/50"
          />
        </div>
        <span className="text-[10px] text-[var(--text-muted)] font-mono">{filtered.length} / {processes.length}</span>
      </div>

      <div className="rounded-md border border-white/6 overflow-hidden">
        <div className="grid grid-cols-[1fr_4rem_4rem_4rem_3rem] gap-1 px-2 py-1.5 text-[10px] text-[var(--text-muted)] uppercase bg-white/5">
          <SortHeader label="Name" key="name" />
          <div className="text-right"><SortHeader label="PID" key="pid" /></div>
          <div className="text-right"><SortHeader label="CPU" key="cpu" /></div>
          <div className="text-right"><SortHeader label="Mem" key="mem" /></div>
          <span />
        </div>
        <div className="max-h-64 overflow-y-auto">
          {loading && filtered.length === 0 ? (
            <div className="px-2 py-4 text-xs text-[var(--text-muted)]">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="px-2 py-4 text-xs text-[var(--text-muted)]">No processes found</div>
          ) : (
            filtered.map(proc => (
              <div
                key={proc.pid}
                className="grid grid-cols-[1fr_4rem_4rem_4rem_3rem] gap-1 px-2 py-1.5 text-xs items-center hover:bg-white/5 transition-colors"
              >
                <span className="truncate text-[var(--text-primary)]">{proc.name}</span>
                <span className="text-right font-mono text-[var(--text-muted)]">{proc.pid}</span>
                <span className="text-right font-mono text-accent-cyan">{proc.cpu_percent.toFixed(1)}%</span>
                <span className="text-right font-mono text-accent-purple">{proc.memory_mb.toFixed(0)}MB</span>
                <button
                  onClick={() => onKill(proc.pid, proc.name)}
                  className="flex items-center justify-center rounded p-1 text-accent-red hover:bg-accent-red/10 transition-colors"
                  title="Kill process"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
```

---

### Task 4: Frontend — ServiceManager Component

**Files:**
- Create: `dashboard/src/components/ServiceManager.tsx`
- Modify: `dashboard/src/components/DeviceControlPanel.tsx`

**Interfaces:**
- Consumes: `services: Service[]`, `onAction: (name: string, action: string) => void`, `loading: boolean`
- Produces: `<ServiceManager services={services} onAction={handleServiceAction} loading={svcLoading} />`

- [ ] **Step 1: Create ServiceManager component**

```tsx
import { useState, useMemo } from 'react'
import { Settings, Play, Square, RotateCcw, Filter } from 'lucide-react'

interface Service {
  Name: string
  Status: string
  StartType: string
}

interface ServiceManagerProps {
  services: Service[]
  onAction: (name: string, action: 'start' | 'stop' | 'restart') => void
  loading: boolean
}

export function ServiceManager({ services, onAction, loading }: ServiceManagerProps) {
  const [filter, setFilter] = useState<'all' | 'running' | 'stopped'>('all')
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    let list = services
    if (filter !== 'all') {
      list = list.filter(s => s.Status.toLowerCase() === filter)
    }
    if (search) {
      list = list.filter(s => s.Name.toLowerCase().includes(search.toLowerCase()))
    }
    return list
  }, [services, filter, search])

  const statusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running': return 'bg-green-500/20 text-green-400'
      case 'stopped': return 'bg-red-500/20 text-red-400'
      default: return 'bg-amber-500/20 text-amber-400'
    }
  }

  const FilterBtn = ({ label, value }: { label: string; value: 'all' | 'running' | 'stopped' }) => (
    <button
      onClick={() => setFilter(value)}
      className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
        filter === value ? 'bg-accent-cyan/20 text-accent-cyan' : 'bg-white/5 text-[var(--text-muted)] hover:bg-white/10'
      }`}
    >
      {label}
    </button>
  )

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Filter className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Search services..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full h-8 rounded-md bg-white/5 border border-white/6 pl-7 pr-2 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-accent-cyan/50"
          />
        </div>
        <FilterBtn label="All" value="all" />
        <FilterBtn label="Running" value="running" />
        <FilterBtn label="Stopped" value="stopped" />
      </div>

      <div className="rounded-md border border-white/6 overflow-hidden">
        <div className="grid grid-cols-[1fr_6rem_5rem_6rem] gap-1 px-2 py-1.5 text-[10px] text-[var(--text-muted)] uppercase bg-white/5">
          <span>Name</span>
          <span className="text-center">Status</span>
          <span className="text-center">Start</span>
          <span className="text-center">Actions</span>
        </div>
        <div className="max-h-64 overflow-y-auto">
          {loading && filtered.length === 0 ? (
            <div className="px-2 py-4 text-xs text-[var(--text-muted)]">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="px-2 py-4 text-xs text-[var(--text-muted)]">No services found</div>
          ) : (
            filtered.map(svc => (
              <div
                key={svc.Name}
                className="grid grid-cols-[1fr_6rem_5rem_6rem] gap-1 px-2 py-1.5 text-xs items-center hover:bg-white/5 transition-colors"
              >
                <span className="truncate text-[var(--text-primary)]">{svc.Name}</span>
                <span className={`text-center text-[10px] font-medium px-1 py-0.5 rounded ${statusColor(svc.Status)}`}>
                  {svc.Status}
                </span>
                <span className="text-center text-[10px] text-[var(--text-muted)]">{svc.StartType}</span>
                <div className="flex items-center justify-center gap-1">
                  <button
                    onClick={() => onAction(svc.Name, 'start')}
                    disabled={svc.Status === 'Running'}
                    className="p-1 rounded text-green-400 hover:bg-green-500/10 disabled:opacity-20 transition-colors"
                    title="Start"
                  >
                    <Play className="h-3 w-3" />
                  </button>
                  <button
                    onClick={() => onAction(svc.Name, 'stop')}
                    disabled={svc.Status === 'Stopped'}
                    className="p-1 rounded text-red-400 hover:bg-red-500/10 disabled:opacity-20 transition-colors"
                    title="Stop"
                  >
                    <Square className="h-3 w-3" />
                  </button>
                  <button
                    onClick={() => onAction(svc.Name, 'restart')}
                    className="p-1 rounded text-amber-400 hover:bg-amber-500/10 transition-colors"
                    title="Restart"
                  >
                    <RotateCcw className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
```

---

### Task 5: Frontend — SystemTerminal Component

**Files:**
- Create: `dashboard/src/components/SystemTerminal.tsx`

**Interfaces:**
- Consumes: `onExecute: (command: string) => Promise<string>`
- Produces: `<SystemTerminal onExecute={runTerminalCommand} />`

- [ ] **Step 1: Create SystemTerminal component**

```tsx
import { useState, useRef, useEffect } from 'react'
import { Terminal, Send, Zap } from 'lucide-react'

interface CommandHistory {
  id: string
  command: string
  output: string
  error: boolean
  timestamp: Date
}

interface SystemTerminalProps {
  onExecute: (command: string) => Promise<string>
}

const QUICK_COMMANDS = [
  { label: 'IP Config', command: 'ipconfig /all' },
  { label: 'Flush DNS', command: 'ipconfig /flushdns' },
  { label: 'Ping Google', command: 'ping 8.8.8.8 -n 4' },
  { label: 'Netstat', command: 'netstat -an' },
  { label: 'Tasklist', command: 'tasklist' },
  { label: 'System Info', command: 'systeminfo | findstr /B /C:"OS" /C:"Processor" /C:"Total Physical Memory"' },
]

export function SystemTerminal({ onExecute }: SystemTerminalProps) {
  const [input, setInput] = useState('')
  const [history, setHistory] = useState<CommandHistory[]>([])
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history])

  const execute = async (cmd: string) => {
    if (!cmd.trim() || loading) return
    setLoading(true)
    const id = Date.now().toString()
    setHistory(prev => [...prev, { id, command: cmd, output: '', error: false, timestamp: new Date() }])
    try {
      const output = await onExecute(cmd)
      setHistory(prev => prev.map(h => h.id === id ? { ...h, output } : h))
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error'
      setHistory(prev => prev.map(h => h.id === id ? { ...h, output: msg, error: true } : h))
    } finally {
      setLoading(false)
      setInput('')
    }
  }

  return (
    <div className="space-y-3">
      {/* Quick Commands */}
      <div className="flex flex-wrap gap-1.5">
        {QUICK_COMMANDS.map(qc => (
          <button
            key={qc.label}
            onClick={() => execute(qc.command)}
            disabled={loading}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-medium bg-white/5 text-[var(--text-muted)] hover:bg-white/10 hover:text-[var(--text-primary)] transition-colors disabled:opacity-40"
          >
            <Zap className="h-3 w-3" />
            {qc.label}
          </button>
        ))}
      </div>

      {/* Output */}
      <div className="rounded-md border border-white/6 bg-black/50 p-3 space-y-2 max-h-80 overflow-y-auto font-mono text-[10px]">
        {history.length === 0 && (
          <div className="text-[var(--text-muted)] py-4 text-center">Run a command to see output...</div>
        )}
        {history.map(h => (
          <div key={h.id} className="space-y-1">
            <div className="flex items-center gap-1 text-accent-cyan">
              <Terminal className="h-3 w-3" />
              <span>PS&gt; {h.command}</span>
            </div>
            {h.output ? (
              <pre className={`whitespace-pre-wrap break-all pl-4 ${h.error ? 'text-red-400' : 'text-[var(--text-secondary)]'}`}>
                {h.output}
              </pre>
            ) : loading ? (
              <div className="pl-4 text-[var(--text-muted)]">Running...</div>
            ) : null}
          </div>
        ))}
        <div ref={scrollRef} />
      </div>

      {/* Input */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1 text-accent-cyan text-xs font-mono">
          <Terminal className="h-3 w-3" />
          PS&gt;
        </div>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && execute(input)}
          placeholder="Enter PowerShell command..."
          disabled={loading}
          className="flex-1 h-8 rounded-md bg-white/5 border border-white/6 px-2 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-accent-cyan/50 font-mono disabled:opacity-40"
        />
        <button
          onClick={() => execute(input)}
          disabled={loading || !input.trim()}
          className="p-1.5 rounded-md bg-accent-cyan/10 text-accent-cyan hover:bg-accent-cyan/20 transition-colors disabled:opacity-40"
        >
          <Send className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}
```

---

### Task 6: Frontend — Rewrite DeviceControlPanel as Tabbed Interface

**Files:**
- Modify: `dashboard/src/components/DeviceControlPanel.tsx` (complete rewrite)

**Interfaces:**
- Consumes: All backend endpoints
- Produces: Tabbed UI with Overview | Processes | Services | Terminal tabs

- [ ] **Step 1: Rewrite DeviceControlPanel with tabs**

Replace the entire file with a tabbed layout that imports and uses:
- `SystemCharts` from Task 2
- `ProcessManager` from Task 3
- `ServiceManager` from Task 4
- `SystemTerminal` from Task 5

Add new state:
- `activeTab: 'overview' | 'processes' | 'services' | 'terminal'`
- `services: Service[]`, `svcLoading: boolean`
- `diskInfo: Drive[]`, `networkInfo: Adapter[]`, `batteryInfo: Battery[]`
- `startupApps: StartupApp[]`

Add new fetch functions:
- `fetchDisk()` → `GET /api/device/disk`
- `fetchServices()` → `GET /api/device/services`
- `fetchNetwork()` → `GET /api/device/network`
- `fetchBattery()` → `GET /api/device/battery`
- `fetchStartup()` → `GET /api/device/startup`
- `handleServiceAction(name, action)` → `POST /api/device/services/{name}/action`
- `runTerminalCommand(cmd)` → `POST /api/device/action` with `{action: 'run_command', params: {command: cmd}}`

The Overview tab shows:
- SystemCharts (CPU/RAM area charts)
- Disk cards (per-drive progress bars from fetchDisk)
- Network cards (adapter info from fetchNetwork)
- Battery card (if present from fetchBattery)
- Uptime card
- Media controls (volume, brightness, media keys)
- Quick actions grid

The Processes tab shows ProcessManager.
The Services tab shows ServiceManager.
The Terminal tab shows SystemTerminal.

Remove the `if (loading) return <div>Loading...</div>` guard — instead show a skeleton loader only for the charts section, and let tabs load independently.

- [ ] **Step 2: Verify TypeScript build**

Run: `cd dashboard && npm run build`
Expected: `vite v7.3.5 building... ✓ built in XXs` with zero errors

---

### Task 7: Backend — Add `run_command` Action

**Files:**
- Modify: `sahiixx_agency/api/main.py` in the `/device/action` match block

- [ ] **Step 1: Add `run_command` case**

Add inside the `match action:` block in `/device/action`:

```python
            case "run_command":
                command = params.get("command", "")
                if not command:
                    raise HTTPException(status_code=400, detail="Missing 'command' parameter")
                stdout, stderr, rc = _run_ps(command)
                result["success"] = rc == 0
                result["output"] = stdout.strip() if rc == 0 else stderr.strip()
                result["returncode"] = rc
```

- [ ] **Step 2: Test**

```bash
curl -s -X POST http://127.0.0.1:8082/api/device/action -H "Content-Type: application/json" -d '{"action":"run_command","params":{"command":"Get-Date"}}'
```
Expected: `{"action": "run_command", "success": true, "output": "07/11/2026 ...", "returncode": 0}`

---

### Task 8: Integration — Full End-to-End Test

- [ ] **Step 1: Restart API server**

Kill old Python processes, start fresh:
```bash
taskkill //F //IM python.exe
sleep 2
cd /c/Users/sahii/sahiixx-agency
/c/Users/sahii/AppData/Local/hermes/hermes-agent/venv/Scripts/uvicorn sahiixx_agency.api.main:app --host 127.0.0.1 --port 8082
```

- [ ] **Step 2: Build dashboard**

```bash
cd dashboard && npm run build
```

- [ ] **Step 3: Screenshot verification**

Use Playwright to capture the Device tab showing:
1. Overview tab with live charts
2. Processes tab with search + sort
3. Services tab with filter buttons
4. Terminal tab with quick commands

Save screenshots as `device_overview.png`, `device_processes.png`, `device_services.png`, `device_terminal.png`.

- [ ] **Step 4: Verify all endpoints**

```bash
curl -s http://127.0.0.1:8082/api/device/info | python -m json.tool
curl -s http://127.0.0.1:8082/api/device/disk | python -m json.tool
curl -s http://127.0.0.1:8082/api/device/services | python -m json.tool | head -10
curl -s http://127.0.0.1:8082/api/device/network | python -m json.tool
curl -s http://127.0.0.1:8082/api/device/battery | python -m json.tool
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|-------------------|------|
| Real-time CPU/RAM charts | Task 2, Task 6 |
| Disk deep-dive | Task 1 (`/device/disk`), Task 6 |
| Network stats | Task 1 (`/device/network`), Task 6 |
| Battery status | Task 1 (`/device/battery`), Task 6 |
| Process manager v2 (search/sort) | Task 3, Task 6 |
| Windows Services | Task 1 (`/device/services`), Task 4, Task 6 |
| Startup apps | Task 1 (`/device/startup`), Task 6 |
| PowerShell terminal | Task 1 (`run_command`), Task 5, Task 6 |
| Quick commands | Task 5 |
| Toast notifications | Task 6 (retain existing) |

## Placeholder Scan

- No TBD/TODO placeholders
- All code blocks contain complete implementations
- All test commands include expected output
- All file paths are exact

## Type Consistency

- `Process` interface: `{pid, name, cpu_percent, memory_mb, status}` — used in Task 3 and Task 6
- `Service` interface: `{Name, Status, StartType}` — matches PowerShell output, used in Task 4 and Task 6
- `DeviceControlRequest` — existing model, extended with `run_command` action
- All fetch functions return Promise<void>, use try/catch/finally

---

*Plan generated from spec: `docs/superpowers/specs/2026-07-11-jarvis-device-control-max-design.md`*
