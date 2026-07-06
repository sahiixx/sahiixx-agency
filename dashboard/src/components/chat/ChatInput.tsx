import { useState, useCallback } from 'react'
import { Send } from 'lucide-react'

interface ChatInputProps {
  onSend: (text: string) => void
  disabled?: boolean
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState('')

  const handleSend = useCallback(() => {
    if (disabled || !text.trim()) return
    onSend(text.trim())
    setText('')
  }, [text, disabled, onSend])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  return (
    <div className="flex items-end gap-3">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder="Type a command or question..."
        rows={1}
        className="flex-1 resize-none rounded-xl bg-[var(--bg-elevated)] border border-white/8 px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-accent-cyan/30 focus:border-accent-cyan/30 disabled:opacity-50"
        style={{ minHeight: '48px', maxHeight: '160px' }}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent-cyan text-white hover:bg-accent-cyan/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        <Send className="h-5 w-5" />
      </button>
    </div>
  )
}
