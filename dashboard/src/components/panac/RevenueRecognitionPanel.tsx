import { useEffect, useState } from 'react'
import { BadgeDollarSign, Loader2, ShieldAlert } from 'lucide-react'

interface Schedule { contract_id: string; customer: string; contract_value: number; recognized_value: number; deferred_value: number; status: string; review_reason: string }
interface RecognitionOverview { as_of: string; contract_value: number; recognized_value: number; deferred_value: number; schedules: Schedule[]; disclaimer: string }
interface RevenueRecognitionPanelProps { revision: number }

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

export function RevenueRecognitionPanel({ revision }: RevenueRecognitionPanelProps) {
  const [data, setData] = useState<RecognitionOverview | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/panac/revenue-recognition', { signal: controller.signal })
      .then((response) => response.ok ? response.json() as Promise<RecognitionOverview> : null)
      .then(setData)
      .catch(() => undefined)
    return () => controller.abort()
  }, [revision])

  if (!data) return <section className="mt-9 flex justify-center rounded-2xl border border-black/5 bg-bg-surface p-8 dark:border-white/10"><Loader2 className="h-5 w-5 animate-spin text-accent-cyan" /></section>

  return <section className="mt-9 rounded-2xl border border-black/5 bg-bg-surface p-6 shadow-card dark:border-white/10"><div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between"><div><div className="flex items-center gap-2"><BadgeDollarSign className="h-5 w-5 text-accent-cyan" /><h2 className="font-display text-xl font-semibold">Revenue schedule review</h2></div><p className="mt-1 text-sm text-text-secondary">As of {data.as_of} · imported contract schedules</p></div><div className="flex items-center gap-2 rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300"><ShieldAlert className="h-4 w-4" />Review required before posting</div></div><div className="mt-6 grid gap-3 sm:grid-cols-3"><div><p className="text-sm text-text-secondary">Contract value</p><p className="mt-1 text-2xl font-semibold">{money.format(data.contract_value)}</p></div><div><p className="text-sm text-text-secondary">Recognized estimate</p><p className="mt-1 text-2xl font-semibold text-accent-green">{money.format(data.recognized_value)}</p></div><div><p className="text-sm text-text-secondary">Deferred estimate</p><p className="mt-1 text-2xl font-semibold text-accent-cyan">{money.format(data.deferred_value)}</p></div></div>{(data.schedules ?? []).length > 0 ? <div className="mt-6 overflow-x-auto"><table className="w-full min-w-[600px] text-left text-sm"><thead className="border-b border-black/5 text-text-muted dark:border-white/10"><tr><th className="pb-3 font-medium">Contract</th><th className="pb-3 font-medium">Customer</th><th className="pb-3 font-medium">Recognized</th><th className="pb-3 font-medium">Deferred</th><th className="pb-3 font-medium">Review</th></tr></thead><tbody>{(data.schedules ?? []).map((schedule) => <tr key={schedule.contract_id} className="border-b border-black/5 last:border-0 dark:border-white/10"><td className="py-3 font-mono text-xs">{schedule.contract_id}</td><td className="py-3">{schedule.customer}</td><td className="py-3">{money.format(schedule.recognized_value)}</td><td className="py-3">{money.format(schedule.deferred_value)}</td><td className="py-3 text-xs text-text-secondary">{schedule.review_reason}</td></tr>)}</tbody></table></div> : <p className="mt-6 rounded-xl bg-bg-elevated p-4 text-sm text-text-secondary">Import contracts to generate a preliminary schedule.</p>}<p className="mt-5 text-xs text-text-muted">{data.disclaimer}</p></section>
}
