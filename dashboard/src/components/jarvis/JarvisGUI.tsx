import { useState, useEffect, useCallback, useRef } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import {
  Monitor, Terminal, AppWindow, Activity, Cpu, HardDrive, MemoryStick,
  Battery, Clock, Send, CheckCircle, XCircle,
  Keyboard, Clipboard, FolderOpen, Play, Square, RefreshCw
} from 'lucide-react';

interface CommandResult {
  id: string;
  command: string;
  result: string;
  success: boolean;
  timestamp: Date;
  duration: number;
}

// Command categories with icons
const COMMANDS = [
  { name: 'system', label: 'System Info', icon: Monitor, category: 'System', description: 'CPU, memory, disk, battery' },
  { name: 'status', label: 'Status', icon: Activity, category: 'System', description: 'Jarvis status' },
  { name: 'health', label: 'Health', icon: Activity, category: 'System', description: 'System health checks' },
  { name: 'help', label: 'Help', icon: Keyboard, category: 'System', description: 'Show all commands' },
  { name: 'processes', label: 'Processes', icon: Cpu, category: 'System', description: 'List running processes' },
  { name: 'windows', label: 'Windows', icon: AppWindow, category: 'Apps', description: 'List open windows' },
  { name: 'open', label: 'Open App', icon: Play, category: 'Apps', description: 'Open an application', needsArg: true },
  { name: 'close', label: 'Close App', icon: Square, category: 'Apps', description: 'Close an application', needsArg: true },
  { name: 'clipboard', label: 'Clipboard', icon: Clipboard, category: 'Files', description: 'Show clipboard' },
  { name: 'screenshot', label: 'Screenshot', icon: Monitor, category: 'Files', description: 'Take screenshot' },
  { name: 'files', label: 'Files', icon: FolderOpen, category: 'Files', description: 'List directory', needsArg: true },
  { name: 'run', label: 'Run Command', icon: Terminal, category: 'System', description: 'Execute shell command', needsArg: true },
  { name: 'battery', label: 'Battery', icon: Battery, category: 'System', description: 'Battery status' },
  { name: 'network', label: 'Network', icon: Activity, category: 'System', description: 'Network info' },
];

export function JarvisGUI() {
  const [history, setHistory] = useState<CommandResult[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Persist history to localStorage
  useEffect(() => {
    const saved = localStorage.getItem('jarvis_history');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setHistory(parsed.map((h: any) => ({ ...h, timestamp: new Date(h.timestamp) })));
      } catch {}
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('jarvis_history', JSON.stringify(history.slice(0, 50)));
  }, [history]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history]);

  // Execute command
  const executeCommand = useCallback(async (command: string) => {
    if (!command.trim()) return;

    const startTime = Date.now();
    const id = Date.now().toString();

    setLoading(true);
    setInput('');

    try {
      const resp = await fetch('/api/jarvis/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: command }),
      });

      const data = await resp.json();
      const result: CommandResult = {
        id,
        command,
        result: data.content || 'No response',
        success: resp.ok,
        timestamp: new Date(),
        duration: Date.now() - startTime,
      };

      setHistory(prev => [result, ...prev]);
    } catch (e) {
      setHistory(prev => [{
        id,
        command,
        result: `Error: ${e instanceof Error ? e.message : 'Connection failed'}`,
        success: false,
        timestamp: new Date(),
        duration: Date.now() - startTime,
      }, ...prev]);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="h-[calc(100vh-100px)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
            <Terminal className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Jarvis Control Center</h1>
            <p className="text-xs text-muted-foreground">Full device control and monitoring</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="default" className="bg-green-500">Connected</Badge>
          <Button variant="ghost" size="icon" onClick={() => setHistory([])}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
        {/* Left - Command Palette */}
        <div className="col-span-3 flex flex-col">
          <Card className="flex-1 flex flex-col overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Keyboard className="h-4 w-4" />
                Commands
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-hidden p-2">
              <ScrollArea className="h-full">
                <div className="space-y-1">
                  {COMMANDS.map(cmd => (
                    <button
                      key={cmd.name}
                      onClick={() => {
                        if (cmd.needsArg) {
                          setInput(`${cmd.name} `);
                        } else {
                          executeCommand(cmd.name);
                        }
                      }}
                      className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-left hover:bg-muted text-sm group"
                    >
                      <cmd.icon className="h-3.5 w-3.5 text-muted-foreground group-hover:text-foreground" />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-xs">{cmd.label}</div>
                        <div className="text-[10px] text-muted-foreground truncate">{cmd.description}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Center - Terminal */}
        <div className="col-span-6 flex flex-col">
          <Card className="flex-1 flex flex-col overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Terminal className="h-4 w-4" />
                Terminal
                <Badge variant="outline" className="text-xs ml-auto">{history.length} commands</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col overflow-hidden p-2">
              {/* Output */}
              <ScrollArea className="flex-1 mb-2" ref={scrollRef}>
                <div className="space-y-2 p-2">
                  {history.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <Terminal className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">Type a command to get started</p>
                      <p className="text-xs mt-1">Try: system, processes, open chrome</p>
                    </div>
                  ) : (
                    history.map(item => (
                      <div key={item.id} className="border rounded-lg overflow-hidden">
                        {/* Command */}
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/50 text-xs">
                          {item.success ? (
                            <CheckCircle className="h-3 w-3 text-green-500" />
                          ) : (
                            <XCircle className="h-3 w-3 text-red-500" />
                          )}
                          <span className="font-mono font-medium">{item.command}</span>
                          <span className="text-muted-foreground ml-auto">{item.duration}ms</span>
                        </div>
                        {/* Output */}
                        <div className="p-3 bg-black/50">
                          <pre className="text-xs font-mono text-green-400 whitespace-pre-wrap overflow-auto max-h-48">
                            {item.result}
                          </pre>
                        </div>
                      </div>
                    ))
                  )}
                  {loading && (
                    <div className="flex items-center gap-2 px-3 py-2 bg-muted/50 rounded text-xs">
                      <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
                      <span className="text-muted-foreground">Executing...</span>
                    </div>
                  )}
                </div>
              </ScrollArea>

              {/* Input */}
              <div className="flex gap-2">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && executeCommand(input)}
                  placeholder="Type a command... (e.g., system, open chrome, processes)"
                  className="font-mono text-sm"
                  disabled={loading}
                />
                <Button
                  onClick={() => executeCommand(input)}
                  size="icon"
                  disabled={loading || !input.trim()}
                  className="shrink-0"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right - Quick Info */}
        <div className="col-span-3 flex flex-col gap-4">
          {/* Quick Stats */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Quick Info
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <Cpu className="h-3 w-3 text-cyan-500" />
                  <span>CPU</span>
                </div>
                <span className="text-muted-foreground">35%</span>
              </div>
              <Progress value={35} className="h-1" />

              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <MemoryStick className="h-3 w-3 text-purple-500" />
                  <span>RAM</span>
                </div>
                <span className="text-muted-foreground">8.2 / 16 GB</span>
              </div>
              <Progress value={51} className="h-1" />

              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <HardDrive className="h-3 w-3 text-amber-500" />
                  <span>Disk</span>
                </div>
                <span className="text-muted-foreground">256 / 512 GB</span>
              </div>
              <Progress value={50} className="h-1" />
            </CardContent>
          </Card>

          {/* Recent History */}
          <Card className="flex-1 flex flex-col overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Clock className="h-4 w-4" />
                History
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-hidden p-2">
              <ScrollArea className="h-full">
                <div className="space-y-1">
                  {history.length === 0 ? (
                    <p className="text-xs text-muted-foreground text-center py-4">No commands yet</p>
                  ) : (
                    history.slice(0, 20).map(item => (
                      <button
                        key={item.id}
                        onClick={() => executeCommand(item.command)}
                        className="w-full flex items-center gap-2 px-2 py-1 rounded hover:bg-muted text-left"
                      >
                        {item.success ? (
                          <CheckCircle className="h-3 w-3 text-green-500 shrink-0" />
                        ) : (
                          <XCircle className="h-3 w-3 text-red-500 shrink-0" />
                        )}
                        <span className="font-mono text-xs truncate flex-1">{item.command}</span>
                        <span className="text-[10px] text-muted-foreground shrink-0">{item.duration}ms</span>
                      </button>
                    ))
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
