import { useEffect, useRef } from 'react'

interface ChatMessage {
  id: string
  role: 'user' | 'agency'
  content: string
  created_at: string
}

interface ChatThreadProps {
  messages: ChatMessage[]
}

export function ChatThread({ messages }: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-[var(--text-muted)]">
        <div className="text-4xl mb-4">🤖</div>
        <p className="text-sm">Welcome to the Agency Command Center.</p>
        <p className="text-xs mt-1">Send a message to start working with your AI agency.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-accent-cyan/15 text-[var(--text-primary)] border border-accent-cyan/20'
                : 'bg-[var(--bg-elevated)] text-[var(--text-secondary)] border border-white/6'
            }`}
          >
            <div className="text-xs font-medium mb-1 opacity-70">
              {msg.role === 'user' ? 'You' : 'Agency'}
            </div>
            <div className="whitespace-pre-wrap">{msg.content}</div>
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
