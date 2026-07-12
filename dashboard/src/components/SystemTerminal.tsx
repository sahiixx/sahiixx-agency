import { useState, useRef, useEffect } from 'react'
import { Terminal, Send, Zap } from 'lucide-react'

interface CommandHistory {
  id: string
  command: string
  output: string
  error: boolean
  timestamp: Date
}

interface SystemTerminalProps {
  onExecute: (command: string) => Promise<string>
}

const QUICK_COMMANDS = [
  { label: 'IP Config', command: 'ipconfig /all' },
  { label: 'Flush DNS', command: 'ipconfig /flushdns' },
  { label: 'Ping Google', command: 'ping 8.8.8.8 -n 4' },
  { label: 'Netstat', command: 'netstat -an' },
  { label: 'Tasklist', command: 'tasklist' },
  { label: 'System Info', command: 'systeminfo | findstr /B /C:"OS" /C:"Processor" /C:"Total Physical Memory"' },
]

export function SystemTerminal({ onExecute }: SystemTerminalProps) {
  const [input, setInput] = useState('')
  const [history, setHistory] = useState<CommandHistory[]>([])
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history])

  const execute = async (cmd: string) => {
    if (!cmd.trim() || loading) return
    setLoading(true)
    const id = Date.now().toString()
    setHistory(prev => [...prev, { id, command: cmd, output: '', error: false, timestamp: new Date() }])
    try {
      const output = await onExecute(cmd)
      setHistory(prev => prev.map(h => h.id === id ? { ...h, output } : h))
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error'
      setHistory(prev => prev.map(h => h.id === id ? { ...h, output: msg, error: true } : h))
    } finally {
      setLoading(false)
      setInput('')
    }
  }

  return (
    <div className="space-y-3">
      {/* Quick Commands */}
      <div className="flex flex-wrap gap-1.5">
        {QUICK_COMMANDS.map(qc => (
          <button
            key={qc.label}
            onClick={() => execute(qc.command)}
            disabled={loading}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-medium bg-white/5 text-[var(--text-muted)] hover:bg-white/10 hover:text-[var(--text-primary)] transition-colors disabled:opacity-40"
          >
            <Zap className="h-3 w-3" />
            {qc.label}
          </button>
        ))}
      </div>

      {/* Output */}
      <div className="rounded-md border border-white/6 bg-black/50 p-3 space-y-2 max-h-80 overflow-y-auto font-mono text-[10px]">
        {history.length === 0 && (
          <div className="text-[var(--text-muted)] py-4 text-center">Run a command to see output...</div>
        )}
        {history.map(h => (
          <div key={h.id} className="space-y-1">
            <div className="flex items-center gap-1 text-accent-cyan">
              <Terminal className="h-3 w-3" />
              <span>PS&gt; {h.command}</span>
            </div>
            {h.output ? (
              <pre className={`whitespace-pre-wrap break-all pl-4 ${h.error ? 'text-red-400' : 'text-[var(--text-secondary)]'}`}>
                {h.output}
              </pre>
            ) : loading ? (
              <div className="pl-4 text-[var(--text-muted)]">Running...</div>
            ) : null}
          </div>
        ))}
        <div ref={scrollRef} />
      </div>

      {/* Input */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1 text-accent-cyan text-xs font-mono">
          <Terminal className="h-3 w-3" />
          PS&gt;
        </div>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && execute(input)}
          placeholder="Enter PowerShell command..."
          disabled={loading}
          className="flex-1 h-8 rounded-md bg-white/5 border border-white/6 px-2 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-accent-cyan/50 font-mono disabled:opacity-40"
        />
        <button
          onClick={() => execute(input)}
          disabled={loading || !input.trim()}
          className="p-1.5 rounded-md bg-accent-cyan/10 text-accent-cyan hover:bg-accent-cyan/20 transition-colors disabled:opacity-40"
        >
          <Send className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}
