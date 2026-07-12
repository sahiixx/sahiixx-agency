import { useEffect, useState, useRef, useCallback } from 'react'

export interface DeviceMetrics {
  cpu: number
  memory: number
  disk: number
  net_sent: number
  net_recv: number
  timestamp: number
}

export function useDeviceStream(enabled: boolean = true) {
  const [metrics, setMetrics] = useState<DeviceMetrics | null>(null)
  const [connected, setConnected] = useState(false)
  const [history, setHistory] = useState<DeviceMetrics[]>([])
  const esRef = useRef<EventSource | null>(null)

  const disconnect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    setConnected(false)
  }, [])

  useEffect(() => {
    if (!enabled) {
      disconnect()
      return
    }

    const es = new EventSource('/api/device/stream')
    esRef.current = es

    es.onopen = () => {
      setConnected(true)
    }

    es.onmessage = (event) => {
      if (!event.data || event.data.startsWith(':')) return
      try {
        const data: DeviceMetrics = JSON.parse(event.data)
        if ('cpu' in data) {
          setMetrics(data)
          setHistory(prev => [...prev, data].slice(-60))
        }
      } catch {
        // ignore malformed
      }
    }

    es.onerror = () => {
      setConnected(false)
    }

    return () => {
      es.close()
      esRef.current = null
    }
  }, [enabled, disconnect])

  return { metrics, connected, history, disconnect }
}
