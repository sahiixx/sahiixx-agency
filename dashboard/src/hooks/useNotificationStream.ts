import { useEffect, useState } from 'react'
import { toast } from 'sonner'

export interface NotificationMessage {
  id: string
  channel: string
  title: string
  body: string
  created_at: string
  status: string
}

export function useNotificationStream() {
  const [connected, setConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<NotificationMessage | null>(null)

  useEffect(() => {
    const eventSource = new EventSource('/api/notifications/stream')

    eventSource.onopen = () => {
      setConnected(true)
    }

    eventSource.onmessage = (event) => {
      if (!event.data || event.data.startsWith(':')) return
      try {
        const notification: NotificationMessage = JSON.parse(event.data)
        setLastMessage(notification)
        if (notification.channel === 'sse') {
          toast.info(notification.title, {
            description: notification.body,
          })
        }
      } catch {
        // ignore malformed events
      }
    }

    eventSource.onerror = () => {
      setConnected(false)
    }

    return () => {
      eventSource.close()
    }
  }, [])

  return { connected, lastMessage }
}
