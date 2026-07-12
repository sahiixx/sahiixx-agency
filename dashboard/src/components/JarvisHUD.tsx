import { Cpu, HardDrive, MemoryStick, Network, X, Activity } from 'lucide-react'

interface JarvisHUDProps {
  cpu: number | null
  memory: number | null
  disk: number | null
  network: { bytes_sent: number; bytes_recv: number } | null
  uptime: number
  processes: Array<{ name: string; cpu_percent: number; memory_mb: number }>
  onClose: () => void
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / k ** i).toFixed(1))} ${sizes[i]}`
}

function getStatusColor(value: number): string {
  if (value >= 80) return '#FF1A1A'
  if (value >= 50) return '#EAB308'
  return '#00F0FF'
}

function getStatusGlow(value: number): string {
  if (value >= 80) return 'rgba(255, 26, 26, 0.4)'
  if (value >= 50) return 'rgba(234, 179, 8, 0.4)'
  return 'rgba(0, 240, 255, 0.4)'
}

export function JarvisHUD({
  cpu,
  memory,
  disk,
  network,
  uptime,
  processes,
  onClose,
}: JarvisHUDProps) {
  const topProcesses = processes
    .slice()
    .sort((a, b) => b.cpu_percent - a.cpu_percent)
    .slice(0, 5)

  const metrics = [
    {
      label: 'CPU',
      value: cpu !== null ? `${cpu.toFixed(1)}%` : '—',
      raw: cpu ?? 0,
      icon: <Cpu className="w-6 h-6" />,
      color: getStatusColor(cpu ?? 0),
      glow: getStatusGlow(cpu ?? 0),
    },
    {
      label: 'RAM',
      value: memory !== null ? `${memory.toFixed(1)}%` : '—',
      raw: memory ?? 0,
      icon: <MemoryStick className="w-6 h-6" />,
      color: getStatusColor(memory ?? 0),
      glow: getStatusGlow(memory ?? 0),
    },
    {
      label: 'DISK',
      value: disk !== null ? `${disk.toFixed(1)}%` : '—',
      raw: disk ?? 0,
      icon: <HardDrive className="w-6 h-6" />,
      color: getStatusColor(disk ?? 0),
      glow: getStatusGlow(disk ?? 0),
    },
    {
      label: 'NETWORK',
      value: network !== null
        ? `↑${formatBytes(network.bytes_sent)} ↓${formatBytes(network.bytes_recv)}`
        : '—',
      raw: 0,
      icon: <Network className="w-6 h-6" />,
      color: '#00FF66',
      glow: 'rgba(0, 255, 102, 0.4)',
    },
  ]

  return (
    <div className="fixed inset-0 z-50 bg-jarvis-void/95 flex flex-col font-mono text-white">
      {/* CRT Scanline overlay */}
      <div className="crt-overlay" />

      {/* Animated grid background */}
      <div className="ambient-grid" />

      {/* Top bar */}
      <div className="relative z-10 flex items-center justify-between border-b border-jarvis-cyan/20 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="live-pulse" style={{ '--pulse-color': '#00FF66' } as React.CSSProperties} />
          <h1 className="text-sm font-display font-bold uppercase tracking-[0.2em] text-jarvis-cyan text-glow"
            style={{ '--glow-color': 'rgba(0,240,255,0.4)' } as React.CSSProperties}>
            JARVIS System Monitor
          </h1>
        </div>
        <div className="flex items-center gap-6">
          <div className="text-xs text-jarvis-text-secondary font-mono">
            UPTIME: <span className="font-bold text-jarvis-cyan">{formatUptime(uptime)}</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded border border-jarvis-cyan/30 text-jarvis-cyan transition-colors hover:bg-jarvis-cyan/20 hover:text-white"
            aria-label="Close HUD"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main 2x2 metric grid */}
      <div className="relative z-10 flex-1 p-6">
        <div className="grid h-full grid-cols-2 grid-rows-2 gap-4">
          {metrics.map((m) => (
            <div
              key={m.label}
              className="jarvis-card corner-brackets relative flex flex-col justify-between overflow-hidden p-6"
              style={{ '--accent-color': m.color } as React.CSSProperties}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-display font-bold uppercase tracking-widest text-jarvis-text-muted">
                  {m.label}
                </span>
                <span style={{ color: m.color }}>{m.icon}</span>
              </div>

              <div
                className="text-5xl font-mono font-bold leading-none tracking-tight text-glow"
                style={{ color: m.color, '--glow-color': m.glow } as React.CSSProperties}
              >
                {m.value}
              </div>

              {/* Progress bar */}
              <div className="mt-4">
                <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
                  <div
                    className="h-full rounded-full transition-all duration-700 ease-out progress-glow"
                    style={{
                      width: `${Math.min(m.raw, 100)}%`,
                      backgroundColor: m.color,
                      '--bar-color': m.glow,
                    } as React.CSSProperties}
                  />
                </div>
              </div>

              {/* Accent bar at bottom */}
              <div className="absolute bottom-0 left-0 h-1 w-full" style={{ backgroundColor: m.color, opacity: 0.6 }} />
            </div>
          ))}
        </div>
      </div>

      {/* Bottom process bar chart */}
      <div className="relative z-10 border-t border-jarvis-cyan/20 px-6 py-5">
        <div className="mb-3 flex items-center gap-2">
          <Activity className="h-3 w-3 text-jarvis-cyan" />
          <div className="text-xs font-display font-bold uppercase tracking-widest text-jarvis-cyan">
            Top Processes
          </div>
        </div>
        <div className="space-y-2">
          {topProcesses.length === 0 && (
            <div className="text-sm text-jarvis-text-muted font-mono">No process data available</div>
          )}
          {topProcesses.map((proc) => {
            const barColor = getStatusColor(proc.cpu_percent)
            const barGlow = getStatusGlow(proc.cpu_percent)
            return (
              <div key={proc.name} className="flex items-center gap-4">
                <div className="w-32 shrink-0 truncate text-xs text-jarvis-text-secondary font-mono" title={proc.name}>
                  {proc.name}
                </div>
                <div className="flex-1">
                  <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/5">
                    <div
                      className="h-full rounded-full transition-all duration-500 ease-out progress-glow"
                      style={{
                        width: `${Math.min(proc.cpu_percent, 100)}%`,
                        backgroundColor: barColor,
                        '--bar-color': barGlow,
                      } as React.CSSProperties}
                    />
                  </div>
                </div>
                <div className="w-16 shrink-0 text-right text-xs font-bold font-mono" style={{ color: barColor }}>
                  {proc.cpu_percent.toFixed(1)}%
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
