import { useState } from 'react'
import { AlertCircle, CheckCircle2, RefreshCw, Download } from 'lucide-react'

interface UpdateItem {
  title: string
  downloaded: boolean
}

interface WindowsUpdateProps {
  updates: UpdateItem[]
  pending: number
  loading: boolean
  onCheck: () => void
}

export function WindowsUpdate({ updates, pending, loading, onCheck }: WindowsUpdateProps) {
  const [lastCheck, setLastCheck] = useState<Date | null>(null)
  const [isChecking, setIsChecking] = useState(false)

  const handleCheck = () => {
    setIsChecking(true)
    onCheck()
    setLastCheck(new Date())
    // Simulate spinner tied to external loading; reset local spinner after a brief delay if parent doesn't update
    setTimeout(() => setIsChecking(false), 2000)
  }

  const allClear = pending === 0 && updates.length === 0

  return (
    <div className="rounded-lg border border-white/6 bg-[var(--bg-elevated)] p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">
          <Download className="h-3.5 w-3.5" />
          Windows Update
        </div>
        <div className="flex items-center gap-2">
          {allClear ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-accent-green/10 px-2 py-0.5 text-[10px] font-medium text-accent-green">
              <CheckCircle2 className="h-3 w-3" />
              Up to date
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-accent-amber/10 px-2 py-0.5 text-[10px] font-medium text-accent-amber">
              <AlertCircle className="h-3 w-3" />
              {pending} pending
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={handleCheck}
          disabled={loading || isChecking}
          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium bg-white/5 text-[var(--text-secondary)] hover:bg-white/10 hover:text-[var(--text-primary)] transition-colors disabled:opacity-40"
        >
          {(loading || isChecking) ? (
            <RefreshCw className="h-3 w-3 animate-spin" />
          ) : (
            <RefreshCw className="h-3 w-3" />
          )}
          Check for Updates
        </button>
        {lastCheck && (
          <span className="text-[10px] text-[var(--text-muted)]">
            Last check: {lastCheck.toLocaleTimeString()}
          </span>
        )}
      </div>

      {loading && updates.length === 0 ? (
        <div className="h-16 rounded-md bg-white/5 animate-pulse" />
      ) : updates.length === 0 ? (
        <div className="text-xs text-[var(--text-muted)] py-2">
          {allClear ? 'No pending updates.' : 'No update details available.'}
        </div>
      ) : (
        <div className="rounded-md border border-white/6 overflow-hidden max-h-60 overflow-y-auto">
          <div className="grid grid-cols-[1fr_5rem] gap-1 px-2 py-1.5 text-[10px] text-[var(--text-muted)] uppercase bg-white/5">
            <span>Update Title</span>
            <span className="text-right">Status</span>
          </div>
          {updates.map((u, i) => (
            <div
              key={`${u.title}-${i}`}
              className="grid grid-cols-[1fr_5rem] gap-1 px-2 py-1.5 text-xs items-center hover:bg-white/5 transition-colors"
            >
              <span className="truncate text-[var(--text-primary)]" title={u.title}>
                {u.title}
              </span>
              <span className="text-right">
                {u.downloaded ? (
                  <span className="inline-flex items-center gap-1 text-[10px] text-accent-green">
                    <CheckCircle2 className="h-3 w-3" />
                    Ready
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[10px] text-accent-amber">
                    <Download className="h-3 w-3" />
                    Pending
                  </span>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
