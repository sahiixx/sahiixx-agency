import { useEffect, useState } from 'react'
import { Activity, AlertCircle, CheckCircle, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from 'sonner'

interface HealthCheck {
  name: string
  status: string
  latency_ms: number
  message: string
  checked_at: string
}

interface Stats {
  config: Record<string, unknown>
  registry: {
    total_modules: number
    active: number
    total_stars: number
    by_category: Record<string, number>
    by_language: Record<string, number>
  }
  memory_events: number
  metrics: {
    counters: Record<string, number>
    gauges: Record<string, number>
    total_points: number
  }
  health: string
  workflows: { definitions: number; instances: number }
  notifications: number
}

export default function MetricsPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [health, setHealth] = useState<HealthCheck[]>([])
  const [metricsText, setMetricsText] = useState('')

  const fetchData = async () => {
    try {
      const [statsRes, healthRes, metricsRes] = await Promise.all([
        fetch('/api/stats'),
        fetch('/api/health'),
        fetch('/api/metrics'),
      ])
      if (!statsRes.ok || !healthRes.ok || !metricsRes.ok) throw new Error('Failed to load metrics')
      setStats(await statsRes.json())
      const healthData = await healthRes.json()
      setHealth(healthData.checks || [])
      setMetricsText(await metricsRes.text())
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load metrics')
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-[100dvh] px-4 py-6 md:px-8 md:py-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="h-6 w-6 text-accent-cyan" />
            <h1 className="font-display text-2xl font-bold text-text-primary">Observability</h1>
          </div>
          {stats && (
            <div className="flex items-center gap-2 text-sm">
              {stats.health === 'healthy' ? (
                <>
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span className="text-green-500">Healthy</span>
                </>
              ) : (
                <>
                  <AlertCircle className="h-4 w-4 text-yellow-500" />
                  <span className="text-yellow-500 capitalize">{stats.health}</span>
                </>
              )}
            </div>
          )}
        </div>

        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-text-secondary">Modules</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.registry.total_modules}</div>
                <div className="text-xs text-text-secondary">{stats.registry.active} active</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-text-secondary">Memory Events</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.memory_events}</div>
                <div className="text-xs text-text-secondary">Logged events</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-text-secondary">Workflows</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.workflows.definitions}</div>
                <div className="text-xs text-text-secondary">{stats.workflows.instances} instances</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-text-secondary">Metric Points</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.metrics.total_points}</div>
                <div className="text-xs text-text-secondary">In memory</div>
              </CardContent>
            </Card>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingUp className="h-4 w-4" /> Counters
              </CardTitle>
            </CardHeader>
            <CardContent>
              {stats && Object.keys(stats.metrics.counters).length > 0 ? (
                <div className="space-y-2">
                  {Object.entries(stats.metrics.counters).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between text-sm">
                      <span className="font-mono text-xs">{key}</span>
                      <span className="font-medium">{value}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-text-secondary">No counters recorded yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Activity className="h-4 w-4" /> Health Checks
              </CardTitle>
            </CardHeader>
            <CardContent>
              {health.length > 0 ? (
                <div className="space-y-2">
                  {health.map((check) => (
                    <div key={check.name} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        {check.status === 'healthy' ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-yellow-500" />
                        )}
                        <span>{check.name}</span>
                      </div>
                      <span className="text-xs text-text-secondary">{check.latency_ms}ms</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-text-secondary">No health checks registered.</p>
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Prometheus Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs font-mono bg-muted p-4 rounded-lg overflow-auto max-h-96">
              {metricsText || 'No metrics exported yet.'}
            </pre>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
