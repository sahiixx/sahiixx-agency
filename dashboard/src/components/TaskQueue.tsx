import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { ListTodo, Loader2, AlertCircle, Clock } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface AgencyTask {
  id: string
  intent: string
  status: 'pending' | 'routing' | 'running' | 'completed' | 'failed' | 'cancelled'
  created_at: string
  module_id?: string | null
  category?: string | null
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080'
const POLL_INTERVAL_MS = 3000

const STATUS_STYLES: Record<
  AgencyTask['status'],
  { dot: string; label: string }
> = {
  pending: { dot: 'bg-amber-400', label: 'text-amber-400' },
  routing: { dot: 'bg-blue-400', label: 'text-blue-400' },
  running: { dot: 'bg-cyan-400 animate-pulse', label: 'text-cyan-400' },
  completed: { dot: 'bg-green-500', label: 'text-green-500' },
  failed: { dot: 'bg-destructive', label: 'text-destructive' },
  cancelled: { dot: 'bg-neutral-400', label: 'text-neutral-400' },
}

function formatTime(iso: string): string {
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleTimeString()
}

export default function TaskQueue() {
  const [tasks, setTasks] = useState<AgencyTask[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTasks = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/tasks?limit=20`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = (await res.json()) as AgencyTask[] | { tasks?: AgencyTask[] }
      const list = Array.isArray(data) ? data : data.tasks ?? []
      setTasks(list)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTasks()
    const intervalId = setInterval(fetchTasks, POLL_INTERVAL_MS)
    return () => clearInterval(intervalId)
  }, [fetchTasks])

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="fixed bottom-4 right-4 z-30 w-full max-w-md"
      >
        <div className="glass-panel rounded-[14px] p-4">
          <div className="flex items-center gap-3 text-text-muted">
            <Loader2 className="w-5 h-5 animate-spin text-primary" />
            <span className="font-mono text-[13px]">Loading task queue...</span>
          </div>
        </div>
      </motion.div>
    )
  }

  if (error && tasks.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="fixed bottom-4 right-4 z-30 w-full max-w-md"
      >
        <div className="glass-panel rounded-[14px] p-4 border border-destructive/30">
          <div className="flex items-center gap-3 text-destructive">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <div>
              <p className="font-medium text-sm">Failed to load task queue</p>
              <p className="font-mono text-[12px] text-text-muted mt-1">{error}</p>
            </div>
          </div>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.8 }}
      className="fixed bottom-4 right-4 z-30 w-full max-w-md"
    >
      <div className="glass-panel rounded-[14px] p-4">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <ListTodo className="w-4 h-4 text-primary" />
            <h3 className="font-display text-h3 text-text-primary">Task Queue</h3>
          </div>
          <div className="flex items-center gap-2">
            {loading && (
              <Loader2 className="w-4 h-4 animate-spin text-text-muted" />
            )}
            {error && (
              <span className="text-[11px] text-destructive font-mono">{error}</span>
            )}
          </div>
        </div>

        <div className="max-h-[280px] overflow-auto">
          {tasks.length === 0 ? (
            <div className="text-text-muted font-mono text-[12px] py-4 text-center">
              No tasks yet
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-text-muted font-mono text-[11px]">
                    Status
                  </TableHead>
                  <TableHead className="text-text-muted font-mono text-[11px]">
                    Intent
                  </TableHead>
                  <TableHead className="text-text-muted font-mono text-[11px]">
                    Created
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasks.map((task) => {
                  const styles = STATUS_STYLES[task.status] ?? {
                    dot: 'bg-text-muted',
                    label: 'text-text-muted',
                  }
                  return (
                    <TableRow key={task.id}>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`w-2 h-2 rounded-full ${styles.dot}`}
                            aria-hidden="true"
                          />
                          <span
                            className={`text-[11px] font-medium uppercase ${styles.label}`}
                          >
                            {task.status}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell
                        className="text-text-primary text-[12px] max-w-[120px] truncate"
                        title={task.intent}
                      >
                        {task.intent}
                      </TableCell>
                      <TableCell className="text-text-muted font-mono text-[11px]">
                        <Clock className="w-3 h-3 inline mr-1" />
                        {formatTime(task.created_at)}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </motion.div>
  )
}
