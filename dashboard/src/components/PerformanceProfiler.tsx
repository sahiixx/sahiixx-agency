import { useState } from 'react'
import { Skull, Activity } from 'lucide-react'

interface ProfilerProcess {
  pid: number
  name: string
  cpu_percent: number
  memory_mb: number
}

interface PerformanceProfilerProps {
  data: ProfilerProcess[]
  loading?: boolean
  onKill?: (pid: number) => void
}

function getCpuColor(value: number): string {
  if (value >= 70) return '#FF1A1A'
  if (value >= 40) return '#EAB308'
  return '#00FF66'
}

function getCpuGlow(value: number): string {
  if (value >= 70) return 'rgba(255, 26, 26, 0.4)'
  if (value >= 40) return 'rgba(234, 179, 8, 0.4)'
  return 'rgba(0, 255, 102, 0.4)'
}

export function PerformanceProfiler({ data, loading, onKill }: PerformanceProfilerProps) {
  const [sortBy, setSortBy] = useState<'cpu' | 'memory' | 'name'>('cpu')
  const [sortDesc, setSortDesc] = useState(true)
  const [killing, setKilling] = useState<number | null>(null)

  const sorted = [...data].sort((a, b) => {
    const factor = sortDesc ? -1 : 1
    if (sortBy === 'cpu') return (a.cpu_percent - b.cpu_percent) * factor
    if (sortBy === 'memory') return (a.memory_mb - b.memory_mb) * factor
    return a.name.localeCompare(b.name) * factor
  })

  const handleSort = (key: 'cpu' | 'memory' | 'name') => {
    if (sortBy === key) {
      setSortDesc(!sortDesc)
    } else {
      setSortBy(key)
      setSortDesc(true)
    }
  }

  const handleKill = async (pid: number) => {
    if (!onKill) return
    setKilling(pid)
    await onKill(pid)
    setKilling(null)
  }

  if (loading) {
    return (
      <div className="jarvis-card p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-jarvis-cyan animate-pulse" />
          <span className="text-xs font-display uppercase tracking-wider text-jarvis-text-muted">
            Loading processes...
          </span>
        </div>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-10 skeleton-shimmer rounded" />
        ))}
      </div>
    )
  }

  return (
    <div className="jarvis-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-jarvis-cyan" />
          <span className="text-xs font-display uppercase tracking-wider text-jarvis-text-secondary">
            Process Profiler
          </span>
          <div className="live-pulse" style={{ '--pulse-color': '#00F0FF' } as React.CSSProperties} />
        </div>
        <div className="text-[10px] text-jarvis-text-muted font-mono">
          {data.length} processes
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/5">
              <th className="text-left p-3 text-[10px] text-jarvis-text-muted uppercase tracking-wider font-display cursor-pointer hover:text-jarvis-cyan transition-colors"
                onClick={() => handleSort('name')}>
                Process {sortBy === 'name' && (sortDesc ? '↓' : '↑')}
              </th>
              <th className="text-right p-3 text-[10px] text-jarvis-text-muted uppercase tracking-wider font-display cursor-pointer hover:text-jarvis-cyan transition-colors"
                onClick={() => handleSort('cpu')}>
                CPU {sortBy === 'cpu' && (sortDesc ? '↓' : '↑')}
              </th>
              <th className="text-right p-3 text-[10px] text-jarvis-text-muted uppercase tracking-wider font-display cursor-pointer hover:text-jarvis-cyan transition-colors"
                onClick={() => handleSort('memory')}>
                Memory {sortBy === 'memory' && (sortDesc ? '↓' : '↑')}
              </th>
              <th className="text-right p-3 text-[10px] text-jarvis-text-muted uppercase tracking-wider font-display">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((proc) => {
              const color = getCpuColor(proc.cpu_percent)
              const glow = getCpuGlow(proc.cpu_percent)
              return (
                <tr
                  key={proc.pid}
                  className="border-b border-white/[0.03] hover:bg-white/[0.03] transition-colors group"
                >
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <div
                        className="h-2 w-2 rounded-full"
                        style={{ backgroundColor: color, boxShadow: `0 0 6px ${glow}` }}
                      />
                      <span className="text-xs font-mono text-jarvis-text-primary truncate max-w-[150px]">
                        {proc.name}
                      </span>
                      <span className="text-[10px] text-jarvis-text-muted font-mono">#{proc.pid}</span>
                    </div>
                  </td>
                  <td className="p-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 h-1.5 rounded-full bg-white/5 overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${Math.min(proc.cpu_percent, 100)}%`,
                            backgroundColor: color,
                            boxShadow: `0 0 6px ${glow}`,
                          }}
                        />
                      </div>
                      <span className="text-xs font-mono font-bold" style={{ color }}>
                        {proc.cpu_percent.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="p-3 text-right">
                    <span className="text-xs font-mono text-jarvis-text-secondary">
                      {proc.memory_mb.toFixed(0)} MB
                    </span>
                  </td>
                  <td className="p-3 text-right">
                    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => handleKill(proc.pid)}
                        disabled={killing === proc.pid}
                        className="p-1.5 rounded border border-jarvis-red/30 text-jarvis-red hover:bg-jarvis-red/20 transition-colors disabled:opacity-50"
                        title="Kill process"
                      >
                        <Skull className="h-3 w-3" />
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
