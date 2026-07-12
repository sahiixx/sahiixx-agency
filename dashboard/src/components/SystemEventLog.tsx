import { RefreshCw, AlertCircle, Loader2 } from 'lucide-react'

interface EventItem {
  TimeCreated: string
  LevelDisplayName: string
  Message: string
}

interface SystemEventLogProps {
  events: EventItem[]
  loading: boolean
  onRefresh: () => void
}

function LevelBadge({ level }: { level: string }) {
  const normalized = level.trim().toLowerCase()
  let className = 'inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium uppercase'

  if (normalized === 'error') {
    className += ' bg-accent-red/10 text-accent-red'
  } else if (normalized === 'warning') {
    className += ' bg-accent-amber/10 text-accent-amber'
  } else if (normalized === 'information') {
    className += ' bg-accent-cyan/10 text-accent-cyan'
  } else {
    className += ' bg-white/5 text-[var(--text-muted)]'
  }

  return <span className={className}>{level}</span>
}

export function SystemEventLog({ events, loading, onRefresh }: SystemEventLogProps) {
  return (
    <div className="rounded-md border border-white/6 overflow-hidden bg-[var(--bg-elevated)]">
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/6 bg-white/5">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">Event Log</h3>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-1 rounded px-2 py-1 text-[10px] font-medium text-[var(--text-secondary)] hover:bg-white/5 hover:text-[var(--text-primary)] transition-colors disabled:opacity-50"
          title="Refresh events"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-[10rem_5rem_1fr] gap-2 px-3 py-1.5 text-[10px] text-[var(--text-muted)] uppercase bg-white/5 border-b border-white/6">
        <span>Time</span>
        <span>Level</span>
        <span>Message</span>
      </div>

      <div className="max-h-72 overflow-y-auto">
        {loading && events.length === 0 ? (
          <div className="flex items-center justify-center gap-2 px-3 py-6 text-xs text-[var(--text-muted)]">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading events...
          </div>
        ) : events.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 px-3 py-6 text-xs text-[var(--text-muted)]">
            <AlertCircle className="h-4 w-4" />
            <span>No events found</span>
          </div>
        ) : (
          events.map((evt, idx) => (
            <div
              key={idx}
              className="grid grid-cols-[10rem_5rem_1fr] gap-2 px-3 py-1.5 text-xs items-center hover:bg-white/5 transition-colors border-b border-white/6 last:border-b-0"
            >
              <span className="font-mono text-[var(--text-secondary)]">
                {new Date(evt.TimeCreated).toLocaleString()}
              </span>
              <span>
                <LevelBadge level={evt.LevelDisplayName} />
              </span>
              <span
                className="truncate text-[var(--text-primary)]"
                title={evt.Message}
              >
                {evt.Message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
