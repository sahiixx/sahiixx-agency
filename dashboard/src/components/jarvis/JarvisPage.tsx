import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MonitoringDashboard } from './MonitoringDashboard';
import { HealthStatus } from './HealthStatus';
import { EventsFeed } from './EventsFeed';
import { JarvisChat } from './JarvisChat';
import { Activity, MessageSquare, BarChart3 } from 'lucide-react';

export function JarvisPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Activity className="h-6 w-6 text-cyan-500" />
          Jarvis 100x
        </h1>
        <p className="text-muted-foreground mt-1">
          Proactive monitoring, system health, and AI assistant
        </p>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="monitoring" className="space-y-4">
        <TabsList>
          <TabsTrigger value="monitoring" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Monitoring
          </TabsTrigger>
          <TabsTrigger value="chat" className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            Chat
          </TabsTrigger>
          <TabsTrigger value="events" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Events
          </TabsTrigger>
        </TabsList>

        {/* Monitoring Tab */}
        <TabsContent value="monitoring" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <MonitoringDashboard />
            </div>
            <div>
              <HealthStatus />
            </div>
          </div>
        </TabsContent>

        {/* Chat Tab */}
        <TabsContent value="chat">
          <div className="h-[calc(100vh-280px)]">
            <JarvisChat />
          </div>
        </TabsContent>

        {/* Events Tab */}
        <TabsContent value="events">
          <EventsFeed limit={50} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
