import { useState, useEffect, useCallback } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Task {
  id: string
  intent: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  module?: string
  module_id?: string
  created_at: string
}

interface TaskStreamProps {
  onSelectTask?: (task: Task) => void
}

export function TaskStream({ onSelectTask }: TaskStreamProps) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTasks = useCallback(async () => {
    try {
      const res = await fetch('/api/tasks')
      if (!res.ok) throw new Error(`Tasks fetch failed: ${res.status}`)
      const data = await res.json()
      setTasks(
        (Array.isArray(data) ? data : []).map((t: Task) => ({
          ...t,
          module: t.module || t.module_id,
        }))
      )
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tasks')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTasks()
    const interval = setInterval(fetchTasks, 3000)
    return () => clearInterval(interval)
  }, [fetchTasks])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading tasks...
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-sm text-red-400">
        <AlertCircle className="h-4 w-4" />
        {error}
      </div>
    )
  }

  if (tasks.length === 0) {
    return <div className="text-sm text-[var(--text-muted)]">No tasks yet.</div>
  }

  return (
    <div className="space-y-3">
      {tasks.map((task) => (
        <TaskCard key={task.id} task={task} onClick={() => onSelectTask?.(task)} />
      ))}
    </div>
  )
}

function TaskCard({ task, onClick }: { task: Task; onClick?: () => void }) {
  const statusColor =
    task.status === 'completed'
      ? 'bg-accent-green/10 text-accent-green border-accent-green/20'
      : task.status === 'failed' || task.status === 'cancelled'
      ? 'bg-accent-red/10 text-accent-red border-accent-red/20'
      : task.status === 'running'
      ? 'bg-accent-cyan/10 text-accent-cyan border-accent-cyan/20'
      : 'bg-accent-amber/10 text-accent-amber border-accent-amber/20'

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left rounded-lg border border-white/6 bg-[var(--bg-elevated)] p-4 hover:border-white/10 transition-colors',
        onClick && 'cursor-pointer'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-[var(--text-primary)] truncate">
            {task.intent}
          </div>
          {task.module && (
            <div className="text-xs text-[var(--text-muted)] mt-1">{task.module}</div>
          )}
        </div>
        <span
          className={cn(
            'shrink-0 inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide',
            statusColor
          )}
        >
          {task.status}
        </span>
      </div>
      <div className="mt-2 text-[11px] text-[var(--text-muted)]">
        {new Date(task.created_at).toLocaleString()}
      </div>
    </button>
  )
}
