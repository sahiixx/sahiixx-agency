import { useState, useEffect, useCallback } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { CommandPalette } from './CommandPalette';
import { SystemPanel } from './SystemPanel';
import { ProcessManager } from './ProcessManager';
import { AppLauncher } from './AppLauncher';
import { ClipboardManager } from './ClipboardManager';
import { CommandHistory } from './CommandHistory';
import { ResultsPanel } from './ResultsPanel';
import {
  Monitor, Terminal, AppWindow, Activity
} from 'lucide-react';

interface CommandResult {
  id: string;
  command: string;
  result: string;
  success: boolean;
  timestamp: Date;
  duration: number;
}

interface Process {
  pid: number;
  name: string;
  cpu_percent: number;
  memory_mb: number;
  status: string;
}

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

interface Window {
  name: string;
  title: string;
}

export function JarvisGUI() {
  // State
  const [commandHistory, setCommandHistory] = useState<CommandResult[]>([]);
  const [lastResult, setLastResult] = useState<CommandResult | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [processes, setProcesses] = useState<Process[]>([]);
  const [openWindows, setOpenWindows] = useState<Window[]>([]);
  const [clipboardContent, setClipboardContent] = useState('');
  const [clipboardHistory, setClipboardHistory] = useState<{ id: string; content: string; timestamp: Date }[]>([]);
  const [loading, setLoading] = useState({ system: false, processes: false });
  const [connected, setConnected] = useState(false);

  // Execute command via API
  const executeCommand = useCallback(async (command: string) => {
    const startTime = Date.now();
    const id = Date.now().toString();

    try {
      const resp = await fetch('/api/jarvis/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: command }),
      });

      if (resp.ok) {
        const data = await resp.json();
        const result: CommandResult = {
          id,
          command,
          result: data.content,
          success: true,
          timestamp: new Date(),
          duration: Date.now() - startTime,
        };
        setCommandHistory(prev => [result, ...prev].slice(0, 50));
        setLastResult(result);
      } else {
        const result: CommandResult = {
          id,
          command,
          result: `Error: HTTP ${resp.status}`,
          success: false,
          timestamp: new Date(),
          duration: Date.now() - startTime,
        };
        setCommandHistory(prev => [result, ...prev].slice(0, 50));
        setLastResult(result);
      }
    } catch (e) {
      const result: CommandResult = {
        id,
        command,
        result: `Error: ${e instanceof Error ? e.message : 'Connection failed'}`,
        success: false,
        timestamp: new Date(),
        duration: Date.now() - startTime,
      };
      setCommandHistory(prev => [result, ...prev].slice(0, 50));
      setLastResult(result);
    }
  }, []);

  // Fetch system info
  const fetchSystemInfo = useCallback(async () => {
    setLoading(prev => ({ ...prev, system: true }));
    try {
      const resp = await fetch('/api/jarvis/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'system' }),
      });
      if (resp.ok) {
        // Parse system info from response
        const data = await resp.json();
        // Extract key-value pairs from the response
        const lines = data.content.split('\n');
        const info: Partial<SystemInfo> = {};
        for (const line of lines) {
          if (line.includes('Hostname:')) info.hostname = line.split(':')[1]?.trim();
          if (line.includes('User:')) info.username = line.split(':')[1]?.trim();
          if (line.includes('OS:')) info.os_version = line.split(':').slice(1).join(':').trim();
          if (line.includes('CPU cores:')) info.cpu_count = parseInt(line.split(':')[1]) || 0;
          if (line.includes('Memory:')) {
            const match = line.match(/([\d.]+)\s*GB\s*\/\s*([\d.]+)\s*GB/);
            if (match) {
              info.memory_available_gb = parseFloat(match[1]);
              info.memory_total_gb = parseFloat(match[2]);
            }
          }
        }
        setSystemInfo(info as SystemInfo);
      }
    } finally {
      setLoading(prev => ({ ...prev, system: false }));
    }
  }, []);

  // Fetch processes
  const fetchProcesses = useCallback(async () => {
    setLoading(prev => ({ ...prev, processes: true }));
    try {
      const resp = await fetch('/api/jarvis/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'processes' }),
      });
      if (resp.ok) {
        const data = await resp.json();
        // Parse process list from response
        const lines = data.content.split('\n').filter((l: string) => l.includes('(PID'));
        const procs: Process[] = lines.map((line: string) => {
          const match = line.match(/PID\s+(\d+).*?CPU\s+([\d.]+).*?RAM\s+(\d+)MB/);
          if (match) {
            return {
              pid: parseInt(match[1]),
              name: line.split('(')[0].replace('- ', '').trim(),
              cpu_percent: parseFloat(match[2]),
              memory_mb: parseInt(match[3]),
              status: 'running',
            };
          }
          return null;
        }).filter(Boolean) as Process[];
        setProcesses(procs);
      }
    } finally {
      setLoading(prev => ({ ...prev, processes: false }));
    }
  }, []);

  // Fetch open windows
  const fetchWindows = useCallback(async () => {
    try {
      const resp = await fetch('/api/jarvis/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'windows' }),
      });
      if (resp.ok) {
        const data = await resp.json();
        const lines = data.content.split('\n').filter((l: string) => l.startsWith('- '));
        const wins: Window[] = lines.map((line: string) => {
          const parts = line.replace('- ', '').split(':');
          return {
            name: parts[0]?.trim() || '',
            title: parts.slice(1).join(':').trim() || '',
          };
        });
        setOpenWindows(wins);
      }
    } catch {
      // Silently fail
    }
  }, []);

  // Fetch clipboard
  const fetchClipboard = useCallback(async () => {
    try {
      const resp = await fetch('/api/jarvis/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'clipboard' }),
      });
      if (resp.ok) {
        const data = await resp.json();
        const content = data.content.replace('**Clipboard:**\n```\n', '').replace('\n```', '').trim();
        if (content && content !== 'Clipboard is empty.') {
          setClipboardContent(content);
        }
      }
    } catch {
      // Silently fail
    }
  }, []);

  // Kill process
  const killProcess = useCallback(async (pid: number) => {
    await executeCommand(`run Stop-Process -Id ${pid} -Force`);
    fetchProcesses();
  }, [executeCommand, fetchProcesses]);

  // Open app
  const openApp = useCallback(async (app: string) => {
    await executeCommand(`open ${app}`);
    fetchWindows();
  }, [executeCommand, fetchWindows]);

  // Close app
  const closeApp = useCallback(async (app: string) => {
    await executeCommand(`close ${app}`);
    fetchWindows();
  }, [executeCommand, fetchWindows]);

  // Initial data load
  useEffect(() => {
    fetchSystemInfo();
    fetchProcesses();
    fetchWindows();
    fetchClipboard();
    setConnected(true);

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchProcesses();
      fetchWindows();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchSystemInfo, fetchProcesses, fetchWindows, fetchClipboard]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Terminal className="h-6 w-6 text-cyan-500" />
            Jarvis Control Center
          </h1>
          <p className="text-muted-foreground mt-1">Full device control and monitoring</p>
        </div>
        <Badge variant={connected ? 'default' : 'destructive'} className="text-sm">
          {connected ? 'Connected' : 'Disconnected'}
        </Badge>
      </div>

      {/* Main Layout */}
      <div className="grid grid-cols-12 gap-4">
        {/* Left Panel - Command Palette */}
        <div className="col-span-3">
          <CommandPalette onCommand={executeCommand} history={commandHistory} />
        </div>

        {/* Center Panel - Results + Tabs */}
        <div className="col-span-6">
          <Tabs defaultValue="results" className="h-full">
            <TabsList>
              <TabsTrigger value="results" className="flex items-center gap-1">
                <Terminal className="h-3.5 w-3.5" />
                Results
              </TabsTrigger>
              <TabsTrigger value="system" className="flex items-center gap-1">
                <Monitor className="h-3.5 w-3.5" />
                System
              </TabsTrigger>
              <TabsTrigger value="processes" className="flex items-center gap-1">
                <Activity className="h-3.5 w-3.5" />
                Processes
              </TabsTrigger>
              <TabsTrigger value="apps" className="flex items-center gap-1">
                <AppWindow className="h-3.5 w-3.5" />
                Apps
              </TabsTrigger>
            </TabsList>

            <TabsContent value="results" className="mt-4">
              <ResultsPanel result={lastResult} />
            </TabsContent>

            <TabsContent value="system" className="mt-4">
              <SystemPanel data={systemInfo} loading={loading.system} />
            </TabsContent>

            <TabsContent value="processes" className="mt-4">
              <ProcessManager
                processes={processes}
                loading={loading.processes}
                onRefresh={fetchProcesses}
                onKill={killProcess}
              />
            </TabsContent>

            <TabsContent value="apps" className="mt-4">
              <AppLauncher
                onOpen={openApp}
                onClose={closeApp}
                openWindows={openWindows}
              />
            </TabsContent>
          </Tabs>
        </div>

        {/* Right Panel - History + Clipboard */}
        <div className="col-span-3 space-y-4">
          <ClipboardManager
            currentClipboard={clipboardContent}
            history={clipboardHistory}
            onCopy={(text) => navigator.clipboard.writeText(text)}
            onClear={() => setClipboardHistory([])}
          />
          <CommandHistory
            history={commandHistory}
            onClear={() => setCommandHistory([])}
            onRerun={executeCommand}
          />
        </div>
      </div>
    </div>
  );
}
