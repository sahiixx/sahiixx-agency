import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

interface HealthCheck {
  name: string;
  status: 'healthy' | 'unhealthy' | 'offline';
  latency?: number;
  message?: string;
  url?: string;
}

export function HealthStatus() {
  const [checks, setChecks] = useState<HealthCheck[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const results: HealthCheck[] = [];

        // Check API server
        try {
          const start = Date.now();
          const resp = await fetch('/api/health', { signal: AbortSignal.timeout(5000) });
          results.push({
            name: 'API Server',
            status: resp.ok ? 'healthy' : 'unhealthy',
            latency: Date.now() - start,
            url: 'http://localhost:8082',
          });
        } catch {
          results.push({ name: 'API Server', status: 'offline', url: 'http://localhost:8082' });
        }

        // Check MCP server
        try {
          const start = Date.now();
          const resp = await fetch('http://localhost:8081/health', { signal: AbortSignal.timeout(5000) });
          results.push({
            name: 'MCP Server',
            status: resp.ok ? 'healthy' : 'unhealthy',
            latency: Date.now() - start,
            url: 'http://localhost:8081',
          });
        } catch {
          results.push({ name: 'MCP Server', status: 'offline', url: 'http://localhost:8081' });
        }

        // Check Dashboard (self)
        results.push({
          name: 'Dashboard',
          status: 'healthy',
          latency: 0,
          url: window.location.origin,
        });

        // Check Jarvis
        try {
          const start = Date.now();
          const resp = await fetch('/api/jarvis/health', { signal: AbortSignal.timeout(5000) });
          results.push({
            name: 'Jarvis',
            status: resp.ok ? 'healthy' : 'unhealthy',
            latency: Date.now() - start,
          });
        } catch {
          results.push({ name: 'Jarvis', status: 'offline' });
        }

        setChecks(results);
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const healthyCount = checks.filter(c => c.status === 'healthy').length;
  const totalCount = checks.length;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Activity className="h-4 w-4" />
            System Health
          </CardTitle>
          <Badge variant={healthyCount === totalCount ? 'default' : 'destructive'}>
            {healthyCount}/{totalCount}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-8 bg-muted animate-pulse rounded" />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {checks.map(check => (
              <div
                key={check.name}
                className="flex items-center justify-between py-1.5 px-2 rounded-lg bg-muted/50"
              >
                <div className="flex items-center gap-2">
                  {check.status === 'healthy' ? (
                    <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                  ) : check.status === 'unhealthy' ? (
                    <AlertTriangle className="h-3.5 w-3.5 text-yellow-500" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-red-500" />
                  )}
                  <span className="text-sm">{check.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  {check.latency !== undefined && check.latency > 0 && (
                    <span className="text-xs text-muted-foreground">{check.latency}ms</span>
                  )}
                  <Badge
                    variant={check.status === 'healthy' ? 'default' : 'destructive'}
                    className="text-xs h-5"
                  >
                    {check.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
