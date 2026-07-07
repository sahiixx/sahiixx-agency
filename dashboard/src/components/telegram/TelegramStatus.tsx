import { useEffect, useState } from 'react'
import { Bot } from 'lucide-react'

interface TelegramStatusData {
  enabled: boolean
  has_token: boolean
  webhook_url: string | null
  allowed_chat_ids_count: number
}

export function TelegramStatus() {
  const [status, setStatus] = useState<TelegramStatusData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    fetch('/api/telegram/status')
      .then((r) => {
        if (!r.ok) throw new Error(`Status fetch failed: ${r.status}`)
        return r.json()
      })
      .then((data) => {
        if (cancelled) return
        setStatus(data)
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

  if (loading) return <div className="text-sm text-[var(--text-muted)]">Loading Telegram status...</div>
  if (error) return <div className="text-sm text-red-400">{error}</div>
  if (!status) return null

  return (
    <div className="rounded-lg border border-white/6 bg-[var(--bg-elevated)] p-4">
      <div className="flex items-center gap-2 mb-2">
        <Bot className="h-4 w-4 text-accent-cyan" />
        <h3 className="font-medium text-[var(--text-primary)]">Telegram Bot</h3>
      </div>
      <div className="space-y-1 text-sm text-[var(--text-secondary)]">
        <div className="flex justify-between">
          <span>Enabled</span>
          <span className={status.enabled ? 'text-accent-green' : 'text-text-muted'}>
            {status.enabled ? 'Yes' : 'No'}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Token configured</span>
          <span className={status.has_token ? 'text-accent-green' : 'text-text-muted'}>
            {status.has_token ? 'Yes' : 'No'}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Allowed chats</span>
          <span>{status.allowed_chat_ids_count}</span>
        </div>
        {status.webhook_url && (
          <div className="truncate text-xs text-[var(--text-muted)]">{status.webhook_url}</div>
        )}
      </div>
    </div>
  )
}
