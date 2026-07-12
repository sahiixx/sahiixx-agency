import { useState } from 'react'
import { ChevronRight, ChevronDown, Circle } from 'lucide-react'

interface ProcessNode {
  pid: number
  name: string
  cpu_percent: number
  memory_mb: number
  status: string
  children?: ProcessNode[]
}

interface ProcessTreeProps {
  processes: ProcessNode[]
}

function getStatusColor(value: number): string {
  if (value >= 70) return '#FF1A1A'
  if (value >= 40) return '#EAB308'
  return '#00FF66'
}

function getStatusDot(status: string): string {
  switch (status.toLowerCase()) {
    case 'running': return '#00FF66'
    case 'sleeping': return '#00F0FF'
    case 'stopped': return '#EAB308'
    case 'zombie': return '#FF1A1A'
    default: return '#525252'
  }
}

function TreeNode({ node, depth = 0 }: { node: ProcessNode; depth?: number }) {
  const [expanded, setExpanded] = useState(depth < 1)
  const hasChildren = node.children && node.children.length > 0
  const cpuColor = getStatusColor(node.cpu_percent)
  const statusColor = getStatusDot(node.status)

  return (
    <div>
      <div
        className="flex items-center gap-2 py-1.5 px-2 hover:bg-white/[0.03] rounded transition-colors cursor-pointer"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {hasChildren ? (
          expanded ? <ChevronDown className="h-3 w-3 text-jarvis-text-muted" /> : <ChevronRight className="h-3 w-3 text-jarvis-text-muted" />
        ) : (
          <div className="w-3" />
        )}
        <Circle className="h-2 w-2" style={{ color: statusColor, fill: statusColor }} />
        <span className="text-xs font-mono text-jarvis-text-primary truncate flex-1">{node.name}</span>
        <span className="text-[10px] text-jarvis-text-muted font-mono">#{node.pid}</span>
        <span className="text-xs font-mono font-bold w-12 text-right" style={{ color: cpuColor }}>
          {node.cpu_percent.toFixed(1)}%
        </span>
      </div>
      {hasChildren && expanded && (
        <div>
          {node.children!.map((child) => (
            <TreeNode key={child.pid} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export function ProcessTree({ processes }: ProcessTreeProps) {
  if (!processes || processes.length === 0) {
    return (
      <div className="jarvis-card p-6 flex items-center justify-center">
        <div className="flex items-center gap-2 text-jarvis-text-muted">
          <div className="h-2 w-2 rounded-full bg-current animate-live-pulse" />
          <span className="text-xs font-mono">No process tree data</span>
        </div>
      </div>
    )
  }

  return (
    <div className="jarvis-card corner-brackets p-4 space-y-2">
      <div className="flex items-center gap-2 mb-2">
        <div className="live-pulse" style={{ '--pulse-color': '#00FF66' } as React.CSSProperties} />
        <span className="text-xs font-display uppercase tracking-wider text-jarvis-text-secondary">
          Process Tree
        </span>
      </div>
      <div className="space-y-0.5">
        {processes.map((proc) => (
          <TreeNode key={proc.pid} node={proc} />
        ))}
      </div>
    </div>
  )
}
