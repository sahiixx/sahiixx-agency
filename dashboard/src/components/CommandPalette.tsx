import { useState, useEffect, useRef } from 'react'
import { Search, Command, CornerDownLeft, ArrowUp, ArrowDown } from 'lucide-react'

interface CommandItem {
  id: string
  label: string
  shortcut?: string
  action: () => void
}

interface CommandPaletteProps {
  open: boolean
  onClose: () => void
  items: CommandItem[]
}

export function CommandPalette({ open, onClose, items }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const filtered = items.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase())
  )

  // Reset query/index when palette opens
  useEffect(() => {
    if (open) {
      // This is a deliberate reset tied to the open prop; using a microtask avoids synchronous
      // setState in the effect body while still clearing the input before focus.
      const timeoutId = window.setTimeout(() => {
        setQuery('')
        setSelectedIndex(0)
        inputRef.current?.focus()
      }, 0)
      return () => window.clearTimeout(timeoutId)
    }
  }, [open])

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (!open) return
      switch (e.key) {
        case 'Escape':
          onClose()
          break
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex((i) => (i + 1) % filtered.length)
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((i) => (i - 1 + filtered.length) % filtered.length)
          break
        case 'Enter':
          e.preventDefault()
          if (filtered[selectedIndex]) {
            filtered[selectedIndex].action()
            onClose()
          }
          break
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [open, filtered, selectedIndex, onClose])

  // Scroll selected into view
  useEffect(() => {
    const el = listRef.current?.children[selectedIndex] as HTMLElement | undefined
    el?.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[20vh]">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg rounded-xl border border-white/10 bg-[var(--bg-surface)] shadow-2xl overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/6">
          <Search className="h-4 w-4 text-[var(--text-muted)]" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelectedIndex(0)
            }}
            placeholder="Search commands..."
            className="flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none"
          />
          <div className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
            <kbd className="rounded bg-white/5 px-1.5 py-0.5 font-mono"><ArrowUp className="h-3 w-3 inline" /></kbd>
            <kbd className="rounded bg-white/5 px-1.5 py-0.5 font-mono"><ArrowDown className="h-3 w-3 inline" /></kbd>
            <kbd className="rounded bg-white/5 px-1.5 py-0.5 font-mono"><CornerDownLeft className="h-3 w-3 inline" /></kbd>
          </div>
        </div>

        <div ref={listRef} className="max-h-80 overflow-y-auto py-2">
          {filtered.length === 0 && (
            <div className="px-4 py-6 text-center text-sm text-[var(--text-muted)]">No commands found.</div>
          )}
          {filtered.map((item, i) => (
            <button
              key={item.id}
              onClick={() => {
                item.action()
                onClose()
              }}
              onMouseEnter={() => setSelectedIndex(i)}
              className={`w-full flex items-center justify-between px-4 py-2.5 text-sm transition-colors ${
                i === selectedIndex
                  ? 'bg-accent-cyan/10 text-accent-cyan'
                  : 'text-[var(--text-secondary)] hover:bg-white/5'
              }`}
            >
              <span>{item.label}</span>
              {item.shortcut && (
                <kbd className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] font-mono text-[var(--text-muted)]">
                  {item.shortcut}
                </kbd>
              )}
            </button>
          ))}
        </div>

        <div className="flex items-center justify-between px-4 py-2 border-t border-white/6 text-[10px] text-[var(--text-muted)]">
          <div className="flex items-center gap-1">
            <Command className="h-3 w-3" />
            <span>Agency Command Palette</span>
          </div>
          <span>Esc to close</span>
        </div>
      </div>
    </div>
  )
}
