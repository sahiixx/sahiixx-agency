import { useState, useMemo } from 'react'
import { Play, Square, RotateCcw, Filter } from 'lucide-react'

interface Service {
  Name: string
  Status: string
  StartType: string
}

interface ServiceManagerProps {
  services: Service[]
  onAction: (name: string, action: 'start' | 'stop' | 'restart') => void
  loading: boolean
}

export function ServiceManager({ services, onAction, loading }: ServiceManagerProps) {
  const [filter, setFilter] = useState<'all' | 'running' | 'stopped'>('all')
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    let list = services
    if (filter !== 'all') {
      list = list.filter(s => s.Status.toLowerCase() === filter)
    }
    if (search) {
      list = list.filter(s => s.Name.toLowerCase().includes(search.toLowerCase()))
    }
    return list
  }, [services, filter, search])

  const statusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running': return 'bg-green-500/20 text-green-400'
      case 'stopped': return 'bg-red-500/20 text-red-400'
      default: return 'bg-amber-500/20 text-amber-400'
    }
  }

  const FilterBtn = ({ label, value }: { label: string; value: 'all' | 'running' | 'stopped' }) => (
    <button
      onClick={() => setFilter(value)}
      className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
        filter === value ? 'bg-accent-cyan/20 text-accent-cyan' : 'bg-white/5 text-[var(--text-muted)] hover:bg-white/10'
      }`}
    >
      {label}
    </button>
  )

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Filter className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Search services..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full h-8 rounded-md bg-white/5 border border-white/6 pl-7 pr-2 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-accent-cyan/50"
          />
        </div>
        <FilterBtn label="All" value="all" />
        <FilterBtn label="Running" value="running" />
        <FilterBtn label="Stopped" value="stopped" />
      </div>

      <div className="rounded-md border border-white/6 overflow-hidden">
        <div className="grid grid-cols-[1fr_6rem_5rem_6rem] gap-1 px-2 py-1.5 text-[10px] text-[var(--text-muted)] uppercase bg-white/5">
          <span>Name</span>
          <span className="text-center">Status</span>
          <span className="text-center">Start</span>
          <span className="text-center">Actions</span>
        </div>
        <div className="max-h-64 overflow-y-auto">
          {loading && filtered.length === 0 ? (
            <div className="px-2 py-4 text-xs text-[var(--text-muted)]">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="px-2 py-4 text-xs text-[var(--text-muted)]">No services found</div>
          ) : (
            filtered.map(svc => (
              <div
                key={svc.Name}
                className="grid grid-cols-[1fr_6rem_5rem_6rem] gap-1 px-2 py-1.5 text-xs items-center hover:bg-white/5 transition-colors"
              >
                <span className="truncate text-[var(--text-primary)]">{svc.Name}</span>
                <span className={`text-center text-[10px] font-medium px-1 py-0.5 rounded ${statusColor(svc.Status)}`}>
                  {svc.Status}
                </span>
                <span className="text-center text-[10px] text-[var(--text-muted)]">{svc.StartType}</span>
                <div className="flex items-center justify-center gap-1">
                  <button
                    onClick={() => onAction(svc.Name, 'start')}
                    disabled={svc.Status === 'Running'}
                    className="p-1 rounded text-green-400 hover:bg-green-500/10 disabled:opacity-20 transition-colors"
                    title="Start"
                  >
                    <Play className="h-3 w-3" />
                  </button>
                  <button
                    onClick={() => onAction(svc.Name, 'stop')}
                    disabled={svc.Status === 'Stopped'}
                    className="p-1 rounded text-red-400 hover:bg-red-500/10 disabled:opacity-20 transition-colors"
                    title="Stop"
                  >
                    <Square className="h-3 w-3" />
                  </button>
                  <button
                    onClick={() => onAction(svc.Name, 'restart')}
                    className="p-1 rounded text-amber-400 hover:bg-amber-500/10 transition-colors"
                    title="Restart"
                  >
                    <RotateCcw className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
