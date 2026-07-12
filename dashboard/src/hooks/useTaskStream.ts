import { useEffect, useState, useCallback } from 'react'

export interface TaskUpdate {
  id: string
  intent: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  module?: string
  module_id?: string
  result?: string
  error?: string
  created_at: string
}

export function useTaskStream(taskId: string | null) {
  const [task, setTask] = useState<TaskUpdate | null>(null)
  const [connected, setConnected] = useState(false)
  const [finished, setFinished] = useState(false)

  const disconnect = useCallback(() => {
    setConnected(false)
    setFinished(true)
  }, [])

  useEffect(() => {
    if (!taskId) {
      setTask(null)
      setConnected(false)
      setFinished(false)
      return
    }

    setFinished(false)
    const eventSource = new EventSource(`/api/tasks/${taskId}/stream`)

    eventSource.onopen = () => {
      setConnected(true)
    }

    eventSource.onmessage = (event) => {
      if (!event.data || event.data.startsWith(':')) return
      try {
        const data: TaskUpdate = JSON.parse(event.data)
        setTask(data)
        const terminal = ['completed', 'failed', 'cancelled']
        if (terminal.includes(data.status)) {
          setFinished(true)
          eventSource.close()
        }
      } catch {
        // ignore malformed events
      }
    }

    eventSource.onerror = () => {
      setConnected(false)
      eventSource.close()
    }

    return () => {
      eventSource.close()
      setConnected(false)
    }
  }, [taskId])

  return { task, connected, finished, disconnect }
}
