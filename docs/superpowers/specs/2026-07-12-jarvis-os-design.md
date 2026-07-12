# JARVIS OS v3.0 — Full-Spectrum Device Command Design Spec

**Date:** 2026-07-12  
**Scope:** Complete UI/UX overhaul of the OPA Dashboard Device Control system  
**Theme:** Arc Reactor + CRT Hybrid — "Jarvis 100x" real-time visual experience  
**Status:** Draft pending approval

---

## 1. Overview

Transform the existing OPA Dashboard Device Control panel from a functional-but-flat admin interface into a **living, breathing Jarvis OS** — a holographic command center that feels like Iron Man's HUD crossed with a military CIC terminal. Every pixel must communicate "this system is alive and watching."

**Key Principles:**
- **Data first, chrome second** — Every visual element serves information
- **Motion = meaning** — Animations indicate state changes, not decoration
- **Depth through light** — Glow, shadow, and transparency create spatial hierarchy
- **Voice as first-class** — ElevenLabs integration for Jarvis persona speech

---

## 2. Visual System

### 2.1 Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-void` | `#0A0A0A` | Deepest background, root layer |
| `--bg-surface` | `rgba(255,255,255,0.03)` | Card surfaces, panels |
| `--bg-elevated` | `rgba(255,255,255,0.06)` | Hover states, active tabs |
| `--accent-red` | `#FF1A1A` | Jarvis primary — alerts, active states, critical |
| `--accent-cyan` | `#00F0FF` | Data streams, charts, info metrics |
| `--accent-green` | `#00FF66` | Healthy status, success, progress fills |
| `--accent-amber` | `#EAB308` | Warnings, attention needed |
| `--text-primary` | `#FFFFFF` | Headings, primary data |
| `--text-secondary` | `#A3A3A3` | Labels, descriptions |
| `--text-muted` | `#525252` | Inactive, disabled |
| `--border-subtle` | `rgba(255,255,255,0.06)` | Default card borders |
| `--border-glow` | `rgba(0,240,255,0.3)` | Active/hover glow borders |

### 2.2 Typography

| Role | Font | Weight | Usage |
|------|------|--------|-------|
| Display | Orbitron | 700-900 | Page titles, HUD labels, section headers |
| Data | JetBrains Mono | 400-700 | Metrics, charts, code, timestamps |
| Body | Inter / system-ui | 400-600 | Descriptions, readable text |

**Text Effects:**
- CRT glitch on hover for interactive titles (chromatic aberration: red `-2px`, cyan `+2px`)
- Text shadow glow on active elements: `0 0 8px rgba(0,240,255,0.4)`

### 2.3 Effects & Animations

**Global Effects:**
- **CRT Scanline Overlay:** `repeating-linear-gradient` at 4px intervals, `opacity: 0.04`, `pointer-events: none`, fixed overlay across entire viewport
- **Ambient Grid:** Subtle perspective grid on empty backgrounds, `opacity: 0.03`

**Card Effects:**
- **Corner Brackets:** 2px accent-color borders on corners only (military HUD style)
- **Border Glow Pulse:** `box-shadow` animation, 2s cycle, intensifies on hover
- **Glass Surface:** `backdrop-filter: blur(12px)` + subtle noise texture

**Motion Language:**
- **Page enter:** `opacity: 0→1`, `scale: 0.98→1.0`, `duration: 0.3s`
- **Card hover:** `translateY(-2px)`, border glow intensifies to 2x
- **Data update:** Value change triggers brief flash (color ping) + counter animation
- **Status change:** Color transition over 0.5s with pulse
- **Loading:** Skeleton shimmer (gradient sweep) instead of spinners

---

## 3. Architecture

### 3.1 Two-Mode System

```
┌─────────────────────────────────────────────────────────────┐
│                    JARVIS OS v3.0                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                  │
│  │   DASHBOARD  │      │    HUD       │                  │
│  │   (Deep)     │  ←→  │  (Overlay)   │                  │
│  │              │      │              │                  │
│  │  9 tabs      │      │  4 metrics   │                  │
│  │  Full control│      │  Top procs   │                  │
│  │  All data    │      │  Voice input │                  │
│  └──────────────┘      └──────────────┘                  │
│                                                             │
│  Hotkey: Ctrl+Shift+J toggles HUD overlay                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo]  JARVIS OS v3.0                    [Voice] [User]  │
├──────────┬──────────────────────────────────────┬───────────┤
│          │                                      │           │
│  NAV     │         MAIN CONTENT AREA            │  COMPACT  │
│  SIDEBAR │         (Active Tab Content)         │  METRICS  │
│          │                                      │  SIDEBAR  │
│  Chat    │                                      │           │
│  Tasks   │  ┌──────────────────────────────┐   │  CPU  45% │
│  Device  │  │  Tab: Overview               │   │  RAM  62% │
│  Graph   │  │  [Charts] [Heatmap] [Info]   │   │  Disk 91% │
│  ...     │  │                              │   │  Uptime   │
│          │  └──────────────────────────────┘   │  Top 5    │
│          │                                      │  Procs    │
│          │                                      │           │
└──────────┴──────────────────────────────────────┴───────────┘
```

### 3.3 Tab Structure (9 Tabs)

| Tab | Purpose | Key Visual |
|-----|---------|------------|
| **Overview** | System health at a glance | 4 neon area charts + CPU heatmap + info cards |
| **Processes** | Process management | Sortable table with sparklines + kill/restart actions |
| **Services** | Windows service control | Status LEDs + start/stop/restart buttons |
| **Terminal** | PowerShell/cmd access | Terminal emulator with command history |
| **Voice** | Voice command interface | ElevenLabs integration + waveform visualization |
| **Profiler** | Performance analysis | Real-time flame-graph style visualization |
| **Updates** | Windows Update | Progress bars + install/schedule actions |
| **Events** | Windows Event Log | Severity-filtered log viewer with color coding |
| **HUD** | Fullscreen immersive | 2x2 metric grid + process bars + scanlines |

---

## 4. Component Specifications

### 4.1 MetricCard (Reusable)

```
┌─────────────────────────┐
│ ◆ CPU                   │  ← Label + live pulse dot
│                         │
│   45.2%                 │  ← Value (Orbitron, large)
│                         │
│ ████████████░░░░░░░░░░  │  ← Progress bar (accent color)
│                         │
│ ┌──────────────────┐    │  ← Corner brackets (accent)
│ └──────────────────┘    │
└─────────────────────────┘
```

**States:**
- Default: Subtle border, no glow
- Hover: `translateY(-2px)`, border glow intensifies
- Critical (>80%): Red pulse animation, border turns red
- Warning (50-80%): Amber pulse, border turns amber
- Healthy (<50%): Cyan steady glow

### 4.2 AreaChart (Neon)

- **Fill:** Gradient from accent color (40% opacity top) to transparent (2% bottom)
- **Stroke:** 2px solid accent color
- **Active dot:** 4px radius, accent color, no stroke
- **Tooltip:** Dark glass panel, accent-colored value
- **Animation:** 500ms smooth transition on data update
- **Empty state:** "Collecting data..." with pulsing dot

### 4.3 ProcessTable

| Column | Style |
|--------|-------|
| PID | Mono, muted |
| Name | Body, primary |
| CPU% | Mono, color-coded (green→amber→red) |
| Memory | Mono, secondary |
| Status | Colored dot + label |
| Actions | Icon buttons (kill, restart, inspect) |

**Row hover:** Highlight row, show action buttons
**Kill action:** Red flash on row → collapse animation → remove

### 4.4 VoicePanel (ElevenLabs Integration)

```
┌─────────────────────────────────┐
│  🎤 JARVIS VOICE INTERFACE      │
│                                 │
│  ┌─────────────────────────┐   │
│  │                         │   │
│  │    ◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯    │   │  ← Waveform
│  │    ◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯    │   │
│  │                         │   │
│  └─────────────────────────┘   │
│                                 │
│  [Hold Space to Speak]          │
│                                 │
│  "System status report"        │
│  "Kill process 1234"             │
│  "Restart service Spooler"     │
│                                 │
└─────────────────────────────────┘
```

**States:**
- Idle: Pulsing orb, ready text
- Listening: Waveform animation, red recording indicator
- Processing: Spinner + "Processing..."
- Speaking: Waveform + green indicator
- Executing: Command displayed + result

### 4.5 HUD Overlay (Fullscreen)

Triggered by `Ctrl+Shift+J` or from the HUD tab.

```
┌─────────────────────────────────────────────────────────────┐
│  ● JARVIS SYSTEM MONITOR                    UPTIME: 04:12:33 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  CPU             │  │  RAM             │                │
│  │                  │  │                  │                │
│  │    45.2%         │  │    62.1%         │                │
│  │                  │  │                  │                │
│  │ ████████████░░░  │  │ ██████████████████░░░ │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  DISK            │  │  NETWORK         │                │
│  │                  │  │                  │                │
│  │    91.4%         │  │  ↑1.2MB ↓5.3MB  │                │
│  │                  │  │                  │                │
│  │ ████████████████████░░  │  │ ████████████░░░░░░░  │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  TOP PROCESSES                                              │
│  chrome.exe      ████████████████████░░░░░░░░░░░░░░░  45.2%  │
│  python.exe      ████████████░░░░░░░░░░░░░░░░░░░░░  28.1%  │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

**Visual:**
- Full black with 95% opacity
- Scanline overlay
- Animated grid background
- Corner brackets on each metric card
- Accent bar at bottom of each card

---

## 5. Data Flow

### 5.1 Real-Time Metrics (SSE)

```
Client ←── SSE /api/device/stream ──→ Server
  │                                        │
  │  { cpu: 45.2, memory: 62.1,            │
  │    disk: 91.4, net_sent: 1024,        │
  │    net_recv: 5120, timestamp: ... }   │
  │                                        │
  ▼                                        │
Chart history arrays (circular, max 30)    │
  │                                        │
  ▼                                        │
Recharts AreaChart re-renders              │
  │                                        │
  ▼                                        │
Metric cards update with counter animation │
```

### 5.2 Voice Command Flow (ElevenLabs)

```
User speaks → Browser mic capture → ElevenLabs STT
                                              │
                                              ▼
                                        Text command
                                              │
                                              ▼
                                        Intent parser (regex/rules)
                                              │
                                              ▼
                                        ┌─────────────┐
                                        │ "status"    │ → Fetch /api/device/info
                                        │ "kill N"    │ → POST /api/device/process/kill
                                        │ "restart X" │ → POST /api/device/service/restart
                                        │ "update"    │ → POST /api/device/updates/install
                                        └─────────────┘
                                              │
                                              ▼
                                        Execute action
                                              │
                                              ▼
                                        ElevenLabs TTS → "Process 1234 terminated."
```

### 5.3 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/device/stream` | SSE | Live metrics stream (2s interval) |
| `/api/device/info` | GET | System info (CPU, RAM, disk, uptime) |
| `/api/device/processes` | GET | Process list |
| `/api/device/processes/:pid/kill` | POST | Kill process |
| `/api/device/services` | GET | Service list |
| `/api/device/services/:name/restart` | POST | Restart service |
| `/api/device/disk` | GET | Disk usage |
| `/api/device/network` | GET | Network adapters |
| `/api/device/battery` | GET | Battery status |
| `/api/device/updates` | GET | Pending updates |
| `/api/device/updates/install` | POST | Install updates |
| `/api/device/events` | GET | Windows Event Log |
| `/api/device/cores` | GET | Per-core CPU usage |
| `/api/device/voice` | POST | Voice command processing |
| `/api/device/clipboard` | GET/POST | Clipboard read/write |
| `/api/device/terminal` | POST | Execute terminal command |

---

## 6. Animation Specifications

| Animation | Trigger | Duration | Easing |
|-----------|---------|----------|--------|
| Page enter | Mount | 300ms | ease-out |
| Card hover | Mouse enter | 200ms | ease-out |
| Card leave | Mouse leave | 150ms | ease-in |
| Border glow pulse | Continuous | 2000ms | ease-in-out |
| Data value change | Value update | 300ms | ease-out |
| Chart area sweep | Data update | 500ms | ease-out |
| Process kill | Action | 400ms | ease-in (collapse) |
| Toast enter | Add | 300ms | ease-out |
| Toast leave | Remove | 200ms | ease-in |
| HUD open | Hotkey | 400ms | cubic-bezier(0.4, 0, 0.2, 1) |
| HUD close | Close | 300ms | ease-in |
| Scanline | Continuous | 8s | linear (infinite) |
| Live pulse | Continuous | 2s | ease-in-out (infinite) |
| Voice waveform | Audio activity | 50ms | linear |
| Skeleton shimmer | Loading | 1.5s | linear (infinite) |

---

## 7. State Management

### 7.1 Device Control Panel State

```typescript
interface DeviceState {
  // Current view
  activeTab: TabKey
  hudOpen: boolean
  
  // System data
  info: SystemInfo | null
  processes: Process[]
  services: Service[]
  diskInfo: Drive[]
  networkInfo: Adapter[]
  batteryInfo: BatteryItem[]
  updatesData: UpdatesData
  eventsData: Event[]
  
  // History for charts
  cpuHistory: number[]
  memHistory: number[]
  diskHistory: number[]
  netHistory: NetSnapshot[]
  coreData: number[]
  
  // UI state
  loading: Record<string, boolean>
  toasts: Toast[]
  confirmDialog: ConfirmDialog | null
  
  // Voice
  voiceState: 'idle' | 'listening' | 'processing' | 'speaking' | 'executing'
  voiceTranscript: string
  voiceResponse: string
}
```

### 7.2 SSE Connection

- Connect on Overview tab mount
- Disconnect on unmount (or keep alive for background updates)
- Reconnect with exponential backoff on error
- Heartbeat/ping every 30s

---

## 8. Performance Considerations

| Concern | Mitigation |
|---------|------------|
| Chart re-renders | Memoize chart data, use `useMemo` for transformed arrays |
| SSE frequency | 2s interval is reasonable; throttle to 5s if CPU > 80% |
| Glow effects | Use `transform` + `opacity` instead of `box-shadow` for GPU acceleration |
| Scanline overlay | Single fixed element, `pointer-events: none`, `will-change: transform` |
| Process list | Virtualize if > 100 processes (react-window) |
| Voice waveform | Use Canvas 2D, not DOM elements; throttle to 30fps |
| HUD overlay | Render only when open; unmount on close to free resources |

---

## 9. Accessibility

- All interactive elements have focus states (visible glow ring)
- Color is not the only indicator — icons + text accompany all status colors
- Keyboard navigation: Tab through tabs, Enter to activate, Escape to close HUD
- Screen reader: Live regions for metric updates, `aria-live="polite"`
- Reduced motion: Disable animations if `prefers-reduced-motion: reduce`

---

## 10. Dependencies

| Package | Purpose |
|---------|---------|
| `recharts` | Area charts (already installed) |
| `framer-motion` | Page transitions, card animations, HUD enter/exit |
| `lucide-react` | Icons (already installed) |
| `elevenlabs` | Voice synthesis (to be integrated) |
| `react-window` | Process list virtualization (if needed) |

---

## 11. Files to Modify/Create

### Modified:
- `dashboard/src/components/DeviceControlPanel.tsx` — Main panel, tab logic, state
- `dashboard/src/components/SystemCharts.tsx` — Neon area charts with new styling
- `dashboard/src/components/PerformanceProfiler.tsx` — Flame-graph style visualization
- `dashboard/src/components/JarvisHUD.tsx` — Fullscreen HUD overlay
- `dashboard/src/components/DeviceSidebarCompact.tsx` — Compact right sidebar
- `dashboard/src/pages/Agency.tsx` — Layout integration
- `dashboard/src/index.css` — Global styles, CRT overlay, animations

### New:
- `dashboard/src/components/CpuHeatmap.tsx` — Per-core CPU visualization (exists, enhance)
- `dashboard/src/components/ProcessTree.tsx` — Process tree view (exists, enhance)
- `dashboard/src/components/VoiceCommandPanel.tsx` — ElevenLabs voice interface
- `dashboard/src/components/SystemTerminal.tsx` — Terminal emulator (exists, enhance)
- `dashboard/src/components/WindowsUpdate.tsx` — Update manager (exists, enhance)
- `dashboard/src/components/SystemEventLog.tsx` — Event viewer (exists, enhance)
- `dashboard/src/hooks/useDeviceStream.ts` — SSE hook (exists, enhance)
- `dashboard/src/hooks/useVoiceCommand.ts` — Voice command hook (new)

---

## 12. Success Criteria

1. **Visual:** Dashboard matches deployed Command Center aesthetic (Orbitron, CRT, glow)
2. **Functional:** All 9 tabs work with real Windows data via API
3. **Performance:** 60fps animations, <100ms response to interactions
4. **Real-time:** Charts show live data within 2 seconds of SSE push
5. **Voice:** ElevenLabs integration functional (STT + TTS)
6. **HUD:** Overlay summons with hotkey, shows live metrics + processes
7. **Polish:** No double headers, no empty chart voids, no skeletons showing indefinitely

---

## 13. Out of Scope (Future)

- Mobile/responsive optimization (desktop-first)
- Multi-device support (single Windows host)
- Plugin system for third-party tools
- AI agent autonomy (always human-in-the-loop for destructive actions)

---

*Spec written. Awaiting approval before proceeding to implementation plan.*
