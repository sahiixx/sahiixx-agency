import { useState, useRef, useEffect, useCallback } from 'react'

export interface TaskUpdate {
  id: string
  status: string
  message: string
  progress: number
  result?: string
  error?: string
  intent?: string
  module?: string
  module_id?: string
}

interface UseTaskStreamOptions {
  onMessage?: (update: TaskUpdate) => void
  onComplete?: (update: TaskUpdate) => void
  onError?: (error: string) => void
}

export function useTaskStream(taskId: string | undefined | null, options: UseTaskStreamOptions = {}) {
  const [task, setTask] = useState<TaskUpdate | null>(null)
  const [connected, setConnected] = useState(false)
  const [finished, setFinished] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  const optionsRef = useRef(options)

  useEffect(() => {
    optionsRef.current = options
  })

  const handleOpen = useCallback(() => setConnected(true), [])

  const handleMessage = useCallback((event: MessageEvent) => {
    if (!event.data || event.data.startsWith(':')) return
    try {
      const data: TaskUpdate = JSON.parse(event.data)
      setTask(data)
      optionsRef.current.onMessage?.(data)
      const terminal = ['completed', 'failed', 'cancelled']
      if (terminal.includes(data.status)) {
        setFinished(true)
        optionsRef.current.onComplete?.(data)
      }
    } catch (e) {
      optionsRef.current.onError?.(e instanceof Error ? e.message : String(e))
    }
  }, [])

  const handleError = useCallback(() => {
    setConnected(false)
    optionsRef.current.onError?.('EventSource connection error')
  }, [])

  useEffect(() => {
    if (!taskId) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      return
    }

    window.setTimeout(() => setFinished(false), 0)
    const eventSource = new EventSource(`/api/tasks/${taskId}/stream`)
    eventSourceRef.current = eventSource

    eventSource.onopen = handleOpen
    eventSource.onmessage = handleMessage
    eventSource.onerror = handleError

    return () => {
      eventSource.close()
      eventSourceRef.current = null
    }
  }, [taskId, handleOpen, handleMessage, handleError])

  return { task, connected, finished }
}
