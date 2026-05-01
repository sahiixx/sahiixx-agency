import { motion, AnimatePresence } from 'framer-motion'
import { X, Star, ExternalLink, Copy, Check, Play, Loader2, Terminal } from 'lucide-react'
import { useState, useMemo } from 'react'
import {
  CATEGORY_COLORS,
  LAYER_COLORS,
  ERA_COLORS,
  EDGE_STYLES,
  type RepoNode,
  type LinkData,
  formatStars,
} from '@/lib/graph-data'

interface DetailDrawerProps {
  repo: RepoNode | null
  links: LinkData[]
  repos: RepoNode[]
  onClose: () => void
  onHighlight: (repoId: string) => void
  onOpenRepo: (repoId: string) => void
}

export default function DetailDrawer({
  repo,
  links,
  repos,
  onClose,
  onHighlight,
  onOpenRepo,
}: DetailDrawerProps) {
  const [copied, setCopied] = useState(false)
  const [execStatus, setExecStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [execResult, setExecResult] = useState<{
    status?: string
    returncode?: number
    stdout?: string
    stderr?: string
    command?: string
    entrypoint?: string
    type?: string
  } | null>(null)

  const handleExecute = async () => {
    if (!repo) return
    setExecStatus('loading')
    setExecResult(null)
    try {
      const res = await fetch(`/tasks/${encodeURIComponent(repo.id)}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const data = await res.json()
      setExecResult(data)
      setExecStatus(data.status === 'success' ? 'success' : 'error')
    } catch (err) {
      setExecResult({ stderr: String(err) })
      setExecStatus('error')
    }
  }

  const connected = useMemo(() => {
    if (!repo) return []
    return links
      .filter(
        (l) =>
          (typeof l.source === 'string' ? l.source : l.source.id) === repo.id ||
          (typeof l.target === 'string' ? l.target : l.target.id) === repo.id
      )
      .map((l) => {
        const sourceId =
          typeof l.source === 'string' ? l.source : l.source.id
        const targetId =
          typeof l.target === 'string' ? l.target : l.target.id
        const otherId = sourceId === repo.id ? targetId : sourceId
        const other = repos.find((r) => r.id === otherId)
        return { ...l, other, otherId }
      })
      .filter((l) => l.other)
  }, [repo, links, repos])

  if (!repo) return null

  const catColor = CATEGORY_COLORS[repo.category]?.fill || '#94a3b8'
  const eraColor = ERA_COLORS[repo.era] || '#94a3b8'
  const layerColor = LAYER_COLORS[repo.layer] || '#94a3b8'

  return (
    <AnimatePresence>
      <motion.div
        initial={{ x: 420 }}
        animate={{ x: 0 }}
        exit={{ x: 420 }}
        transition={{ duration: 0.45, ease: [0.85, 0, 0.15, 1] }}
        className="fixed right-0 top-16 bottom-0 w-[420px] z-50 overflow-y-auto hidden lg:block"
        style={{
          background: 'rgba(10, 10, 18, 0.85)',
          backdropFilter: 'blur(24px) saturate(1.2)',
          WebkitBackdropFilter: 'blur(24px) saturate(1.2)',
          borderLeft: '1px solid rgba(255,255,255,0.08)',
          boxShadow: '-8px 0 32px rgba(0,0,0,0.4)',
        }}
      >
        <div className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex gap-2">
              <span
                className="px-2 py-0.5 rounded-full text-[11px] font-mono uppercase tracking-wider text-white"
                style={{ background: eraColor }}
              >
                {repo.era === 'trending'
                  ? 'Trending'
                  : repo.era === 'recent'
                  ? 'Recent'
                  : 'Landmark'}
              </span>
              <span
                className="px-2 py-0.5 rounded-full text-[11px] font-mono uppercase tracking-wider text-white"
                style={{ background: catColor }}
              >
                {repo.category}
              </span>
            </div>
            <button
              onClick={onClose}
              className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4 text-text-muted" />
            </button>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="mb-6"
          >
            <div className="flex items-center gap-3 mb-2">
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center text-[18px] font-bold text-white shrink-0"
                style={{ background: catColor }}
              >
                {repo.name.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0">
                <h2 className="font-display font-semibold text-[24px] leading-[1.2] text-text-primary truncate">
                  {repo.name}
                </h2>
                <p className="font-mono text-[11px] text-text-muted truncate">
                  {repo.id}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4 mt-3">
              <div className="flex items-center gap-1 text-text-secondary">
                <Star className="w-4 h-4 text-accent-amber" />
                <span className="text-[14px]">{formatStars(repo.stars)} stars</span>
              </div>
              <div className="flex items-center gap-1 text-text-muted">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ background: layerColor }}
                />
                <span className="text-[12px]">{repo.language}</span>
              </div>
              <a
                href={repo.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-accent-cyan text-[13px] hover:underline"
              >
                <ExternalLink className="w-3 h-3" />
                View on GitHub
              </a>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mb-6"
          >
            <h3 className="font-mono text-[11px] uppercase tracking-wider text-text-muted mb-2">
              Description
            </h3>
            <p className="text-[15px] leading-[1.6] text-text-primary">
              {repo.description}
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="mb-6 p-3 rounded-[10px]"
            style={{
              borderLeft: '3px solid var(--accent-cyan)',
              background: 'rgba(0,212,255,0.03)',
            }}
          >
            <h3 className="font-mono text-[11px] uppercase tracking-wider text-accent-cyan mb-2">
              Why It Matters
            </h3>
            <p className="text-[15px] leading-[1.6] text-text-secondary">
              {repo.why}
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mb-6"
          >
            <h3 className="font-mono text-[11px] uppercase tracking-wider text-text-muted mb-2">
              Architecture
            </h3>
            <div className="grid grid-cols-3 gap-2">
              <div className="glass-panel p-2 rounded-[6px]">
                <div className="text-[10px] font-mono text-text-muted uppercase mb-1">
                  Layer
                </div>
                <div className="flex items-center gap-1.5 text-[13px] text-text-primary">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ background: layerColor }}
                  />
                  {repo.layer}
                </div>
              </div>
              <div className="glass-panel p-2 rounded-[6px]">
                <div className="text-[10px] font-mono text-text-muted uppercase mb-1">
                  Era
                </div>
                <div className="flex items-center gap-1.5 text-[13px] text-text-primary">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ background: eraColor }}
                  />
                  {repo.era}
                </div>
              </div>
              <div className="glass-panel p-2 rounded-[6px]">
                <div className="text-[10px] font-mono text-text-muted uppercase mb-1">
                  Category
                </div>
                <div className="flex items-center gap-1.5 text-[13px] text-text-primary">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ background: catColor }}
                  />
                  {repo.category}
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            className="mb-6"
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-mono text-[11px] uppercase tracking-wider text-text-muted">
                Connections
              </h3>
              <span className="text-[11px] font-mono text-text-muted">
                {connected.length} connections
              </span>
            </div>
            <div className="flex flex-col gap-1 max-h-60 overflow-y-auto">
              {connected.map((c) => {
                const style = EDGE_STYLES[c.type] || {
                  color: '#94a3b8',
                  dash: '0',
                  width: 1,
                }
                return (
                  <button
                    key={`${c.otherId}-${c.type}`}
                    onClick={() => onOpenRepo(c.otherId)}
                    className="flex items-center gap-2 px-2 py-2 rounded-[6px] hover:bg-white/5 transition-colors text-left"
                  >
                    <span
                      className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase shrink-0 text-white"
                      style={{ background: style.color }}
                    >
                      {c.type}
                    </span>
                    <span className="text-[13px] text-text-primary truncate">
                      {c.other?.name}
                    </span>
                    <span className="ml-auto text-[10px] text-text-muted shrink-0">
                      {'●'.repeat(Math.min(3, Math.ceil(c.strength)))}
                    </span>
                  </button>
                )
              })}
            </div>
            <button
              onClick={() => onHighlight(repo.id)}
              className="mt-3 w-full py-2 rounded-[10px] text-[13px] text-accent-cyan border border-accent-cyan/30 hover:bg-accent-cyan/10 transition-colors"
            >
              Highlight on Graph
            </button>
          </motion.div>
        </div>

        <div className="sticky bottom-0 p-4 flex gap-2" style={{ background: 'rgba(10,10,18,0.9)', backdropFilter: 'blur(12px)' }}>
          <button
            onClick={handleExecute}
            disabled={execStatus === 'loading'}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-[10px] font-medium text-[14px] hover:brightness-110 transition-all ${
              execStatus === 'success'
                ? 'bg-accent-green text-text-inverse'
                : execStatus === 'error'
                ? 'bg-accent-red text-text-inverse'
                : 'bg-accent-amber text-text-inverse'
            }`}
          >
            {execStatus === 'loading' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {execStatus === 'loading'
              ? 'Running...'
              : execStatus === 'success'
              ? 'Ran Successfully'
              : execStatus === 'error'
              ? 'Run Failed'
              : 'Execute Module'}
          </button>
          <a
            href={repo.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-[10px] bg-accent-cyan text-text-inverse font-medium text-[14px] hover:brightness-110 transition-all"
          >
            <ExternalLink className="w-4 h-4" />
            Open Repository
          </a>
          <button
            onClick={() => {
              navigator.clipboard.writeText(repo.url)
              setCopied(true)
              setTimeout(() => setCopied(false), 2000)
            }}
            className="w-10 h-10 flex items-center justify-center rounded-[10px] border border-white/10 hover:bg-white/5 transition-colors"
          >
            {copied ? (
              <Check className="w-4 h-4 text-accent-green" />
            ) : (
              <Copy className="w-4 h-4 text-text-muted" />
            )}
          </button>
        </div>

        {execResult && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 border-t border-white/10"
            style={{ background: 'rgba(10,10,18,0.95)' }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Terminal className="w-4 h-4 text-accent-cyan" />
              <span className="font-mono text-[11px] uppercase tracking-wider text-text-muted">
                Execution Result
              </span>
              <span
                className={`ml-auto px-2 py-0.5 rounded-full text-[10px] font-mono uppercase ${
                  execStatus === 'success'
                    ? 'bg-accent-green/20 text-accent-green'
                    : 'bg-accent-red/20 text-accent-red'
                }`}
              >
                {execResult.status || execStatus}
              </span>
            </div>
            {execResult.entrypoint && (
              <div className="text-[12px] text-text-muted mb-1">
                Entrypoint: <span className="text-text-secondary">{execResult.entrypoint}</span>
              </div>
            )}
            {execResult.command && (
              <div className="text-[12px] text-text-muted mb-2">
                Command: <span className="text-text-secondary font-mono">{execResult.command}</span>
              </div>
            )}
            {execResult.stdout && (
              <div className="mb-2">
                <div className="text-[10px] font-mono uppercase text-text-muted mb-1">stdout</div>
                <pre className="text-[11px] text-text-primary bg-black/40 rounded-[6px] p-2 max-h-32 overflow-y-auto font-mono whitespace-pre-wrap">
                  {execResult.stdout}
                </pre>
              </div>
            )}
            {execResult.stderr && (
              <div>
                <div className="text-[10px] font-mono uppercase text-text-muted mb-1">stderr</div>
                <pre className="text-[11px] text-accent-red bg-black/40 rounded-[6px] p-2 max-h-32 overflow-y-auto font-mono whitespace-pre-wrap">
                  {execResult.stderr}
                </pre>
              </div>
            )}
          </motion.div>
        )}
      </motion.div>

      {/* Mobile drawer */}
      <motion.div
        initial={{ y: '100%' }}
        animate={{ y: 0 }}
        exit={{ y: '100%' }}
        transition={{ duration: 0.35, ease: [0.85, 0, 0.15, 1] }}
        className="fixed inset-x-0 bottom-0 z-50 rounded-t-[24px] overflow-y-auto lg:hidden"
        style={{
          maxHeight: '80vh',
          background: 'rgba(10, 10, 18, 0.92)',
          backdropFilter: 'blur(24px) saturate(1.2)',
          WebkitBackdropFilter: 'blur(24px) saturate(1.2)',
          borderTop: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        <div className="w-12 h-1 rounded-full bg-white/20 mx-auto mt-3 mb-2" />
        <div className="p-6 pb-24">
          <div className="flex items-start justify-between mb-4">
            <div className="flex gap-2">
              <span
                className="px-2 py-0.5 rounded-full text-[11px] font-mono uppercase tracking-wider text-white"
                style={{ background: eraColor }}
              >
                {repo.era === 'trending'
                  ? 'Trending'
                  : repo.era === 'recent'
                  ? 'Recent'
                  : 'Landmark'}
              </span>
              <span
                className="px-2 py-0.5 rounded-full text-[11px] font-mono uppercase tracking-wider text-white"
                style={{ background: catColor }}
              >
                {repo.category}
              </span>
            </div>
            <button
              onClick={onClose}
              className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4 text-text-muted" />
            </button>
          </div>

          <div className="mb-6">
            <div className="flex items-center gap-3 mb-2">
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center text-[18px] font-bold text-white shrink-0"
                style={{ background: catColor }}
              >
                {repo.name.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0">
                <h2 className="font-display font-semibold text-[22px] leading-[1.2] text-text-primary truncate">
                  {repo.name}
                </h2>
                <p className="font-mono text-[11px] text-text-muted truncate">
                  {repo.id}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4 mt-3 flex-wrap">
              <div className="flex items-center gap-1 text-text-secondary">
                <Star className="w-4 h-4 text-accent-amber" />
                <span className="text-[14px]">{formatStars(repo.stars)} stars</span>
              </div>
              <div className="flex items-center gap-1 text-text-muted">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ background: layerColor }}
                />
                <span className="text-[12px]">{repo.language}</span>
              </div>
              <a
                href={repo.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-accent-cyan text-[13px] hover:underline"
              >
                <ExternalLink className="w-3 h-3" />
                GitHub
              </a>
            </div>
          </div>

          <div className="mb-6">
            <h3 className="font-mono text-[11px] uppercase tracking-wider text-text-muted mb-2">
              Description
            </h3>
            <p className="text-[15px] leading-[1.6] text-text-primary">
              {repo.description}
            </p>
          </div>

          <div
            className="mb-6 p-3 rounded-[10px]"
            style={{
              borderLeft: '3px solid var(--accent-cyan)',
              background: 'rgba(0,212,255,0.03)',
            }}
          >
            <h3 className="font-mono text-[11px] uppercase tracking-wider text-accent-cyan mb-2">
              Why It Matters
            </h3>
            <p className="text-[15px] leading-[1.6] text-text-secondary">
              {repo.why}
            </p>
          </div>

          <div className="mb-6">
            <h3 className="font-mono text-[11px] uppercase tracking-wider text-text-muted mb-2">
              Architecture
            </h3>
            <div className="grid grid-cols-3 gap-2">
              <div className="glass-panel p-2 rounded-[6px]">
                <div className="text-[10px] font-mono text-text-muted uppercase mb-1">Layer</div>
                <div className="flex items-center gap-1.5 text-[13px] text-text-primary">
                  <span className="w-2 h-2 rounded-full" style={{ background: layerColor }} />
                  {repo.layer}
                </div>
              </div>
              <div className="glass-panel p-2 rounded-[6px]">
                <div className="text-[10px] font-mono text-text-muted uppercase mb-1">Era</div>
                <div className="flex items-center gap-1.5 text-[13px] text-text-primary">
                  <span className="w-2 h-2 rounded-full" style={{ background: eraColor }} />
                  {repo.era}
                </div>
              </div>
              <div className="glass-panel p-2 rounded-[6px]">
                <div className="text-[10px] font-mono text-text-muted uppercase mb-1">Category</div>
                <div className="flex items-center gap-1.5 text-[13px] text-text-primary">
                  <span className="w-2 h-2 rounded-full" style={{ background: catColor }} />
                  {repo.category}
                </div>
              </div>
            </div>
          </div>

          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-mono text-[11px] uppercase tracking-wider text-text-muted">
                Connections
              </h3>
              <span className="text-[11px] font-mono text-text-muted">
                {connected.length} connections
              </span>
            </div>
            <div className="flex flex-col gap-1 max-h-60 overflow-y-auto">
              {connected.map((c) => {
                const style = EDGE_STYLES[c.type] || { color: '#94a3b8', dash: '0', width: 1 }
                return (
                  <button
                    key={`${c.otherId}-${c.type}`}
                    onClick={() => onOpenRepo(c.otherId)}
                    className="flex items-center gap-2 px-2 py-2 rounded-[6px] hover:bg-white/5 transition-colors text-left"
                  >
                    <span
                      className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase shrink-0 text-white"
                      style={{ background: style.color }}
                    >
                      {c.type}
                    </span>
                    <span className="text-[13px] text-text-primary truncate">
                      {c.other?.name}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="sticky bottom-0 p-4 flex gap-2" style={{ background: 'rgba(10,10,18,0.9)', backdropFilter: 'blur(12px)' }}>
            <button
              onClick={handleExecute}
              disabled={execStatus === 'loading'}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-[10px] font-medium text-[14px] hover:brightness-110 transition-all ${
                execStatus === 'success'
                  ? 'bg-accent-green text-text-inverse'
                  : execStatus === 'error'
                  ? 'bg-accent-red text-text-inverse'
                  : 'bg-accent-amber text-text-inverse'
              }`}
            >
              {execStatus === 'loading' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {execStatus === 'loading'
                ? 'Running...'
                : execStatus === 'success'
                ? 'Ran Successfully'
                : execStatus === 'error'
                ? 'Run Failed'
                : 'Execute Module'}
            </button>
            <a
              href={repo.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-[10px] bg-accent-cyan text-text-inverse font-medium text-[14px] hover:brightness-110 transition-all"
            >
              <ExternalLink className="w-4 h-4" />
              GitHub
            </a>
          </div>

          {execResult && (
            <div className="p-4 border-t border-white/10" style={{ background: 'rgba(10,10,18,0.95)' }}>
              <div className="flex items-center gap-2 mb-2">
                <Terminal className="w-4 h-4 text-accent-cyan" />
                <span className="font-mono text-[11px] uppercase tracking-wider text-text-muted">
                  Execution Result
                </span>
                <span
                  className={`ml-auto px-2 py-0.5 rounded-full text-[10px] font-mono uppercase ${
                    execStatus === 'success'
                      ? 'bg-accent-green/20 text-accent-green'
                      : 'bg-accent-red/20 text-accent-red'
                  }`}
                >
                  {execResult.status || execStatus}
                </span>
              </div>
              {execResult.entrypoint && (
                <div className="text-[12px] text-text-muted mb-1">
                  Entrypoint: <span className="text-text-secondary">{execResult.entrypoint}</span>
                </div>
              )}
              {execResult.command && (
                <div className="text-[12px] text-text-muted mb-2">
                  Command: <span className="text-text-secondary font-mono">{execResult.command}</span>
                </div>
              )}
              {execResult.stdout && (
                <div className="mb-2">
                  <div className="text-[10px] font-mono uppercase text-text-muted mb-1">stdout</div>
                  <pre className="text-[11px] text-text-primary bg-black/40 rounded-[6px] p-2 max-h-32 overflow-y-auto font-mono whitespace-pre-wrap">
                    {execResult.stdout}
                  </pre>
                </div>
              )}
              {execResult.stderr && (
                <div>
                  <div className="text-[10px] font-mono uppercase text-text-muted mb-1">stderr</div>
                  <pre className="text-[11px] text-accent-red bg-black/40 rounded-[6px] p-2 max-h-32 overflow-y-auto font-mono whitespace-pre-wrap">
                    {execResult.stderr}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  )
}
