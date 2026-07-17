import { useState, useEffect, useCallback, useRef } from 'react'
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
  Radio,
  CheckCircle2,
  XCircle,
  Activity,
  Volume2,
  VolumeX,
  Command,
  Monitor,
  Bot,
  Bell,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ChatThread } from '@/components/chat/ChatThread'
import { ChatInput } from '@/components/chat/ChatInput'
import { TypingIndicator } from '@/components/chat/TypingIndicator'
import { TaskStream } from '@/components/tasks/TaskStream'
import { ApprovalQueue } from '@/components/approvals/ApprovalQueue'
import { TrendingPanel } from '@/components/discovery/TrendingPanel'
import { CommandPalette } from '@/components/CommandPalette'
import { DeviceControlPanel } from '@/components/DeviceControlPanel'
import { DeviceSidebarCompact } from '@/components/DeviceSidebarCompact'
import { TaskTimeline } from '@/components/TaskTimeline'
import { LiveMetricsHUD } from '@/components/LiveMetricsHUD'
import { useTaskStream } from '@/hooks/useTaskStream'
import { useVoiceSynthesis } from '@/hooks/useVoiceSynthesis'

type SidebarItem = 'chat' | 'tasks' | 'discovery' | 'approvals' | 'memory' | 'device' | 'graph' | 'notifications'

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

interface NotificationItem {
  id: string
  channel: string
  title: string
  body: string
  status: string
  created_at: string
  sent_at?: string
  error?: string
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
  const [liveTaskId, setLiveTaskId] = useState<string | null>(null)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [ttsEnabled, setTtsEnabled] = useState(true)
  const [agentMode, setAgentMode] = useState(true)
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const navigate = useNavigate()

  const { task: liveTask, connected: liveConnected, finished } = useTaskStream(liveTaskId)
  const { speaking, speak, stop } = useVoiceSynthesis()
  const liveCardRef = useRef<HTMLDivElement>(null)
  const prevMessagesLen = useRef(0)

  // Auto-scroll live task card into view when it appears/updates
  useEffect(() => {
    if (liveTask && liveCardRef.current) {
      liveCardRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [liveTask])

  // TTS: speak the latest agency message when messages update
  useEffect(() => {
    if (!ttsEnabled) return
    if (messages.length > prevMessagesLen.current) {
      const lastMsg = messages[messages.length - 1]
      if (lastMsg.role === 'agency' && lastMsg.content) {
        speak(lastMsg.content)
      }
    }
    prevMessagesLen.current = messages.length
  }, [messages, ttsEnabled, speak])

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

  // Keyboard shortcuts
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      // Cmd/Ctrl+K or / to open palette
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setPaletteOpen((o) => !o)
        return
      }
      if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) {
        e.preventDefault()
        setPaletteOpen(true)
        return
      }
      // Esc to close sidebar on mobile
      if (e.key === 'Escape' && mobileSidebarOpen) {
        setMobileSidebarOpen(false)
        return
      }
      // 1-8 for sidebar navigation
      if (e.key >= '1' && e.key <= '8' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const idx = parseInt(e.key) - 1
        const keys: SidebarItem[] = ['chat', 'tasks', 'discovery', 'approvals', 'memory', 'notifications', 'device', 'graph']
        if (keys[idx]) {
          e.preventDefault()
          handleNav(keys[idx])
        }
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [mobileSidebarOpen, handleNav])

  const navItems: { key: SidebarItem; label: string; icon: React.ReactNode }[] = [
    { key: 'chat', label: 'Chat', icon: <MessageSquare className="h-5 w-5" /> },
    { key: 'tasks', label: 'Tasks', icon: <CheckSquare className="h-5 w-5" /> },
    { key: 'discovery', label: 'Discovery', icon: <Search className="h-5 w-5" /> },
    { key: 'approvals', label: 'Approvals', icon: <ShieldCheck className="h-5 w-5" /> },
    { key: 'memory', label: 'Memory', icon: <Database className="h-5 w-5" /> },
    { key: 'notifications', label: 'Notifications', icon: <Bell className="h-5 w-5" /> },
    { key: 'device', label: 'Device', icon: <Monitor className="h-5 w-5" /> },
    { key: 'graph', label: 'Graph', icon: <GitBranch className="h-5 w-5" /> },
  ]

  const handleSend = useCallback(
    async (text: string) => {
      if (!text.trim()) return
      setChatLoading(true)
      setChatError(null)
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text.trim(), thread_id: threadId, agent: agentMode }),
        })
        if (!res.ok) throw new Error(`Chat error: ${res.status}`)
        const data = await res.json()
        if (data.thread_id) setThreadId(data.thread_id)
        if (Array.isArray(data.messages)) {
          setMessages(data.messages)
        }
        if (data.task_id) {
          setLiveTaskId(data.task_id)
        }
      } catch (err) {
        setChatError(err instanceof Error ? err.message : 'Failed to send')
      } finally {
        setChatLoading(false)
      }
    },
    [threadId, agentMode]
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

  useEffect(() => {
    if (active !== 'notifications') return
    let cancelled = false
    const fetchNotifications = async () => {
      try {
        const res = await fetch('/api/notifications?limit=50')
        if (!res.ok) return
        const data = await res.json()
        if (cancelled) return
        setNotifications(data)
      } catch {
        // ignore
      }
    }
    fetchNotifications()
    const interval = setInterval(fetchNotifications, 5000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [active])

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
      : active === 'notifications'
      ? 'Notifications'
      : active === 'device'
      ? 'Device Control'
      : 'Context'

  const statusIcon = (status?: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-accent-green" />
      case 'failed':
      case 'cancelled':
        return <XCircle className="h-4 w-4 text-accent-red" />
      case 'running':
        return <Activity className="h-4 w-4 text-accent-cyan animate-pulse" />
      default:
        return <Loader2 className="h-4 w-4 text-accent-amber animate-spin" />
    }
  }

  const paletteItems = [
    { id: 'chat', label: 'Go to Chat', shortcut: '1', action: () => handleNav('chat') },
    { id: 'tasks', label: 'Go to Tasks', shortcut: '2', action: () => handleNav('tasks') },
    { id: 'discovery', label: 'Go to Discovery', shortcut: '3', action: () => handleNav('discovery') },
    { id: 'approvals', label: 'Go to Approvals', shortcut: '4', action: () => handleNav('approvals') },
    { id: 'memory', label: 'Go to Memory', shortcut: '5', action: () => handleNav('memory') },
    { id: 'notifications', label: 'Go to Notifications', shortcut: '6', action: () => handleNav('notifications') },
    { id: 'device', label: 'Go to Device', shortcut: '7', action: () => handleNav('device') },
    { id: 'graph', label: 'Go to Graph', shortcut: '8', action: () => handleNav('graph') },
    { id: 'toggle-tts', label: ttsEnabled ? 'Disable Voice (TTS)' : 'Enable Voice (TTS)', shortcut: 'T', action: () => setTtsEnabled((v) => !v) },
    { id: 'stop-speech', label: 'Stop Speaking', shortcut: 'S', action: () => stop() },
    { id: 'clear-chat', label: 'Clear Chat', shortcut: 'C', action: () => { setMessages([]); setThreadId(null); setLiveTaskId(null); } },
  ]

  return (
    <>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} items={paletteItems} />
      <div className="min-h-[100dvh] flex bg-[var(--bg-base)] text-[var(--text-primary)]">
        {/* CRT Overlay — only visible in device mode */}
        {active === 'device' && <div className="crt-overlay" />}
        {active === 'device' && <div className="ambient-grid" />}

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
            {navItems.map((item, idx) => (
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
                {sidebarOpen && (
                  <div className="flex items-center justify-between flex-1">
                    <span>{item.label}</span>
                    <kbd className="hidden lg:inline-flex rounded bg-white/5 px-1 text-[10px] font-mono text-[var(--text-muted)]">
                      {idx + 1}
                    </kbd>
                  </div>
                )}
              </button>
            ))}
          </nav>

          {/* Bottom sidebar controls */}
          <div className="mt-auto px-2 pb-4">
            <button
              onClick={() => setTtsEnabled((v) => !v)}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors w-full',
                ttsEnabled
                  ? 'text-accent-cyan hover:bg-accent-cyan/10'
                  : 'text-[var(--text-muted)] hover:bg-white/5'
              )}
              title={ttsEnabled ? 'Voice output on' : 'Voice output off'}
            >
              {ttsEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
              {sidebarOpen && <span>{ttsEnabled ? 'Voice On' : 'Voice Off'}</span>}
            </button>
            <button
              onClick={() => setPaletteOpen(true)}
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[var(--text-muted)] hover:bg-white/5 hover:text-[var(--text-primary)] transition-colors w-full mt-1"
            >
              <Command className="h-4 w-4" />
              {sidebarOpen && (
                <div className="flex items-center justify-between flex-1">
                  <span>Command</span>
                  <kbd className="hidden lg:inline-flex rounded bg-white/5 px-1 text-[10px] font-mono text-[var(--text-muted)]">
                    /
                  </kbd>
                </div>
              )}
            </button>
          </div>
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
                    {chatLoading && <TypingIndicator />}
                    {speaking && (
                      <div className="flex items-center gap-2 text-xs text-accent-cyan mt-2 animate-pulse">
                        <Volume2 className="h-3 w-3" />
                        <span>Speaking...</span>
                      </div>
                    )}
                    {liveTask && (
                      <div ref={liveCardRef} className="mt-4 rounded-lg border border-white/6 bg-[var(--bg-elevated)] p-4 space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <div className="flex items-center gap-2 text-sm font-medium text-[var(--text-primary)]">
                          {statusIcon(liveTask.status)}
                          <span>{liveTask.intent}</span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                          {liveConnected && !finished && (
                            <>
                              <Radio className="h-3 w-3 text-accent-cyan animate-pulse" />
                              <span className="text-accent-cyan font-medium">Live</span>
                            </>
                          )}
                          {finished && liveTask.status === 'completed' && (
                            <span className="inline-flex items-center rounded-full bg-accent-green/10 px-2 py-0.5 text-accent-green text-[10px] font-semibold uppercase tracking-wider">Done</span>
                          )}
                          {finished && (liveTask.status === 'failed' || liveTask.status === 'cancelled') && (
                            <span className="inline-flex items-center rounded-full bg-accent-red/10 px-2 py-0.5 text-accent-red text-[10px] font-semibold uppercase tracking-wider">{liveTask.status}</span>
                          )}
                          <span className={`uppercase font-mono text-[10px] font-semibold tracking-wider rounded-full px-2 py-0.5 ${
                            liveTask.status === 'completed' ? 'bg-accent-green/10 text-accent-green' :
                            liveTask.status === 'failed' || liveTask.status === 'cancelled' ? 'bg-accent-red/10 text-accent-red' :
                            liveTask.status === 'running' ? 'bg-accent-cyan/10 text-accent-cyan' :
                            'bg-accent-amber/10 text-accent-amber'
                          }`}>
                            {liveTask.status}
                          </span>
                          {liveTask.module && <span>· {liveTask.module}</span>}
                        </div>
                        {liveTask.result && (
                          <div className="text-xs text-[var(--text-secondary)] bg-white/5 rounded-md p-2 max-h-32 overflow-y-auto">
                            {liveTask.result}
                          </div>
                        )}
                        {liveTask.error && (
                          <div className="text-xs text-red-400 bg-red-500/10 rounded-md p-2">
                            {liveTask.error}
                          </div>
                        )}
                        <TaskTimeline status={liveTask.status} module={liveTask.module || liveTask.module_id} />
                      </div>
                    )}
                  </div>
                  <div className="border-t border-white/6 p-4 md:p-6 space-y-3">
                    <div className="flex items-center justify-between">
                      <button
                        onClick={() => setAgentMode((v) => !v)}
                        className={cn(
                          'inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
                          agentMode
                            ? 'bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/30'
                            : 'bg-white/5 text-[var(--text-muted)] border border-white/6 hover:bg-white/10'
                        )}
                        title={agentMode ? 'Agent planning enabled' : 'Agent planning disabled'}
                      >
                        <Bot className="h-3.5 w-3.5" />
                        {agentMode ? 'Agent mode on' : 'Agent mode off'}
                      </button>
                      <span className="text-[10px] text-[var(--text-muted)]">
                        {agentMode ? 'LLM plans the intent before dispatch' : 'Dispatch intent directly'}
                      </span>
                    </div>
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

              {active === 'notifications' && (
                <div className="flex-1 overflow-y-auto p-4 md:p-6">
                  <div className="space-y-3">
                    {notifications.length === 0 && (
                      <p className="text-sm text-[var(--text-muted)]">No notifications yet.</p>
                    )}
                    {notifications.map((n) => (
                      <div
                        key={n.id}
                        className="rounded-lg border border-white/6 bg-[var(--bg-elevated)] p-3 space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-[var(--text-primary)]">{n.title}</span>
                          <span className="text-[10px] uppercase font-mono text-[var(--text-muted)]">{n.channel}</span>
                        </div>
                        <p className="text-xs text-[var(--text-secondary)]">{n.body}</p>
                        <div className="flex items-center gap-2 text-[10px] text-[var(--text-muted)]">
                          <span className={`px-1.5 py-0.5 rounded ${n.status === 'sent' ? 'bg-accent-green/10 text-accent-green' : 'bg-accent-amber/10 text-accent-amber'}`}>
                            {n.status}
                          </span>
                          <span>{new Date(n.created_at).toLocaleString()}</span>
                        </div>
                        {n.error && <div className="text-[10px] text-red-400">{n.error}</div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {active === 'device' && (
                <div className="flex-1 overflow-y-auto p-4 md:p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="live-pulse" style={{ '--pulse-color': '#FF1A1A' } as React.CSSProperties} />
                    <h2 className="text-lg font-display font-bold uppercase tracking-wider text-jarvis-cyan text-glow"
                      style={{ '--glow-color': 'rgba(0,240,255,0.3)' } as React.CSSProperties}>
                      Device Control
                    </h2>
                  </div>
                  <DeviceControlPanel />
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
                ) : active === 'notifications' ? (
                  <div className="text-sm text-[var(--text-muted)]">
                    Real-time notifications also appear as toast alerts.
                  </div>
                ) : active === 'device' ? (
                  <DeviceSidebarCompact
                    cpu={null}
                    memory={null}
                    disk={null}
                    uptime={0}
                    processes={[]}
                  />
                ) : (
                  <LiveMetricsHUD />
                )}
              </div>
            </aside>
          </div>
        </div>
      </div>
    </>
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
