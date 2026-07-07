import { useState, useRef, useEffect } from 'react'
import { Search, X, Filter } from 'lucide-react'
import { motion } from 'framer-motion'
import type { RepoNode } from '@/lib/graph-data'
import { useBrand } from '@/components/BrandProvider'

interface HeroBarProps {
  repos: RepoNode[]
  viewMode: 'category' | 'layer' | 'era'
  onViewModeChange: (mode: 'category' | 'layer' | 'era') => void
  onFilterToggle: () => void
  onSearchSelect: (repo: RepoNode) => void
}

export default function HeroBar({
  repos,
  viewMode,
  onViewModeChange,
  onFilterToggle,
  onSearchSelect,
}: HeroBarProps) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const { brandName } = useBrand()

  const results = query.trim()
    ? repos
        .filter((r) => {
          const q = query.toLowerCase()
          return (
            r.name.toLowerCase().includes(q) ||
            r.description.toLowerCase().includes(q) ||
            r.category.toLowerCase().includes(q) ||
            r.language.toLowerCase().includes(q)
          )
        })
        .slice(0, 8)
    : []

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === '/' || (e.metaKey && e.key === 'k')) {
        e.preventDefault()
        inputRef.current?.focus()
      }
      if (e.key === 'Escape') {
        setQuery('')
        setOpen(false)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [])

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    window.addEventListener('mousedown', handleClick)
    return () => window.removeEventListener('mousedown', handleClick)
  }, [])

  return (
    <div className="fixed top-16 left-0 right-0 z-40 px-4 py-3 flex items-center justify-between gap-4 pointer-events-none">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4 }}
        className="pointer-events-auto flex items-center gap-3 hidden lg:flex"
      >
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-green opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-green" />
          </span>
          <span className="font-mono text-[11px] text-text-muted uppercase tracking-wider">
            Live
          </span>
        </div>
        <div>
          <h1 className="font-display font-semibold text-[24px] leading-[1.2] text-text-primary">
            {brandName}
          </h1>
          <p className="text-body-sm text-text-muted">
            Unified AI orchestration for all repos
          </p>
        </div>
      </motion.div>

      <motion.div
        ref={containerRef}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.15 }}
        className="pointer-events-auto flex-1 max-w-md mx-auto relative"
      >
        <div className="glass-input flex items-center gap-2 px-3 h-11 transition-all focus-within:border-accent-cyan focus-within:shadow-[0_0_20px_rgba(0,212,255,0.2)]">
          <Search className="w-4 h-4 text-text-muted shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setOpen(true)
            }}
            onFocus={() => setOpen(true)}
            placeholder="Search 113 repositories by name, category, language..."
            className="bg-transparent border-none outline-none text-[14px] text-text-primary placeholder:text-text-muted w-full"
          />
          {query && (
            <button
              onClick={() => {
                setQuery('')
                setOpen(false)
              }}
              className="shrink-0"
            >
              <X className="w-4 h-4 text-text-muted hover:text-text-secondary" />
            </button>
          )}
        </div>

        {open && results.length > 0 && (
          <div className="absolute top-full mt-2 left-0 right-0 glass-panel rounded-[10px] overflow-hidden max-h-80 overflow-y-auto">
            {results.map((repo) => (
              <button
                key={repo.id}
                onClick={() => {
                  onSearchSelect(repo)
                  setQuery('')
                  setOpen(false)
                }}
                className="w-full text-left px-4 py-3 hover:bg-white/5 transition-colors flex items-center gap-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-[14px] font-medium text-text-primary truncate">
                    {repo.name}
                  </div>
                  <div className="text-[11px] font-mono text-text-muted truncate">
                    {repo.category} · {repo.language}
                  </div>
                </div>
                <div className="text-[11px] font-mono text-text-muted shrink-0">
                  {repo.stars.toLocaleString()} ★
                </div>
              </button>
            ))}
          </div>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.3 }}
        className="pointer-events-auto flex items-center gap-2"
      >
        <div className="glass-tag flex items-center h-9 overflow-hidden">
          {(['category', 'layer', 'era'] as const).map((m) => (
            <button
              key={m}
              onClick={() => onViewModeChange(m)}
              className={`px-3 py-1 text-[12px] font-medium capitalize transition-all ${
                viewMode === m
                  ? 'bg-accent-cyan text-text-inverse'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {m}
            </button>
          ))}
        </div>

        <button
          onClick={onFilterToggle}
          className="glass-tag w-9 h-9 flex items-center justify-center hover:bg-white/10 transition-colors"
        >
          <Filter className="w-4 h-4 text-text-secondary" />
        </button>
      </motion.div>
    </div>
  )
}
