import { useEffect, useState } from 'react'
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Check, CircleAlert, Loader2, ShieldCheck, Sparkles } from 'lucide-react'
import { ImportPanel } from '@/components/panac/ImportPanel'
import { RevenueRecognitionPanel } from '@/components/panac/RevenueRecognitionPanel'
import { DemandPlanningPanel } from '@/components/panac/DemandPlanningPanel'

type Trend = 'up' | 'down' | 'neutral'

interface Metric { label: string; value: string; change: string; trend: Trend; detail: string }
interface Signal { id: string; domain: string; title: string; detail: string; severity: 'critical' | 'high' | 'medium' | 'low'; impact: string }
interface Recommendation { id: string; title: string; owner: string; domain: string; expected_impact: string; rationale: string; status: 'review' | 'approved'; requires_approval: boolean }
interface Overview { workspace: string; period: string; metrics: Metric[]; signals: Signal[]; recommendations: Recommendation[]; agents: string[]; demo_mode: boolean }

const severityClasses = {
  critical: 'bg-red-500/10 text-red-500 border-red-500/20',
  high: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
  medium: 'bg-amber-500/10 text-amber-600 border-amber-500/20',
  low: 'bg-cyan-500/10 text-cyan-600 border-cyan-500/20',
} as const

export default function Panac() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [approving, setApproving] = useState<string | null>(null)
  const [dataRevision, setDataRevision] = useState(0)

  async function refreshOverview(signal?: AbortSignal) {
    const response = await fetch('/api/panac/overview', { signal })
    if (!response.ok) throw new Error('Panac workspace is unavailable')
    setOverview(await response.json() as Overview)
  }

  useEffect(() => {
    const controller = new AbortController()
    refreshOverview(controller.signal)
      .catch((fetchError: unknown) => {
        if (fetchError instanceof DOMException && fetchError.name === 'AbortError') return
        setError(fetchError instanceof Error ? fetchError.message : 'Unable to load Panac')
      })
    return () => controller.abort()
  }, [])

  async function approve(recommendationId: string) {
    setApproving(recommendationId)
    try {
      const response = await fetch(`/api/panac/recommendations/${recommendationId}/approve`, { method: 'POST' })
      if (!response.ok) throw new Error('Could not record approval')
      const approved = await response.json() as Recommendation
      setOverview((current) => current && {
        ...current,
        recommendations: current.recommendations.map((item) => item.id === approved.id ? approved : item),
      })
    } catch (approvalError) {
      setError(approvalError instanceof Error ? approvalError.message : 'Could not record approval')
    } finally {
      setApproving(null)
    }
  }

  if (error) return <main className="mx-auto max-w-7xl px-6 py-12 text-red-500">{error}</main>
  if (!overview) return <main className="flex min-h-[60vh] items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-accent-cyan" /></main>

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 md:px-6 md:py-12">
      <header className="mb-9 flex flex-col gap-5 border-b border-black/5 pb-8 dark:border-white/10 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="mb-3 flex items-center gap-2 text-sm font-medium text-accent-cyan"><Sparkles className="h-4 w-4" /> Enterprise intelligence</div>
          <h1 className="font-display text-4xl font-semibold tracking-tight text-text-primary">Panac</h1>
          <p className="mt-2 text-text-secondary">{overview.workspace} · {overview.period}</p>
        </div>
        {overview.demo_mode && <div className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-700 dark:text-amber-300">Demo workspace · no business systems connected</div>}
      </header>

      <section aria-label="Business health" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {overview.metrics.map((metric) => {
          const positive = metric.trend !== 'down'
          return <article key={metric.label} className="rounded-2xl border border-black/5 bg-bg-surface p-5 shadow-card dark:border-white/10">
            <p className="text-sm text-text-secondary">{metric.label}</p>
            <p className="mt-3 text-3xl font-semibold tracking-tight text-text-primary">{metric.value}</p>
            <p className={`mt-3 flex items-center gap-1 text-sm font-medium ${positive ? 'text-accent-green' : 'text-accent-red'}`}>
              {positive ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}{metric.change}<span className="ml-1 font-normal text-text-muted">{metric.detail}</span>
            </p>
          </article>
        })}
      </section>

      <section className="mt-9 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border border-black/5 bg-bg-surface p-6 shadow-card dark:border-white/10">
          <div className="mb-5 flex items-center justify-between"><div><h2 className="font-display text-xl font-semibold">Operating signals</h2><p className="mt-1 text-sm text-text-secondary">Cross-functional exceptions that need attention.</p></div><CircleAlert className="h-5 w-5 text-accent-amber" /></div>
          <div className="space-y-3">
            {overview.signals.map((signal) => <article key={signal.id} className="rounded-xl border border-black/5 p-4 dark:border-white/10">
              <div className="flex gap-3"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-accent-amber" /><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-medium text-text-primary">{signal.title}</h3><span className={`rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${severityClasses[signal.severity]}`}>{signal.severity}</span></div><p className="mt-1 text-sm text-text-secondary">{signal.detail}</p><p className="mt-2 font-mono text-xs text-text-muted">{signal.domain} · {signal.impact}</p></div></div>
            </article>)}
          </div>
        </div>
        <aside className="rounded-2xl border border-black/5 bg-bg-surface p-6 shadow-card dark:border-white/10">
          <div className="flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-accent-green" /><h2 className="font-display text-xl font-semibold">Agent fabric</h2></div>
          <p className="mt-2 text-sm text-text-secondary">Specialist agents share one governed operating context.</p>
          <ul className="mt-5 space-y-3">{overview.agents.map((agent) => <li key={agent} className="flex items-center gap-3 rounded-xl bg-bg-elevated px-3 py-3 text-sm text-text-primary"><span className="h-2 w-2 rounded-full bg-accent-green" />{agent}<span className="ml-auto font-mono text-[10px] uppercase text-text-muted">ready</span></li>)}</ul>
        </aside>
      </section>

      <section className="mt-9"><div className="mb-5"><h2 className="font-display text-2xl font-semibold">Recommended actions</h2><p className="mt-1 text-sm text-text-secondary">Panac proposes actions; an operator approves before any connector can execute.</p></div><div className="grid gap-4 lg:grid-cols-3">{overview.recommendations.map((recommendation) => <article key={recommendation.id} className="flex flex-col rounded-2xl border border-black/5 bg-bg-surface p-5 shadow-card dark:border-white/10"><p className="text-xs font-semibold uppercase tracking-wider text-accent-cyan">{recommendation.domain}</p><h3 className="mt-3 text-lg font-semibold text-text-primary">{recommendation.title}</h3><p className="mt-3 flex-1 text-sm leading-6 text-text-secondary">{recommendation.rationale}</p><div className="mt-5 border-t border-black/5 pt-4 dark:border-white/10"><p className="text-sm font-medium text-accent-green">{recommendation.expected_impact}</p><p className="mt-1 text-xs text-text-muted">Owner: {recommendation.owner}</p></div>{recommendation.status === 'approved' ? <div className="mt-4 flex items-center justify-center gap-2 rounded-lg bg-green-500/10 px-3 py-2 text-sm font-medium text-accent-green"><Check className="h-4 w-4" /> Approval recorded</div> : <button type="button" onClick={() => approve(recommendation.id)} disabled={approving !== null} className="mt-4 rounded-lg bg-accent-cyan px-3 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50">{approving === recommendation.id ? 'Recording…' : 'Approve for execution'}</button>}</article>)}</div></section>
      <ImportPanel onImported={() => { void refreshOverview(); setDataRevision((revision) => revision + 1) }} />
      <RevenueRecognitionPanel revision={dataRevision} />
      <DemandPlanningPanel revision={dataRevision} />
    </main>
  )
}
