import { useState, useEffect } from 'react'
import { Server, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { motion } from 'framer-motion'

interface StatusInfo {
  name: string
  version: string
  status: string
}

export default function StatusCard() {
  const [status, setStatus] = useState<StatusInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8080'
        const res = await fetch(`${apiBase}/status`)
        if (!res.ok) throw new Error('Failed to fetch status')
        const data = await res.json()
        setStatus(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchStatus()
  }, [])

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel rounded-[14px] p-4"
      >
        <div className="flex items-center gap-3 text-text-muted">
          <Loader2 className="w-5 h-5 animate-spin text-primary" />
          <span className="font-mono text-[13px]">Loading status...</span>
        </div>
      </motion.div>
    )
  }

  if (error || !status) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel rounded-[14px] p-4 border border-destructive/30"
      >
        <div className="flex items-center gap-3 text-destructive">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <div>
            <p className="font-medium text-sm">Failed to load status</p>
            <p className="font-mono text-[12px] text-text-muted mt-1">{error || 'Unknown error'}</p>
          </div>
        </div>
      </motion.div>
    )
  }

  const isHealthy = status.status === 'running' || status.status === 'healthy'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel rounded-[14px] p-4"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Server className={`w-5 h-5 ${isHealthy ? 'text-green-500' : 'text-destructive'}`} />
            <h3 className="font-display text-h3 text-text-primary">{status.name}</h3>
            <span className="font-mono text-[13px] text-text-secondary px-2 py-0.5 rounded bg-muted">
              v{status.version}
            </span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle className={`w-4 h-4 ${isHealthy ? 'text-green-500' : 'text-destructive'}`} />
            <span className={`font-medium ${isHealthy ? 'text-green-500' : 'text-destructive'}`}>
              {isHealthy ? 'Running' : 'Degraded'}
            </span>
            <span className="text-text-muted font-mono text-[12px]">API: {status.status}</span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <span 
            className={`w-2.5 h-2.5 rounded-full ${isHealthy ? 'bg-green-500 animate-pulse' : 'bg-destructive'}`}
            title={isHealthy ? 'Healthy' : 'Unhealthy'}
          />
        </div>
      </div>
    </motion.div>
  )
}