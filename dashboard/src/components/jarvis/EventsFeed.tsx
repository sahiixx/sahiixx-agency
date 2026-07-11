import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Bell, AlertTriangle, AlertCircle, Info, Clock } from 'lucide-react';

interface MonitorEvent {
  event_type: string;
  severity: 'info' | 'warning' | 'critical';
  source: string;
  title: string;
  description: string;
  suggested_action?: string;
  timestamp: string;
}

const severityConfig = {
  info: { icon: Info, color: 'text-blue-500', bg: 'bg-blue-500/10', badge: 'default' as const },
  warning: { icon: AlertTriangle, color: 'text-yellow-500', bg: 'bg-yellow-500/10', badge: 'secondary' as const },
  critical: { icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-500/10', badge: 'destructive' as const },
};

function timeAgo(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const seconds = Math.floor((now.getTime() - then.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function EventsFeed({ limit = 20 }: { limit?: number }) {
  const [events, setEvents] = useState<MonitorEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const resp = await fetch(`/api/jarvis/events?limit=${limit}`);
        if (resp.ok) {
          setEvents(await resp.json());
        }
      } catch {
        // Silently fail — dashboard may be offline
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
    const interval = setInterval(fetchEvents, 15000);
    return () => clearInterval(interval);
  }, [limit]);

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Events Feed
          </CardTitle>
          <Badge variant="outline" className="text-xs">
            {events.length} events
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 bg-muted animate-pulse rounded" />
            ))}
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No events yet</p>
            <p className="text-xs">Events will appear here when Jarvis detects changes</p>
          </div>
        ) : (
          <ScrollArea className="h-[400px]">
            <div className="space-y-2">
              {events.map((event, i) => {
                const config = severityConfig[event.severity] || severityConfig.info;
                const Icon = config.icon;

                return (
                  <div
                    key={`${event.timestamp}-${i}`}
                    className={`p-3 rounded-lg border ${config.bg} transition-colors`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2 flex-1 min-w-0">
                        <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${config.color}`} />
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium text-sm">{event.title}</span>
                            <Badge variant={config.badge} className="text-xs h-4">
                              {event.severity}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                            {event.description}
                          </p>
                          {event.suggested_action && (
                            <p className="text-xs text-blue-500 mt-1">
                              → {event.suggested_action}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
                        <Clock className="h-3 w-3" />
                        {timeAgo(event.timestamp)}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
