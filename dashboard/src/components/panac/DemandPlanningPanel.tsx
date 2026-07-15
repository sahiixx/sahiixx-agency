import { useEffect, useState } from 'react'
import { Boxes, Loader2 } from 'lucide-react'

interface Forecast { sku: string; daily_demand: number; projected_30_day_demand: number; available_inventory: number; coverage_days: number | null; risk: 'critical' | 'high' | 'medium' | 'low' }
interface PlanningData { horizon_days: number; forecasts: Forecast[]; disclaimer: string }
interface DemandPlanningPanelProps { revision: number }

const riskClass = { critical: 'text-red-500 bg-red-500/10', high: 'text-orange-500 bg-orange-500/10', medium: 'text-amber-600 bg-amber-500/10', low: 'text-accent-green bg-green-500/10' }

export function DemandPlanningPanel({ revision }: DemandPlanningPanelProps) {
  const [data, setData] = useState<PlanningData | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/panac/demand-planning', { signal: controller.signal }).then((response) => response.ok ? response.json() as Promise<PlanningData> : null).then(setData).catch(() => undefined)
    return () => controller.abort()
  }, [revision])

  if (!data) return <section className="mt-9 flex justify-center rounded-2xl border border-black/5 bg-bg-surface p-8 dark:border-white/10"><Loader2 className="h-5 w-5 animate-spin text-accent-cyan" /></section>
  return <section className="mt-9 rounded-2xl border border-black/5 bg-bg-surface p-6 shadow-card dark:border-white/10"><div className="flex items-center gap-2"><Boxes className="h-5 w-5 text-accent-cyan" /><div><h2 className="font-display text-xl font-semibold">Demand & inventory planning</h2><p className="mt-1 text-sm text-text-secondary">{data.horizon_days}-day projection based on imported usage.</p></div></div>{data.forecasts.length > 0 ? <div className="mt-6 overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead className="border-b border-black/5 text-text-muted dark:border-white/10"><tr><th className="pb-3 font-medium">SKU / metric</th><th className="pb-3 font-medium">Daily demand</th><th className="pb-3 font-medium">30-day demand</th><th className="pb-3 font-medium">Available</th><th className="pb-3 font-medium">Coverage</th><th className="pb-3 font-medium">Risk</th></tr></thead><tbody>{data.forecasts.map((forecast) => <tr key={forecast.sku} className="border-b border-black/5 last:border-0 dark:border-white/10"><td className="py-3 font-mono text-xs">{forecast.sku}</td><td className="py-3">{forecast.daily_demand.toLocaleString()}</td><td className="py-3">{forecast.projected_30_day_demand.toLocaleString()}</td><td className="py-3">{forecast.available_inventory.toLocaleString()}</td><td className="py-3">{forecast.coverage_days === null ? 'No usage baseline' : `${forecast.coverage_days} days`}</td><td className="py-3"><span className={`rounded-full px-2 py-1 text-xs font-medium capitalize ${riskClass[forecast.risk]}`}>{forecast.risk}</span></td></tr>)}</tbody></table></div> : <p className="mt-6 rounded-xl bg-bg-elevated p-4 text-sm text-text-secondary">Import usage and inventory CSVs to generate demand coverage forecasts.</p>}<p className="mt-5 text-xs text-text-muted">{data.disclaimer}</p></section>
}
