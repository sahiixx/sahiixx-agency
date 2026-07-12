import { useState, useMemo } from 'react'
import { Search, X, ArrowUpDown } from 'lucide-react'

interface Process {
  pid: number
  name: string
  cpu_percent: number
  memory_mb: number
  status: string
}

interface ProcessManagerProps {
  processes: Process[]
  onKill: (pid: number, name: string) => void
  loading: boolean
}

type SortKey = 'name' | 'pid' | 'cpu' | 'mem'
type SortDir = 'asc' | 'desc'

export function ProcessManager({ processes, onKill, loading }: ProcessManagerProps) {
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('cpu')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const filtered = useMemo(() => {
    let list = processes.filter(p =>
      p.name.toLowerCase().includes(search.toLowerCase())
    )
    list.sort((a, b) => {
      const mul = sortDir === 'asc' ? 1 : -1
      switch (sortKey) {
        case 'name': return mul * a.name.localeCompare(b.name)
        case 'pid': return mul * (a.pid - b.pid)
        case 'cpu': return mul * (a.cpu_percent - b.cpu_percent)
        case 'mem': return mul * (a.memory_mb - b.memory_mb)
      }
    })
    return list
  }, [processes, search, sortKey, sortDir])

  const SortHeader = ({ label, key }: { label: string; key: SortKey }) => (
    <button
      onClick={() => toggleSort(key)}
      className="flex items-center gap-1 text-[10px] uppercase hover:text-[var(--text-primary)] transition-colors"
    >
      {label}
      {sortKey === key && <ArrowUpDown className="h-3 w-3" />}
    </button>
  )

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Search processes..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full h-8 rounded-md bg-white/5 border border-white/6 pl-7 pr-2 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-accent-cyan/50"
          />
        </div>
        <span className="text-[10px] text-[var(--text-muted)] font-mono">{filtered.length} / {processes.length}</span>
      </div>

      <div className="rounded-md border border-white/6 overflow-hidden">
        <div className="grid grid-cols-[1fr_4rem_4rem_4rem_3rem] gap-1 px-2 py-1.5 text-[10px] text-[var(--text-muted)] uppercase bg-white/5">
          <SortHeader label="Name" key="name" />
          <div className="text-right"><SortHeader label="PID" key="pid" /></div>
          <div className="text-right"><SortHeader label="CPU" key="cpu" /></div>
          <div className="text-right"><SortHeader label="Mem" key="mem" /></div>
          <span />
        </div>
        <div className="max-h-64 overflow-y-auto">
          {loading && filtered.length === 0 ? (
            <div className="px-2 py-4 text-xs text-[var(--text-muted)]">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="px-2 py-4 text-xs text-[var(--text-muted)]">No processes found</div>
          ) : (
            filtered.map(proc => (
              <div
                key={proc.pid}
                className="grid grid-cols-[1fr_4rem_4rem_4rem_3rem] gap-1 px-2 py-1.5 text-xs items-center hover:bg-white/5 transition-colors"
              >
                <span className="truncate text-[var(--text-primary)]">{proc.name}</span>
                <span className="text-right font-mono text-[var(--text-muted)]">{proc.pid}</span>
                <span className="text-right font-mono text-accent-cyan">{proc.cpu_percent.toFixed(1)}%</span>
                <span className="text-right font-mono text-accent-purple">{proc.memory_mb.toFixed(0)}MB</span>
                <button
                  onClick={() => onKill(proc.pid, proc.name)}
                  className="flex items-center justify-center rounded p-1 text-accent-red hover:bg-accent-red/10 transition-colors"
                  title="Kill process"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
