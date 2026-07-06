import { useState, useEffect, useCallback } from 'react'
import { Loader2, AlertCircle, Check, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Approval {
  id: string
  title: string
  description?: string
  requester: string
  created_at: string
}

interface ApprovalQueueProps {
  compact?: boolean
}

export function ApprovalQueue({ compact }: ApprovalQueueProps) {
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [acting, setActing] = useState<Record<string, boolean>>({})

  const fetchApprovals = useCallback(async () => {
    try {
      const res = await fetch('/api/approvals/pending')
      if (!res.ok) throw new Error(`Approvals fetch failed: ${res.status}`)
      const data = await res.json()
      setApprovals(Array.isArray(data) ? data : [])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch approvals')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchApprovals()
    const interval = setInterval(fetchApprovals, 5000)
    return () => clearInterval(interval)
  }, [fetchApprovals])

  const handleAction = useCallback(
    async (id: string, action: 'approve' | 'reject') => {
      setActing((prev) => ({ ...prev, [id]: true }))
      try {
        const res = await fetch(`/api/approvals/${id}/${action}`, { method: 'POST' })
        if (!res.ok) throw new Error(`${action} failed: ${res.status}`)
        setApprovals((prev) => prev.filter((a) => a.id !== id))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Action failed')
      } finally {
        setActing((prev) => ({ ...prev, [id]: false }))
      }
    },
    []
  )

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading approvals...
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

  if (approvals.length === 0) {
    return <div className="text-sm text-[var(--text-muted)]">No pending approvals.</div>
  }

  return (
    <div className={cn('space-y-3', compact && 'space-y-2')}>
      {approvals.map((approval) => (
        <div
          key={approval.id}
          className={cn(
            'rounded-lg border border-white/6 bg-[var(--bg-elevated)]',
            compact ? 'p-3' : 'p-4'
          )}
        >
          <div className="text-sm font-medium text-[var(--text-primary)]">{approval.title}</div>
          {approval.description && (
            <div className="text-xs text-[var(--text-secondary)] mt-1">{approval.description}</div>
          )}
          <div className="text-[11px] text-[var(--text-muted)] mt-1">
            {approval.requester} · {new Date(approval.created_at).toLocaleString()}
          </div>
          <div className="flex items-center gap-2 mt-3">
            <button
              onClick={() => handleAction(approval.id, 'approve')}
              disabled={acting[approval.id]}
              className="inline-flex items-center gap-1 rounded-md bg-accent-green/10 text-accent-green border border-accent-green/20 px-3 py-1.5 text-xs font-medium hover:bg-accent-green/20 disabled:opacity-40"
            >
              <Check className="h-3.5 w-3.5" />
              Approve
            </button>
            <button
              onClick={() => handleAction(approval.id, 'reject')}
              disabled={acting[approval.id]}
              className="inline-flex items-center gap-1 rounded-md bg-accent-red/10 text-accent-red border border-accent-red/20 px-3 py-1.5 text-xs font-medium hover:bg-accent-red/20 disabled:opacity-40"
            >
              <X className="h-3.5 w-3.5" />
              Reject
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
