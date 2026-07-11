import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MessageSquare,
  CheckSquare,
  Search,
  ShieldCheck,
  Database,
  GitBranch,
  PanelLeftClose,
  PanelLeft,
  Loader2,
  AlertCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ChatThread } from '@/components/chat/ChatThread'
import { ChatInput } from '@/components/chat/ChatInput'
import { TaskStream } from '@/components/tasks/TaskStream'
import { ApprovalQueue } from '@/components/approvals/ApprovalQueue'
import { TrendingPanel } from '@/components/discovery/TrendingPanel'
import { TelegramStatus } from '@/components/telegram/TelegramStatus'

type SidebarItem = 'chat' | 'tasks' | 'discovery' | 'approvals' | 'memory' | 'graph'

interface ChatMessage {
  id: string
  role: 'user' | 'agency'
  content: string
  created_at: string
}

interface Task {
  id: string
  intent: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  module?: string
  module_id?: string
  created_at: string
}

export default function Agency() {
  const [active, setActive] = useState<SidebarItem>('chat')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [threadId, setThreadId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const navigate = useNavigate()

  const navItems: { key: SidebarItem; label: string; icon: React.ReactNode }[] = [
    { key: 'chat', label: 'Chat', icon: <MessageSquare className="h-5 w-5" /> },
    { key: 'tasks', label: 'Tasks', icon: <CheckSquare className="h-5 w-5" /> },
    { key: 'discovery', label: 'Discovery', icon: <Search className="h-5 w-5" /> },
    { key: 'approvals', label: 'Approvals', icon: <ShieldCheck className="h-5 w-5" /> },
    { key: 'memory', label: 'Memory', icon: <Database className="h-5 w-5" /> },
    { key: 'graph', label: 'Graph', icon: <GitBranch className="h-5 w-5" /> },
  ]

  const handleNav = useCallback(
    (key: SidebarItem) => {
      if (key === 'graph') {
        navigate('/graph')
        return
      }
      setActive(key)
      setMobileSidebarOpen(false)
      setSelectedTask(null)
    },
    [navigate]
  )

  const handleSend = useCallback(
    async (text: string) => {
      if (!text.trim()) return
      setChatLoading(true)
      setChatError(null)
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text.trim(), thread_id: threadId }),
        })
        if (!res.ok) throw new Error(`Chat error: ${res.status}`)
        const data = await res.json()
        if (data.thread_id) setThreadId(data.thread_id)
        if (Array.isArray(data.messages)) {
          setMessages(data.messages)
        }
      } catch (err) {
        setChatError(err instanceof Error ? err.message : 'Failed to send')
      } finally {
        setChatLoading(false)
      }
    },
    [threadId]
  )

  useEffect(() => {
    if (!threadId) return
    let cancelled = false
    const poll = async () => {
      try {
        const res = await fetch(`/api/chat/${threadId}`)
        if (!res.ok) return
        const data = await res.json()
        if (cancelled) return
        if (Array.isArray(data.messages)) {
          setMessages(data.messages)
        }
      } catch {
        // ignore polling errors
      }
    }
    poll()
    const interval = setInterval(poll, 3000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [threadId])

  const rightPanelTitle =
    selectedTask
      ? 'Task Details'
      : active === 'tasks'
      ? 'Task Details'
      : active === 'approvals'
      ? 'Approval Queue'
      : active === 'discovery'
      ? 'Trending Repos'
      : active === 'memory'
      ? 'Memory'
      : 'Context'

  return (
    <div className="min-h-[100dvh] flex bg-[var(--bg-base)] text-[var(--text-primary)]">
      {/* Mobile overlay */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed md:sticky top-16 left-0 z-50 h-[calc(100dvh-4rem)] flex-shrink-0 border-r border-white/6 bg-[var(--bg-surface)] transition-all duration-300',
          sidebarOpen ? 'w-60' : 'w-16',
          mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        )}
      >
        <div className="flex h-14 items-center justify-between px-3">
          {sidebarOpen && (
            <span className="font-display text-sm font-semibold text-[var(--text-primary)]">
              Agency
            </span>
          )}
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="hidden md:flex h-8 w-8 items-center justify-center rounded-lg hover:bg-white/5 text-[var(--text-muted)]"
          >
            {sidebarOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeft className="h-4 w-4" />}
          </button>
          <button
            onClick={() => setMobileSidebarOpen(false)}
            className="md:hidden h-8 w-8 items-center justify-center rounded-lg hover:bg-white/5 text-[var(--text-muted)]"
          >
            <PanelLeftClose className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex flex-col gap-1 px-2">
          {navItems.map((item) => (
            <button
              key={item.key}
              onClick={() => handleNav(item.key)}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                active === item.key
                  ? 'bg-accent-cyan/10 text-accent-cyan'
                  : 'text-[var(--text-secondary)] hover:bg-white/5 hover:text-[var(--text-primary)]'
              )}
            >
              {item.icon}
              {sidebarOpen && <span>{item.label}</span>}
            </button>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar for mobile */}
        <div className="md:hidden flex h-14 items-center gap-3 px-4 border-b border-white/6 bg-[var(--bg-surface)]">
          <button
            onClick={() => setMobileSidebarOpen(true)}
            className="h-9 w-9 flex items-center justify-center rounded-lg hover:bg-white/5 text-[var(--text-muted)]"
          >
            <PanelLeft className="h-5 w-5" />
          </button>
          <span className="font-display text-sm font-semibold text-[var(--text-primary)]">
            Agency Command Center
          </span>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Center */}
          <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {active === 'chat' && (
              <>
                <div className="flex-1 overflow-y-auto p-4 md:p-6">
                  {chatError && (
                    <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                      <AlertCircle className="h-4 w-4" />
                      {chatError}
                    </div>
                  )}
                  <ChatThread messages={messages} />
                  {chatLoading && (
                    <div className="flex items-center gap-2 text-sm text-[var(--text-muted)] mt-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Agency is thinking...
                    </div>
                  )}
                </div>
                <div className="border-t border-white/6 p-4 md:p-6">
                  <ChatInput onSend={handleSend} disabled={chatLoading} />
                </div>
              </>
            )}

            {active === 'tasks' && (
              <div className="flex-1 overflow-y-auto p-4 md:p-6">
                <TaskStream onSelectTask={setSelectedTask} />
              </div>
            )}

            {active === 'approvals' && (
              <div className="flex-1 overflow-y-auto p-4 md:p-6">
                <ApprovalQueue />
              </div>
            )}

            {active === 'discovery' && (
              <div className="flex-1 overflow-y-auto p-4 md:p-6">
                <TrendingPanel />
              </div>
            )}

            {active === 'memory' && (
              <div className="flex-1 overflow-y-auto p-4 md:p-6">
                <MemoryPanel />
              </div>
            )}
          </main>

          {/* Right panel */}
          <aside className="hidden lg:flex w-80 flex-col border-l border-white/6 bg-[var(--bg-surface)] overflow-hidden">
            <div className="h-14 flex items-center px-4 border-b border-white/6">
              <h2 className="font-display text-sm font-semibold text-[var(--text-primary)]">
                {rightPanelTitle}
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {selectedTask ? (
                <TaskDetails task={selectedTask} onClose={() => setSelectedTask(null)} />
              ) : active === 'tasks' ? (
                <div className="text-sm text-[var(--text-muted)]">
                  Select a task from the stream to view details.
                </div>
              ) : active === 'approvals' ? (
                <ApprovalQueue compact />
              ) : active === 'discovery' ? (
                <TrendingPanel />
              ) : active === 'memory' ? (
                <MemoryPanel />
              ) : (
                <ContextPanel />
              )}
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}

function ContextPanel() {
  return (
    <div className="space-y-4 text-sm text-[var(--text-secondary)]">
      <div className="rounded-lg border border-white/6 bg-[var(--bg-elevated)] p-4">
        <h3 className="font-medium text-[var(--text-primary)] mb-2">Active Thread</h3>
        <p>No thread selected. Start a conversation in the chat.</p>
      </div>
      <TelegramStatus />
      <div className="rounded-lg border border-white/6 bg-[var(--bg-elevated)] p-4">
        <h3 className="font-medium text-[var(--text-primary)] mb-2">Quick Stats</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md bg-white/5 p-3">
            <div className="text-xs text-[var(--text-muted)]">Modules</div>
            <div className="text-lg font-semibold text-[var(--text-primary)]">—</div>
          </div>
          <div className="rounded-md bg-white/5 p-3">
            <div className="text-xs text-[var(--text-muted)]">Tasks Today</div>
            <div className="text-lg font-semibold text-[var(--text-primary)]">—</div>
          </div>
        </div>
      </div>
    </div>
  )
}

function MemoryPanel() {
  const [entries, setEntries] = useState<{ key: string; value: string; updated_at: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    fetch('/api/memory')
      .then((r) => {
        if (!r.ok) throw new Error(`Memory fetch failed: ${r.status}`)
        return r.json()
      })
      .then((data) => {
        if (cancelled) return
        setEntries(Array.isArray(data) ? data : [])
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Error')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) return <div className="text-sm text-[var(--text-muted)]">Loading memory...</div>
  if (error) return <div className="text-sm text-red-400">{error}</div>
  if (entries.length === 0)
    return <div className="text-sm text-[var(--text-muted)]">No memory entries yet.</div>

  return (
    <div className="space-y-3">
      {entries.map((entry) => (
        <div
          key={entry.key}
          className="rounded-lg border border-white/6 bg-[var(--bg-elevated)] p-3"
        >
          <div className="text-xs font-mono text-[var(--text-muted)] mb-1">{entry.key}</div>
          <div className="text-sm text-[var(--text-secondary)] line-clamp-3">{entry.value}</div>
        </div>
      ))}
    </div>
  )
}

function TaskDetails({ task, onClose }: { task: Task; onClose: () => void }) {
  const [details, setDetails] = useState<Task | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    // Initialize loading state via microtask to avoid cascading render
    Promise.resolve().then(() => {
      if (!cancelled) setLoading(true)
    })
    fetch(`/api/tasks/${task.id}`)
      .then((r) => {
        if (!r.ok) throw new Error(`Task fetch failed: ${r.status}`)
        return r.json()
      })
      .then((data) => {
        if (!cancelled) setDetails(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Error')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [task.id])

  const statusColor =
    details?.status === 'completed'
      ? 'text-accent-green'
      : details?.status === 'failed' || details?.status === 'cancelled'
      ? 'text-accent-red'
      : details?.status === 'running'
      ? 'text-accent-cyan'
      : 'text-accent-amber'

  return (
    <div className="space-y-4">
      <button
        onClick={onClose}
        className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)]"
      >
        ← Back
      </button>
      {loading && <div className="text-sm text-[var(--text-muted)]">Loading...</div>}
      {error && <div className="text-sm text-red-400">{error}</div>}
      {details && (
        <div className="rounded-lg border border-white/6 bg-[var(--bg-elevated)] p-4 space-y-3">
          <div>
            <div className="text-xs text-[var(--text-muted)] mb-1">Intent</div>
            <div className="text-sm text-[var(--text-primary)]">{details.intent}</div>
          </div>
          <div>
            <div className="text-xs text-[var(--text-muted)] mb-1">Status</div>
            <div className={cn('text-sm font-medium uppercase', statusColor)}>
              {details.status}
            </div>
          </div>
          {(details.module || details.module_id) && (
            <div>
              <div className="text-xs text-[var(--text-muted)] mb-1">Module</div>
              <div className="text-sm text-[var(--text-primary)]">{details.module || details.module_id}</div>
            </div>
          )}
          <div>
            <div className="text-xs text-[var(--text-muted)] mb-1">Created</div>
            <div className="text-sm text-[var(--text-primary)]">
              {new Date(details.created_at).toLocaleString()}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
