import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Monitor,
  Volume2,
  VolumeX,
  Sun,
  Lock,
  Power,
  RotateCcw,
  Camera,
  Activity,
  Cpu,
  HardDrive,
  Zap,
  AlertTriangle,
  Play,
  Pause,
  SkipForward,
  SkipBack,
  Square,
  Globe,
  FileText,
  Trash2,
  Clipboard,
  Wifi,
  Bluetooth,
  Clock,
  ChevronUp,
  ChevronDown,
  CheckCircle2,
  XCircle,
  Loader2,
  LayoutDashboard,
  List,
  Cog,
  Terminal as TerminalIcon,
  Battery,
  Network,
  TrendingUp,
  AlertCircle,
  Mic,
  Shield,
  Maximize2,
  ScrollText,
} from 'lucide-react'
import { SystemCharts } from './SystemCharts'
import { ProcessManager } from './ProcessManager'
import { ServiceManager } from './ServiceManager'
import { SystemTerminal } from './SystemTerminal'
import { PerformanceProfiler } from './PerformanceProfiler'
import { WindowsUpdate } from './WindowsUpdate'
import { VoiceCommandPanel } from './VoiceCommandPanel'
import { SystemEventLog } from './SystemEventLog'
import { JarvisHUD } from './JarvisHUD'
import { CpuHeatmap } from './CpuHeatmap'
import { ProcessTree } from './ProcessTree'
import { useDeviceStream } from '../hooks/useDeviceStream'

interface SystemInfo {
  platform: string
  platform_version: string
  machine: string
  processor: string
  cpu_percent: number | null
  memory_percent: number | null
  disk_usage?: Record<string, { used: number; free: number }>
  uptime_seconds?: number
}

interface Process {
  pid: number
  name: string
  cpu_percent: number
  memory_mb: number
  status: string
}

interface Service {
  Name: string
  Status: string
  StartType: string
}

interface Drive {
  device_id: string
  total_gb: number
  free_gb: number
  used_gb: number
  used_percent: number
}

interface Adapter {
  Name: string
  Status: string
  LinkSpeed: string
  MacAddress: string
  bytes_sent?: number
  bytes_recv?: number
}

interface BatteryItem {
  EstimatedChargeRemaining?: number
  BatteryStatus?: number
}

interface Toast {
  id: string
  message: string
  type: 'success' | 'error'
}

interface NetworkItem {
  name: string
  signal?: number
  connected?: boolean
}

type TabKey = 'overview' | 'processes' | 'services' | 'terminal' | 'voice' | 'profiler' | 'updates' | 'events' | 'hud'

export function DeviceControlPanel() {
  const [activeTab, setActiveTab] = useState<TabKey>('overview')
  const [info, setInfo] = useState<SystemInfo | null>(null)
  const [infoLoading, setInfoLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [volume, setVolume] = useState(50)
  const [muted, setMuted] = useState(false)
  const [brightness, setBrightness] = useState(50)
  const [lastAction, setLastAction] = useState<{ action: string; result: string } | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [processes, setProcesses] = useState<Process[]>([])
  const [procLoading, setProcLoading] = useState(false)
  const [services, setServices] = useState<Service[]>([])
  const [svcLoading, setSvcLoading] = useState(false)
  const [diskInfo, setDiskInfo] = useState<Drive[]>([])
  const [diskLoading, setDiskLoading] = useState(false)
  const [networkInfo, setNetworkInfo] = useState<Adapter[]>([])
  const [networkLoading, setNetworkLoading] = useState(false)
  const [batteryInfo, setBatteryInfo] = useState<BatteryItem[]>([])
  const [clipboardText, setClipboardText] = useState('')
  const [clipboardLoading, setClipboardLoading] = useState(false)
  const [wifiNetworks, setWifiNetworks] = useState<NetworkItem[]>([])
  const [bluetoothDevices, setBluetoothDevices] = useState<NetworkItem[]>([])
  const [wifiBtLoading, setWifiBtLoading] = useState(false)
  const [confirmDialog, setConfirmDialog] = useState<{ open: boolean; title: string; message: string; onConfirm: () => void } | null>(null)
  const [cpuHistory, setCpuHistory] = useState<number[]>([])
  const [memHistory, setMemHistory] = useState<number[]>([])
  const [profilerData, setProfilerData] = useState<Array<{pid: number; name: string; cpu_percent: number; memory_mb: number}>>([])
  const [profilerLoading, setProfilerLoading] = useState(false)
  const [updatesData, setUpdatesData] = useState<{pending: number; updates: Array<{title: string; downloaded: boolean}>}>({ pending: 0, updates: [] })
  const [updatesLoading, setUpdatesLoading] = useState(false)
  const [eventsData, setEventsData] = useState<Array<{TimeCreated: string; LevelDisplayName: string; Message: string}>>([])
  const [eventsLoading, setEventsLoading] = useState(false)
  const [hudOpen, setHudOpen] = useState(false)
  const [diskHistory, setDiskHistory] = useState<number[]>([])
  const [netHistory, setNetHistory] = useState<Array<{sent: number; recv: number}>>([])
  const [coreData, setCoreData] = useState<number[]>([])
  const clipboardInputRef = useRef<HTMLTextAreaElement>(null)

  // SSE live metrics stream — updates history in real-time
  const { metrics: liveMetrics, connected: streamConnected } = useDeviceStream(activeTab === 'overview')

  // Merge live SSE metrics into chart history
  useEffect(() => {
    if (liveMetrics) {
      setCpuHistory(prev => [...prev, liveMetrics.cpu].slice(-30))
      setMemHistory(prev => [...prev, liveMetrics.memory].slice(-30))
      setDiskHistory(prev => [...prev, liveMetrics.disk].slice(-30))
      setNetHistory(prev => [...prev, { sent: liveMetrics.net_sent, recv: liveMetrics.net_recv }].slice(-30))
    }
  }, [liveMetrics])

  const addToast = useCallback((message: string, type: 'success' | 'error') => {
    const id = Date.now().toString()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 3000)
  }, [])

  const fetchInfo = useCallback(async () => {
    try {
      const res = await fetch('/api/device/info')
      if (res.ok) {
        const raw = await res.json()
        const data: SystemInfo = {
          platform: raw.platform || 'Windows',
          platform_version: raw.platform_version || '',
          machine: raw.machine || '',
          processor: raw.processor || '',
          cpu_percent: raw.cpu_percent ?? null,
          memory_percent: raw.memory_percent ?? null,
          disk_usage: raw.disk_usage,
          uptime_seconds: raw.uptime_seconds,
        }
        setInfo(data)
        setCpuHistory(prev => {
          const next = [...prev, data.cpu_percent ?? 0].slice(-30)
          return next
        })
        setMemHistory(prev => {
          const next = [...prev, data.memory_percent ?? 0].slice(-30)
          return next
        })
        // Calculate disk usage percentage from disk_usage
        const diskPercent = data.disk_usage
          ? Math.round(
              Object.values(data.disk_usage).reduce((sum, d) => sum + (d.used / (d.used + d.free)), 0) /
                Object.keys(data.disk_usage).length * 100
            )
          : 0
        setDiskHistory(prev => [...prev, diskPercent].slice(-30))
      }
    } catch (err) {
      console.error('fetchInfo error:', err)
    } finally {
      setInfoLoading(false)
    }
  }, [])

  const fetchProcesses = useCallback(async () => {
    setProcLoading(true)
    try {
      const res = await fetch('/api/device/processes')
      if (res.ok) {
        const raw = await res.json()
        const rawProcs: Array<Record<string, unknown>> = raw.processes || []
        const mapped: Process[] = rawProcs.map((p) => ({
          pid: (p.Id as number) || (p.id as number) || (p.pid as number) || 0,
          name: (p.Name as string) || (p.name as string) || 'Unknown',
          cpu_percent: (p.CPU as number) || (p.cpu_percent as number) || 0,
          memory_mb: ((p.WorkingSet as number) || (p.memory_mb as number) || 0) / 1024 / 1024,
          status: (p.Status as string) || (p.status as string) || 'running',
        }))
        setProcesses(mapped)
      }
    } catch (err) {
      console.error('fetchProcesses error:', err)
    } finally {
      setProcLoading(false)
    }
  }, [])

  const fetchServices = useCallback(async () => {
    setSvcLoading(true)
    try {
      const res = await fetch('/api/device/services')
      if (res.ok) {
        const raw = await res.json()
        const rawSvcs: Service[] = raw.services || []
        setServices(rawSvcs)
      }
    } catch (err) {
      console.error('fetchServices error:', err)
    } finally {
      setSvcLoading(false)
    }
  }, [])

  const fetchDisk = useCallback(async () => {
    setDiskLoading(true)
    try {
      const res = await fetch('/api/device/disk')
      if (res.ok) {
        const raw = await res.json()
        const drives: Drive[] = raw.drives || []
        setDiskInfo(drives)
        // Update disk history from drive data
        const diskPercent = drives.length
          ? Math.round(drives.reduce((sum, d) => sum + (d.used_gb / d.total_gb), 0) / drives.length * 100)
          : 0
        setDiskHistory((prev) => [...prev, diskPercent].slice(-30))
      }
    } catch (err) {
      console.error('fetchDisk error:', err)
    } finally {
      setDiskLoading(false)
    }
  }, [])

  const fetchNetwork = useCallback(async () => {
    setNetworkLoading(true)
    try {
      const res = await fetch('/api/device/network')
      if (res.ok) {
        const raw = await res.json()
        const adapters: Adapter[] = raw.adapters || []
        setNetworkInfo(adapters)
        // Track total network throughput
        const totalSent = adapters.reduce((sum, a) => sum + (a.bytes_sent || 0), 0)
        const totalRecv = adapters.reduce((sum, a) => sum + (a.bytes_recv || 0), 0)
        setNetHistory(prev => [...prev, { sent: totalSent, recv: totalRecv }].slice(-30))
      }
    } catch (err) {
      console.error('fetchNetwork error:', err)
    } finally {
      setNetworkLoading(false)
    }
  }, [])

  const fetchBattery = useCallback(async () => {
    try {
      const res = await fetch('/api/device/battery')
      if (res.ok) {
        const raw = await res.json()
        const batteries: BatteryItem[] = raw.battery || []
        setBatteryInfo(batteries)
      }
    } catch (err) {
      console.error('fetchBattery error:', err)
    }
  }, [])

  const fetchProfiler = useCallback(async () => {
    setProfilerLoading(true)
    try {
      const res = await fetch('/api/device/profiler')
      if (res.ok) {
        const raw = await res.json()
        const procs = raw.processes || []
        setProfilerData(procs.map((p: { Id?: number; pid?: number; Name?: string; name?: string; CPU?: number; cpu_percent?: number; WorkingSet?: number; memory_mb?: number }) => ({
          pid: p.Id || p.pid || 0,
          name: p.Name || p.name || 'Unknown',
          cpu_percent: p.CPU || p.cpu_percent || 0,
          memory_mb: (p.WorkingSet || p.memory_mb || 0) / 1024 / 1024,
        })))
      }
    } catch (err) {
      console.error('fetchProfiler error:', err)
    } finally {
      setProfilerLoading(false)
    }
  }, [])

  const fetchUpdates = useCallback(async () => {
    setUpdatesLoading(true)
    try {
      const res = await fetch('/api/device/updates')
      if (res.ok) {
        const raw = await res.json()
        setUpdatesData({
          pending: raw.pending || 0,
          updates: raw.updates || [],
        })
      }
    } catch (err) {
      console.error('fetchUpdates error:', err)
    } finally {
      setUpdatesLoading(false)
    }
  }, [])

  const fetchEvents = useCallback(async () => {
    setEventsLoading(true)
    try {
      const res = await fetch('/api/device/events')
      if (res.ok) {
        const raw = await res.json()
        setEventsData(raw.events || [])
      }
    } catch (err) {
      console.error('fetchEvents error:', err)
    } finally {
      setEventsLoading(false)
    }
  }, [])

  const fetchCores = useCallback(async () => {
    try {
      const res = await fetch('/api/device/cores')
      if (res.ok) {
        const raw = await res.json()
        setCoreData(raw.cores || [])
      }
    } catch (err) {
      console.error('fetchCores error:', err)
    }
  }, [])

  const fetchClipboard = useCallback(async () => {
    setClipboardLoading(true)
    try {
      const res = await fetch('/api/device/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'clipboard', params: { action: 'get' } }),
      })
      const data = await res.json()
      if (data.success && data.output) {
        setClipboardText(data.output)
      }
    } catch {
      // ignore
    } finally {
      setClipboardLoading(false)
    }
  }, [])

  const fetchWifiBt = useCallback(async () => {
    setWifiBtLoading(true)
    try {
      const [wifiRes, btRes] = await Promise.all([
        fetch('/api/device/action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'wifi', params: { action: 'list' } }),
        }),
        fetch('/api/device/action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'bluetooth', params: { action: 'list' } }),
        }),
      ])
      const wifiData = wifiRes.ok ? await wifiRes.json() : null
      const btData = btRes.ok ? await btRes.json() : null
      if (wifiData?.success && Array.isArray(wifiData.output)) {
        setWifiNetworks(wifiData.output)
      } else if (wifiData?.success && typeof wifiData.output === 'string') {
        setWifiNetworks(wifiData.output.split('\n').filter(Boolean).map((n: string) => ({ name: n.trim() })))
      }
      if (btData?.success && Array.isArray(btData.output)) {
        setBluetoothDevices(btData.output)
      } else if (btData?.success && typeof btData.output === 'string') {
        setBluetoothDevices(btData.output.split('\n').filter(Boolean).map((n: string) => ({ name: n.trim() })))
      }
    } catch {
      // ignore
    } finally {
      setWifiBtLoading(false)
    }
  }, [])

  // Polling: info always runs; other tabs fetch on mount + when active
  useEffect(() => {
    fetchInfo()
    fetchProcesses()
    fetchProfiler()
    fetchUpdates()
    fetchProfiler()
    fetchUpdates()
    fetchClipboard()
    fetchWifiBt()
    fetchDisk()
    fetchNetwork()
    fetchBattery()
    fetchServices()
    fetchEvents()
    fetchCores()

    const infoInterval = setInterval(fetchInfo, 3000)
    const procInterval = setInterval(fetchProcesses, 5000)

    return () => {
      clearInterval(infoInterval)
      clearInterval(procInterval)
    }
  }, [fetchInfo, fetchProcesses, fetchClipboard, fetchWifiBt, fetchDisk, fetchNetwork, fetchBattery, fetchServices, fetchProfiler, fetchUpdates, fetchEvents, fetchCores])

  // Tab-specific polling
  useEffect(() => {
    if (activeTab !== 'services') return
    fetchServices()
    const interval = setInterval(fetchServices, 5000)
    return () => clearInterval(interval)
  }, [activeTab, fetchServices])

  useEffect(() => {
    if (activeTab !== 'profiler') return
    fetchProfiler()
    const interval = setInterval(fetchProfiler, 5000)
    return () => clearInterval(interval)
  }, [activeTab, fetchProfiler])

  useEffect(() => {
    if (activeTab !== 'updates') return
    fetchUpdates()
  }, [activeTab, fetchUpdates])

  useEffect(() => {
    if (activeTab !== 'events') return
    fetchEvents()
    const interval = setInterval(fetchEvents, 10000)
    return () => clearInterval(interval)
  }, [activeTab, fetchEvents])

  useEffect(() => {
    if (activeTab !== 'overview') return
    fetchCores()
    const interval = setInterval(fetchCores, 3000)
    return () => clearInterval(interval)
  }, [activeTab, fetchCores])

  const runAction = async (action: string, params?: Record<string, unknown>) => {
    setActionLoading(action)
    try {
      const res = await fetch('/api/device/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, params: params || {} }),
      })
      const data = await res.json()
      const success = data.success ?? res.ok
      setLastAction({ action, result: success ? 'OK' : data.output || 'Failed' })
      addToast(`${action}: ${success ? 'Success' : data.output || 'Failed'}`, success ? 'success' : 'error')
      return data
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error'
      setLastAction({ action, result: msg })
      addToast(`${action}: ${msg}`, 'error')
      return null
    } finally {
      setActionLoading(null)
    }
  }

  const handleVolume = async (val: number) => {
    setVolume(val)
    setMuted(false)
    await runAction('volume', { level: val })
  }

  const handleMuteToggle = async () => {
    const next = !muted
    setMuted(next)
    await runAction(next ? 'mute' : 'volume', next ? {} : { level: volume })
  }

  const handleBrightness = async (val: number) => {
    setBrightness(val)
    await runAction('brightness', { level: val })
  }

  const handleMediaKey = async (key: string) => {
    await runAction('media_key', { key })
  }

  const handleKillProcess = async (pid: number, name: string) => {
    if (!confirm(`Kill process "${name}" (PID ${pid})?`)) return
    await runAction('kill_process', { pid })
    fetchProcesses()
  }

  const handleServiceAction = async (name: string, action: 'start' | 'stop' | 'restart') => {
    setSvcLoading(true)
    try {
      const res = await fetch(`/api/device/services/${encodeURIComponent(name)}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      })
      const data = await res.json()
      addToast(`${name}: ${action} ${data.success ? 'OK' : data.output || 'Failed'}`, data.success ? 'success' : 'error')
      fetchServices()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error'
      addToast(`${name}: ${action} ${msg}`, 'error')
    } finally {
      setSvcLoading(false)
    }
  }

  const runTerminalCommand = async (command: string) => {
    const res = await fetch('/api/device/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'run_command', params: { command } }),
    })
    const data = await res.json()
    if (!data.success) {
      throw new Error(data.output || 'Command failed')
    }
    return data.output as string
  }

  const handleCopyToClipboard = async () => {
    const text = clipboardInputRef.current?.value || ''
    if (!text) return
    await runAction('clipboard', { action: 'set', text })
    addToast('Copied to clipboard', 'success')
  }

  const handleShutdown = () => {
    setConfirmDialog({
      open: true,
      title: 'Shutdown',
      message: 'Are you sure you want to shut down the computer?',
      onConfirm: async () => {
        setConfirmDialog(null)
        await runAction('shutdown')
      },
    })
  }

  const handleRestart = () => {
    setConfirmDialog({
      open: true,
      title: 'Restart',
      message: 'Are you sure you want to restart the computer?',
      onConfirm: async () => {
        setConfirmDialog(null)
        await runAction('restart')
      },
    })
  }

  const formatUptime = (seconds?: number) => {
    if (seconds == null) return '—'
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    return `${h}h ${m}m`
  }

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'overview', label: 'Overview', icon: <LayoutDashboard className="h-3.5 w-3.5" /> },
    { key: 'processes', label: 'Processes', icon: <List className="h-3.5 w-3.5" /> },
    { key: 'services', label: 'Services', icon: <Cog className="h-3.5 w-3.5" /> },
    { key: 'terminal', label: 'Terminal', icon: <TerminalIcon className="h-3.5 w-3.5" /> },
    { key: 'voice', label: 'Voice', icon: <Mic className="h-3.5 w-3.5" /> },
    { key: 'profiler', label: 'Profiler', icon: <TrendingUp className="h-3.5 w-3.5" /> },
    { key: 'updates', label: 'Updates', icon: <AlertCircle className="h-3.5 w-3.5" /> },
    { key: 'events', label: 'Events', icon: <ScrollText className="h-3.5 w-3.5" /> },
    { key: 'hud', label: 'HUD', icon: <Maximize2 className="h-3.5 w-3.5" /> },
  ]

  return (
    <div className="space-y-4 relative">
      {/* Toasts */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm shadow-lg border ${
              t.type === 'success'
                ? 'bg-green-500/10 border-green-500/20 text-green-400'
                : 'bg-red-500/10 border-red-500/20 text-red-400'
            }`}
          >
            {t.type === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            {t.message}
          </div>
        ))}
      </div>

      {/* Confirm Dialog */}
      {confirmDialog?.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="rounded-lg border border-white/6 bg-[var(--bg-elevated)] p-6 w-80 space-y-4">
            <div className="flex items-center gap-2 text-accent-red">
              <AlertTriangle className="h-5 w-5" />
              <h3 className="font-semibold">{confirmDialog.title}</h3>
            </div>
            <p className="text-sm text-[var(--text-secondary)]">{confirmDialog.message}</p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setConfirmDialog(null)}
                className="rounded-lg px-3 py-1.5 text-xs font-medium bg-white/5 text-[var(--text-secondary)] hover:bg-white/10 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmDialog.onConfirm}
                className="rounded-lg px-3 py-1.5 text-xs font-medium bg-accent-red/10 text-accent-red hover:bg-accent-red/20 transition-colors"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Monitor className="h-4 w-4 text-jarvis-cyan" />
          <h2 className="text-sm font-display font-bold uppercase tracking-wider text-jarvis-text-primary">
            Device Control
          </h2>
          <div className="live-pulse" style={{ '--pulse-color': '#00F0FF' } as React.CSSProperties} />
        </div>
        <button
          onClick={() => setHudOpen(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded border border-jarvis-cyan/30 text-jarvis-cyan text-xs font-display uppercase tracking-wider hover:bg-jarvis-cyan/20 transition-colors"
        >
          <Maximize2 className="h-3 w-3" />
          HUD
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-white/6 pb-1">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-display uppercase tracking-wider transition-all ${
              activeTab === tab.key
                ? 'text-jarvis-cyan border-b-2 border-jarvis-cyan shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                : 'text-jarvis-text-muted hover:text-jarvis-text-secondary'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          {/* System Charts — already has jarvis-card */}
          <SystemCharts cpuData={cpuHistory} memData={memHistory} diskData={diskHistory} netData={netHistory} />

          {/* CPU Heatmap + Info Cards Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* CPU Heatmap — already has jarvis-card */}
            <CpuHeatmap cores={coreData} />

            {/* System Info Cards */}
            <div className="jarvis-card p-4 space-y-3">
              <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
                <Monitor className="h-3.5 w-3.5 text-jarvis-cyan" />
                System Info
              </div>
              {infoLoading && info == null ? (
                <div className="h-24 rounded-md bg-white/5 animate-pulse" />
              ) : (
                <>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="rounded-md bg-white/5 p-2 space-y-1">
                      <div className="flex items-center gap-1 text-[10px] text-jarvis-text-muted">
                        <Cpu className="h-3 w-3" /> CPU
                      </div>
                      <div className="text-sm font-mono font-semibold text-jarvis-cyan">
                        {info?.cpu_percent != null ? `${info.cpu_percent.toFixed(1)}%` : '—'}
                      </div>
                    </div>
                    <div className="rounded-md bg-white/5 p-2 space-y-1">
                      <div className="flex items-center gap-1 text-[10px] text-jarvis-text-muted">
                        <HardDrive className="h-3 w-3" /> RAM
                      </div>
                      <div className="text-sm font-mono font-semibold text-jarvis-green">
                        {info?.memory_percent != null ? `${info.memory_percent.toFixed(1)}%` : '—'}
                      </div>
                    </div>
                    <div className="rounded-md bg-white/5 p-2">
                      <div className="flex items-center gap-1 text-[10px] text-jarvis-text-muted">
                        <HardDrive className="h-3 w-3" /> Disk
                      </div>
                      <div className="text-sm font-mono font-semibold text-jarvis-amber">
                        {info?.disk_usage
                          ? Object.entries(info.disk_usage)
                              .map(([d, u]) => `${d}: ${((u.used / (u.used + u.free)) * 100).toFixed(0)}%`)
                              .join(', ')
                          : '—'}
                      </div>
                    </div>
                    <div className="rounded-md bg-white/5 p-2">
                      <div className="flex items-center gap-1 text-[10px] text-jarvis-text-muted">
                        <Clock className="h-3 w-3" /> Uptime
                      </div>
                      <div className="text-sm font-mono font-semibold text-jarvis-green">
                        {formatUptime(info?.uptime_seconds)}
                      </div>
                    </div>
                  </div>
                  <div className="text-[10px] text-jarvis-text-muted font-mono">
                    {info?.platform} {info?.platform_version} · {info?.machine}
                  </div>
                  {/* SSE Stream Status */}
                  <div className="flex items-center gap-2 text-[10px]">
                    <div className={`h-1.5 w-1.5 rounded-full ${streamConnected ? 'bg-jarvis-green animate-pulse' : 'bg-jarvis-red'}`} />
                    <span className={streamConnected ? 'text-jarvis-green' : 'text-jarvis-red'}>
                      {streamConnected ? 'Live stream connected' : 'Live stream offline'}
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Process Tree — already has jarvis-card */}
          <ProcessTree
            processes={processes.map(p => ({
              pid: p.pid,
              name: p.name,
              cpu_percent: p.cpu_percent,
              memory_mb: p.memory_mb,
              status: p.status,
              children: [],
            }))}
          />

          {/* Disk Drives */}
          <div className="jarvis-card p-4 space-y-3">
            <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
              <HardDrive className="h-3.5 w-3.5 text-jarvis-cyan" />
              Disk Drives
            </div>
            {diskLoading && diskInfo.length === 0 ? (
              <div className="h-16 rounded-md bg-white/5 animate-pulse" />
            ) : diskInfo.length === 0 ? (
              <div className="text-xs text-jarvis-text-muted">No disk data available</div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {diskInfo.map(d => (
                  <div key={d.device_id} className="rounded-md bg-white/5 p-2 space-y-1">
                    <div className="flex items-center justify-between text-[10px] text-jarvis-text-muted">
                      <span>Drive {d.device_id}</span>
                      <span className="font-mono">{d.used_percent.toFixed(0)}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-jarvis-amber transition-all"
                        style={{ width: `${Math.min(d.used_percent, 100)}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-jarvis-text-muted">
                      <span>{d.used_gb.toFixed(1)} GB used</span>
                      <span>{d.free_gb.toFixed(1)} GB free</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Network Adapters */}
          <div className="jarvis-card p-4 space-y-3">
            <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
              <Network className="h-3.5 w-3.5 text-jarvis-cyan" />
              Network
            </div>
            {networkLoading && networkInfo.length === 0 ? (
              <div className="h-16 rounded-md bg-white/5 animate-pulse" />
            ) : networkInfo.length === 0 ? (
              <div className="text-xs text-jarvis-text-muted">No network adapters found</div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {networkInfo.map((a, i) => (
                  <div key={`${a.Name}-${i}`} className="rounded-md bg-white/5 p-2 space-y-1">
                    <div className="text-xs text-jarvis-text-primary font-medium truncate">{a.Name}</div>
                    <div className="text-[10px] text-jarvis-text-muted">Status: {a.Status}</div>
                    <div className="text-[10px] text-jarvis-text-muted">Speed: {a.LinkSpeed}</div>
                    <div className="text-[10px] text-jarvis-text-muted font-mono truncate">{a.MacAddress}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Battery */}
          {batteryInfo.length > 0 && (
            <div className="jarvis-card p-4 space-y-3">
              <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
                <Battery className="h-3.5 w-3.5 text-jarvis-cyan" />
                Battery
              </div>
              {batteryInfo.map((b, i) => (
                <div key={i} className="rounded-md bg-white/5 p-2 space-y-1">
                  <div className="flex items-center justify-between text-[10px] text-jarvis-text-muted">
                    <span>Charge Remaining</span>
                    <span className="font-mono text-jarvis-green">{b.EstimatedChargeRemaining ?? '—'}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-jarvis-green transition-all"
                      style={{ width: `${Math.min(b.EstimatedChargeRemaining ?? 0, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Media Controls */}
          <div className="jarvis-card p-4 space-y-3">
            <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
              <Activity className="h-3.5 w-3.5 text-jarvis-cyan" />
              Media Controls
            </div>
            {/* Volume */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] text-jarvis-text-muted">
                <span className="flex items-center gap-1">
                  {muted ? <VolumeX className="h-3 w-3" /> : <Volume2 className="h-3 w-3" />}
                  Volume
                </span>
                <span className="font-mono">{muted ? 'Muted' : `${volume}%`}</span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={volume}
                  onChange={(e) => handleVolume(Number(e.target.value))}
                  className="flex-1 accent-jarvis-cyan h-1.5 rounded-lg appearance-none bg-white/10 cursor-pointer"
                />
                <button
                  onClick={handleMuteToggle}
                  className={`rounded-md p-1.5 transition-colors ${
                    muted ? 'bg-jarvis-red/10 text-jarvis-red' : 'bg-white/5 text-jarvis-text-muted hover:bg-white/10'
                  }`}
                  title={muted ? 'Unmute' : 'Mute'}
                >
                  {muted ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
                </button>
              </div>
            </div>
            {/* Brightness */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] text-jarvis-text-muted">
                <span className="flex items-center gap-1">
                  <Sun className="h-3 w-3" />
                  Brightness
                </span>
                <span className="font-mono">{brightness}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={brightness}
                onChange={(e) => handleBrightness(Number(e.target.value))}
                className="w-full accent-jarvis-amber h-1.5 rounded-lg appearance-none bg-white/10 cursor-pointer"
              />
            </div>
            {/* Media Keys */}
            <div className="flex items-center gap-2">
              <ActionButton
                icon={<SkipBack className="h-4 w-4" />}
                label="Prev"
                onClick={() => handleMediaKey('prev')}
                loading={actionLoading === 'media_key'}
                compact
              />
              <ActionButton
                icon={<Play className="h-4 w-4" />}
                label="Play"
                onClick={() => handleMediaKey('play_pause')}
                loading={actionLoading === 'media_key'}
                compact
              />
              <ActionButton
                icon={<Pause className="h-4 w-4" />}
                label="Pause"
                onClick={() => handleMediaKey('play_pause')}
                loading={actionLoading === 'media_key'}
                compact
              />
              <ActionButton
                icon={<SkipForward className="h-4 w-4" />}
                label="Next"
                onClick={() => handleMediaKey('next')}
                loading={actionLoading === 'media_key'}
                compact
              />
              <ActionButton
                icon={<Square className="h-4 w-4" />}
                label="Stop"
                onClick={() => handleMediaKey('stop')}
                loading={actionLoading === 'media_key'}
                compact
              />
            </div>
          </div>

          {/* Quick Actions Grid */}
          <div className="jarvis-card p-4 space-y-3">
            <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
              <Zap className="h-3.5 w-3.5 text-jarvis-cyan" />
              Quick Actions
            </div>
            <div className="grid grid-cols-2 gap-2">
              <ActionButton
                icon={<Globe className="h-4 w-4" />}
                label="Open Chrome"
                onClick={() => runAction('open_app', { app: 'chrome' })}
                loading={actionLoading === 'open_app'}
              />
              <ActionButton
                icon={<FileText className="h-4 w-4" />}
                label="Open Notepad"
                onClick={() => runAction('open_app', { app: 'notepad' })}
                loading={actionLoading === 'open_app'}
              />
              <ActionButton
                icon={<Camera className="h-4 w-4" />}
                label="Screenshot"
                onClick={() => runAction('screenshot')}
                loading={actionLoading === 'screenshot'}
              />
              <ActionButton
                icon={<Lock className="h-4 w-4" />}
                label="Lock PC"
                onClick={() => runAction('lock')}
                loading={actionLoading === 'lock'}
              />
              <ActionButton
                icon={<VolumeX className="h-4 w-4" />}
                label="Mute"
                onClick={() => runAction('mute')}
                loading={actionLoading === 'mute'}
              />
              <ActionButton
                icon={<Zap className="h-4 w-4" />}
                label="Sleep"
                onClick={() => runAction('sleep')}
                loading={actionLoading === 'sleep'}
              />
              <ActionButton
                icon={<Trash2 className="h-4 w-4" />}
                label="Empty Recycle Bin"
                onClick={() => runAction('empty_trash')}
                loading={actionLoading === 'empty_trash'}
              />
              <ActionButton
                icon={<Clipboard className="h-4 w-4" />}
                label="Clear Clipboard"
                onClick={() => runAction('clipboard', { action: 'clear' })}
                loading={actionLoading === 'clipboard'}
              />
            </div>
          </div>

          {/* Safety: Shutdown & Restart */}
          <div className="jarvis-card p-4 space-y-3">
            <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
              <AlertTriangle className="h-3.5 w-3.5 text-jarvis-red" />
              Power
            </div>
            <div className="grid grid-cols-2 gap-2">
              <ActionButton
                icon={<Power className="h-4 w-4" />}
                label="Shutdown"
                onClick={handleShutdown}
                loading={actionLoading === 'shutdown'}
                danger
              />
              <ActionButton
                icon={<RotateCcw className="h-4 w-4" />}
                label="Restart"
                onClick={handleRestart}
                loading={actionLoading === 'restart'}
                danger
              />
            </div>
          </div>

          {/* Clipboard */}
          <div className="jarvis-card p-4 space-y-3">
            <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
              <Clipboard className="h-3.5 w-3.5 text-jarvis-cyan" />
              Clipboard
            </div>
            <textarea
              ref={clipboardInputRef}
              defaultValue={clipboardText}
              placeholder="Clipboard content..."
              className="w-full h-20 rounded-md bg-white/5 border border-white/6 px-2 py-1.5 text-xs text-jarvis-text-primary placeholder:text-jarvis-text-muted resize-none focus:outline-none focus:border-jarvis-cyan/50"
            />
            <div className="flex items-center gap-2">
              <button
                onClick={fetchClipboard}
                disabled={clipboardLoading}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium bg-white/5 text-jarvis-text-secondary hover:bg-white/10 hover:text-jarvis-text-primary transition-colors disabled:opacity-40"
              >
                {clipboardLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <ChevronDown className="h-3 w-3" />}
                Refresh
              </button>
              <button
                onClick={handleCopyToClipboard}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium bg-jarvis-cyan/10 text-jarvis-cyan hover:bg-jarvis-cyan/20 transition-colors"
              >
                <Clipboard className="h-3 w-3" />
                Copy to Clipboard
              </button>
            </div>
          </div>

          {/* WiFi / Bluetooth */}
          <div className="jarvis-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
                <Wifi className="h-3.5 w-3.5 text-jarvis-cyan" />
                Network
              </div>
              <button
                onClick={fetchWifiBt}
                disabled={wifiBtLoading}
                className="flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-medium bg-white/5 text-jarvis-text-muted hover:bg-white/10 transition-colors disabled:opacity-40"
              >
                {wifiBtLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <ChevronUp className="h-3 w-3" />}
                Refresh
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-1 text-[10px] text-jarvis-text-muted uppercase">
                  <Wifi className="h-3 w-3" />
                  WiFi Networks
                </div>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {wifiNetworks.length === 0 ? (
                    <div className="text-xs text-jarvis-text-muted py-1">No networks found</div>
                  ) : (
                    wifiNetworks.map((net, i) => (
                      <div
                        key={`wifi-${i}`}
                        className="flex items-center justify-between rounded-md bg-white/5 px-2 py-1 text-xs"
                      >
                        <span className="truncate text-jarvis-text-primary">{net.name}</span>
                        {net.connected && <span className="text-[10px] text-jarvis-green font-medium">Connected</span>}
                      </div>
                    ))
                  )}
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-1 text-[10px] text-jarvis-text-muted uppercase">
                  <Bluetooth className="h-3 w-3" />
                  Bluetooth Devices
                </div>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {bluetoothDevices.length === 0 ? (
                    <div className="text-xs text-jarvis-text-muted py-1">No devices found</div>
                  ) : (
                    bluetoothDevices.map((dev, i) => (
                      <div
                        key={`bt-${i}`}
                        className="flex items-center justify-between rounded-md bg-white/5 px-2 py-1 text-xs"
                      >
                        <span className="truncate text-jarvis-text-primary">{dev.name}</span>
                        {dev.connected && <span className="text-[10px] text-jarvis-cyan font-medium">Paired</span>}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Last Action */}
          {lastAction && (
            <div className="jarvis-card p-3">
              <div className="flex items-center gap-2 text-xs text-jarvis-text-muted">
                <Activity className="h-3 w-3" />
                <span>Last: {lastAction.action} → {lastAction.result}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Processes Tab */}
      {activeTab === 'processes' && (
        <div className="jarvis-card p-4 space-y-3">
          <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
            <Cpu className="h-3.5 w-3.5 text-jarvis-cyan" />
            Processes
          </div>
          <ProcessManager processes={processes} onKill={handleKillProcess} loading={procLoading} />
        </div>
      )}

      {/* Services Tab */}
      {activeTab === 'services' && (
        <div className="jarvis-card p-4 space-y-3">
          <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
            <Cog className="h-3.5 w-3.5 text-jarvis-cyan" />
            Services
          </div>
          <ServiceManager services={services} onAction={handleServiceAction} loading={svcLoading} />
        </div>
      )}

      {/* Terminal Tab */}
      {activeTab === 'terminal' && (
        <div className="jarvis-card p-4 space-y-3">
          <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
            <TerminalIcon className="h-3.5 w-3.5 text-jarvis-cyan" />
            Terminal
          </div>
          <SystemTerminal onExecute={runTerminalCommand} />
        </div>
      )}

      {/* Voice Tab */}
      {activeTab === 'voice' && (
        <div className="jarvis-card p-4">
          <VoiceCommandPanel />
        </div>
      )}

      {/* Profiler Tab */}
      {activeTab === 'profiler' && (
        <div className="jarvis-card p-4">
          <PerformanceProfiler
            data={profilerData}
            loading={profilerLoading}
          />
        </div>
      )}

      {/* Updates Tab */}
      {activeTab === 'updates' && (
        <div className="jarvis-card p-4 space-y-3">
          <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
            <Shield className="h-3.5 w-3.5 text-jarvis-cyan" />
            Windows Update
          </div>
          <WindowsUpdate
            updates={updatesData.updates}
            pending={updatesData.pending}
            loading={updatesLoading}
            onCheck={fetchUpdates}
          />
        </div>
      )}

      {/* Events Tab */}
      {activeTab === 'events' && (
        <div className="jarvis-card p-4 space-y-3">
          <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
            <ScrollText className="h-3.5 w-3.5 text-jarvis-cyan" />
            System Event Log
          </div>
          <SystemEventLog
            events={eventsData}
            loading={eventsLoading}
            onRefresh={fetchEvents}
          />
        </div>
      )}

      {/* HUD Tab */}
      {activeTab === 'hud' && (
        <div className="jarvis-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-display font-semibold uppercase tracking-wider text-jarvis-text-secondary">
              <Maximize2 className="h-3.5 w-3.5 text-jarvis-cyan" />
              Jarvis HUD
            </div>
            <button
              onClick={() => setHudOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded border border-jarvis-cyan/30 text-jarvis-cyan text-xs font-display uppercase tracking-wider hover:bg-jarvis-cyan/20 transition-colors"
            >
              <Maximize2 className="h-3 w-3" />
              Launch Fullscreen
            </button>
          </div>
          <p className="text-xs text-jarvis-text-muted">
            Click "Launch Fullscreen" to open the immersive Jarvis system monitor overlay.
          </p>
        </div>
      )}

      {/* HUD Overlay */}
      {hudOpen && info && (
        <JarvisHUD
          cpu={info.cpu_percent}
          memory={info.memory_percent}
          disk={diskHistory[diskHistory.length - 1] ?? null}
          network={networkInfo[0] ? { bytes_sent: networkInfo[0].bytes_sent || 0, bytes_recv: networkInfo[0].bytes_recv || 0 } : null}
          uptime={info.uptime_seconds || 0}
          processes={processes.slice(0, 5).map(p => ({ name: p.name, cpu_percent: p.cpu_percent, memory_mb: p.memory_mb }))}
          onClose={() => setHudOpen(false)}
        />
      )}
    </div>
  )
}

function ActionButton({
  icon,
  label,
  onClick,
  loading,
  danger,
  compact,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
  loading?: boolean
  danger?: boolean
  compact?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`flex items-center gap-2 rounded-lg text-xs font-medium transition-colors w-full ${
        danger
          ? 'bg-accent-red/10 text-accent-red hover:bg-accent-red/20'
          : 'bg-white/5 text-[var(--text-secondary)] hover:bg-white/10 hover:text-[var(--text-primary)]'
      } disabled:opacity-40 disabled:cursor-not-allowed ${compact ? 'px-2 py-1.5 justify-center' : 'px-3 py-2.5'}`}
    >
      {loading ? (
        <div className="h-3 w-3 rounded-full border-2 border-current border-t-transparent animate-spin" />
      ) : (
        icon
      )}
      <span className={compact ? 'hidden sm:inline' : ''}>{label}</span>
    </button>
  )
}
