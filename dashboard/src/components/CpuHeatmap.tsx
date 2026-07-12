import { Cpu } from 'lucide-react'

interface CpuHeatmapProps {
  cores: number[]
}

function getHeatColor(value: number): string {
  if (value >= 80) return '#FF1A1A'
  if (value >= 60) return '#EAB308'
  if (value >= 40) return '#00F0FF'
  return '#00FF66'
}

function getHeatGlow(value: number): string {
  if (value >= 80) return 'rgba(255, 26, 26, 0.5)'
  if (value >= 60) return 'rgba(234, 179, 8, 0.5)'
  if (value >= 40) return 'rgba(0, 240, 255, 0.5)'
  return 'rgba(0, 255, 102, 0.5)'
}

export function CpuHeatmap({ cores }: CpuHeatmapProps) {
  if (!cores || cores.length === 0) {
    return (
      <div className="jarvis-card p-6 flex items-center justify-center">
        <div className="flex items-center gap-2 text-jarvis-text-muted">
          <div className="h-2 w-2 rounded-full bg-current animate-live-pulse" />
          <span className="text-xs font-mono">No core data available</span>
        </div>
      </div>
    )
  }

  return (
    <div className="jarvis-card corner-brackets p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Cpu className="h-4 w-4 text-jarvis-cyan" />
        <span className="text-xs font-display uppercase tracking-wider text-jarvis-text-secondary">
          CPU Core Heatmap
        </span>
        <div className="live-pulse" style={{ '--pulse-color': '#00F0FF' } as React.CSSProperties} />
      </div>

      <div className="grid grid-cols-4 gap-2">
        {cores.map((load, i) => {
          const color = getHeatColor(load)
          const glow = getHeatGlow(load)
          return (
            <div
              key={i}
              className="relative rounded overflow-hidden bg-white/5 p-2"
            >
              <div className="text-[10px] text-jarvis-text-muted font-mono mb-1">Core {i + 1}</div>
              <div className="text-lg font-mono font-bold" style={{ color }}>
                {load.toFixed(1)}%
              </div>
              <div className="absolute bottom-0 left-0 h-1 w-full bg-white/5">
                <div
                  className="h-full transition-all duration-500 progress-glow"
                  style={{
                    width: `${Math.min(load, 100)}%`,
                    backgroundColor: color,
                    '--bar-color': glow,
                  } as React.CSSProperties}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
