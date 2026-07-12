import { useState, useEffect } from 'react'
import { Cpu, HardDrive, Clock, Activity, Zap } from 'lucide-react'

interface DiskUsageEntry {
  used: number
  free: number
}

interface DeviceInfoData {
  cpu_percent?: number
  memory_percent?: number
  uptime_seconds?: number
  disk_usage?: Record<string, DiskUsageEntry>
}

interface DeviceSidebarCompactProps {
  cpu: number | null
  memory: number | null
  disk: number | null
  uptime: number
  processes: Array<{ name: string; cpu_percent: number }>
}

function getStatusColor(value: number | null): string {
  if (value === null) return '#525252'
  if (value >= 80) return '#FF1A1A'
  if (value >= 50) return '#EAB308'
  return '#00F0FF'
}

function getStatusGlow(value: number | null): string {
  if (value === null) return 'rgba(82, 82, 82, 0.3)'
  if (value >= 80) return 'rgba(255, 26, 26, 0.3)'
  if (value >= 50) return 'rgba(234, 179, 8, 0.3)'
  return 'rgba(0, 240, 255, 0.3)'
}

interface MetricCardProps {
  icon: React.ReactNode
  label: string
  value: number | null
  suffix?: string
}

function MetricCard({ icon, label, value, suffix = '%' }: MetricCardProps) {
  const color = getStatusColor(value)
  const glow = getStatusGlow(value)
  return (
    <div
      className="jarvis-card corner-brackets p-3 space-y-2 hover:border-jarvis-cyan/30 transition-all duration-300"
      style={{ '--accent-color': color } as React.CSSProperties}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-[10px] text-jarvis-text-muted uppercase font-display tracking-wider">
          {icon}
          {label}
        </div>
        <div className="live-pulse" style={{ '--pulse-color': color } as React.CSSProperties} />
      </div>
      <div
        className="text-xl font-mono font-bold text-glow"
        style={{ color, '--glow-color': glow } as React.CSSProperties}
      >
        {value != null ? `${value.toFixed(1)}${suffix}` : '—'}
      </div>
      <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500 progress-glow"
          style={{
            width: `${Math.min(value ?? 0, 100)}%`,
            backgroundColor: color,
            '--bar-color': glow,
          } as React.CSSProperties}
        />
      </div>
    </div>
  )
}

export function DeviceSidebarCompact({ cpu, memory, disk, uptime, processes }: DeviceSidebarCompactProps) {
  const [liveCpu, setLiveCpu] = useState<number | null>(cpu)
  const [liveMem, setLiveMem] = useState<number | null>(memory)
  const [liveDisk, setLiveDisk] = useState<number | null>(disk)
  const [liveUptime, setLiveUptime] = useState<number>(uptime)

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/device/info')
        if (res.ok) {
          const data: DeviceInfoData = await res.json()
          setLiveCpu(data.cpu_percent ?? null)
          setLiveMem(data.memory_percent ?? null)
          setLiveUptime(data.uptime_seconds ?? 0)
          const entries = data.disk_usage ? Object.values(data.disk_usage) : []
          const diskPercent = entries.length
            ? Math.round(
                entries.reduce((sum: number, d: DiskUsageEntry) => sum + (d.used / (d.used + d.free)), 0) /
                  entries.length * 100
              )
            : 0
          setLiveDisk(diskPercent)
        }
      } catch {
        // ignore
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  const formatUptime = (seconds: number) => {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    return `${h.toString().padStart(2, '0')}h ${m.toString().padStart(2, '0')}m`
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2 px-1">
        <Zap className="h-4 w-4 text-jarvis-cyan" />
        <span className="text-xs font-display uppercase tracking-wider text-jarvis-text-secondary">
          Live Metrics
        </span>
      </div>

      {/* CPU + RAM grid */}
      <div className="grid grid-cols-2 gap-2">
        <MetricCard
          icon={<Cpu className="h-3 w-3" />}
          label="CPU"
          value={liveCpu}
        />
        <MetricCard
          icon={<HardDrive className="h-3 w-3" />}
          label="RAM"
          value={liveMem}
        />
      </div>

      {/* Disk */}
      <MetricCard
        icon={<Activity className="h-3 w-3" />}
        label="Disk"
        value={liveDisk}
      />

      {/* Uptime */}
      <div className="jarvis-card p-3 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-[10px] text-jarvis-text-muted uppercase font-display tracking-wider">
          <Clock className="h-3 w-3" />
          Uptime
        </div>
        <div className="text-sm font-mono font-bold text-jarvis-green text-glow" style={{ '--glow-color': 'rgba(0,255,102,0.3)' } as React.CSSProperties}>
          {formatUptime(liveUptime)}
        </div>
      </div>

      {/* Top Processes */}
      <div className="jarvis-card p-3 space-y-2">
        <div className="flex items-center gap-2">
          <div className="live-pulse" style={{ '--pulse-color': '#00F0FF' } as React.CSSProperties} />
          <div className="text-[10px] text-jarvis-text-muted uppercase font-display font-semibold tracking-wider">
            Top Processes
          </div>
        </div>
        <div className="space-y-1.5">
          {processes.length === 0 ? (
            <div className="text-xs text-jarvis-text-muted py-1 font-mono">No process data</div>
          ) : (
            processes.slice(0, 5).map((p, i) => {
              const color = getStatusColor(p.cpu_percent)
              return (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="truncate text-jarvis-text-primary max-w-[120px] font-mono">{p.name}</span>
                  <span className="font-mono" style={{ color }}>{p.cpu_percent.toFixed(1)}%</span>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
