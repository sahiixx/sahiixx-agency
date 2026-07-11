import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Cpu, HardDrive, MemoryStick, Battery, Clock, Server } from 'lucide-react';

interface SystemInfo {
  hostname: string;
  username: string;
  os_version: string;
  cpu_count: number;
  memory_total_gb: number;
  memory_available_gb: number;
  disk_usage: Record<string, { used: number; free: number }>;
  battery: { charge_percent: number; charging: boolean } | null;
  uptime_seconds: number;
}

interface SystemPanelProps {
  data: SystemInfo | null;
  loading: boolean;
}

export function SystemPanel({ data, loading }: SystemPanelProps) {
  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="space-y-3">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-12 bg-muted animate-pulse rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-muted-foreground">
          No system data available
        </CardContent>
      </Card>
    );
  }

  const memoryUsed = data.memory_total_gb - data.memory_available_gb;
  const memoryPercent = data.memory_total_gb > 0 ? (memoryUsed / data.memory_total_gb) * 100 : 0;
  const uptimeHours = Math.floor(data.uptime_seconds / 3600);
  const uptimeMinutes = Math.floor((data.uptime_seconds % 3600) / 60);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Server className="h-4 w-4" />
          System
          <Badge variant="outline" className="ml-auto text-xs">{data.hostname}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* CPU */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5 text-cyan-500" />
              <span>CPU</span>
            </div>
            <span className="text-muted-foreground">{data.cpu_count} cores</span>
          </div>
        </div>

        {/* Memory */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5">
              <MemoryStick className="h-3.5 w-3.5 text-purple-500" />
              <span>Memory</span>
            </div>
            <span className="text-muted-foreground">
              {memoryUsed.toFixed(1)} / {data.memory_total_gb.toFixed(1)} GB
            </span>
          </div>
          <Progress value={memoryPercent} className="h-1.5" />
        </div>

        {/* Disk */}
        {Object.entries(data.disk_usage).map(([drive, usage]) => {
          const total = usage.used + usage.free;
          const percent = total > 0 ? (usage.used / total) * 100 : 0;
          return (
            <div key={drive} className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <HardDrive className="h-3.5 w-3.5 text-amber-500" />
                  <span>Drive {drive}</span>
                </div>
                <span className="text-muted-foreground">
                  {usage.used.toFixed(1)} / {total.toFixed(1)} GB
                </span>
              </div>
              <Progress value={percent} className="h-1.5" />
            </div>
          );
        })}

        {/* Battery */}
        {data.battery && (
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5">
              <Battery className={`h-3.5 w-3.5 ${data.battery.charging ? 'text-green-500' : 'text-yellow-500'}`} />
              <span>Battery</span>
            </div>
            <Badge variant={data.battery.charge_percent > 20 ? 'default' : 'destructive'} className="text-xs">
              {data.battery.charge_percent}% {data.battery.charging ? '⚡' : ''}
            </Badge>
          </div>
        )}

        {/* Uptime */}
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-green-500" />
            <span>Uptime</span>
          </div>
          <span className="text-muted-foreground">{uptimeHours}h {uptimeMinutes}m</span>
        </div>

        {/* User */}
        <div className="text-xs text-muted-foreground">
          User: {data.username} | OS: {data.os_version?.substring(0, 30)}
        </div>
      </CardContent>
    </Card>
  );
}
