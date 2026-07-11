import { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Terminal, Play, Trash2, Clock, CheckCircle, XCircle,
  Monitor, Cpu, Wifi, Battery, AppWindow,
  Clipboard, Camera, Keyboard, MousePointer,
  Package, FolderOpen, Layers, Zap
} from 'lucide-react';

interface CommandResult {
  id: string;
  command: string;
  result: string;
  success: boolean;
  timestamp: Date;
  duration: number;
}

interface CommandCategory {
  name: string;
  icon: React.ReactNode;
  commands: { name: string; description: string; icon: React.ReactNode }[];
}

const COMMAND_CATEGORIES: CommandCategory[] = [
  {
    name: 'System',
    icon: <Monitor className="h-4 w-4" />,
    commands: [
      { name: 'system', description: 'System info', icon: <Cpu className="h-3 w-3" /> },
      { name: 'battery', description: 'Battery status', icon: <Battery className="h-3 w-3" /> },
      { name: 'network', description: 'Network info', icon: <Wifi className="h-3 w-3" /> },
      { name: 'wifi', description: 'WiFi networks', icon: <Wifi className="h-3 w-3" /> },
    ],
  },
  {
    name: 'Applications',
    icon: <AppWindow className="h-4 w-4" />,
    commands: [
      { name: 'open', description: 'Open app', icon: <Play className="h-3 w-3" /> },
      { name: 'close', description: 'Close app', icon: <Trash2 className="h-3 w-3" /> },
      { name: 'windows', description: 'List windows', icon: <Layers className="h-3 w-3" /> },
      { name: 'focus', description: 'Focus window', icon: <Zap className="h-3 w-3" /> },
    ],
  },
  {
    name: 'Files',
    icon: <FolderOpen className="h-4 w-4" />,
    commands: [
      { name: 'files', description: 'List directory', icon: <FolderOpen className="h-3 w-3" /> },
      { name: 'clipboard', description: 'Clipboard', icon: <Clipboard className="h-3 w-3" /> },
      { name: 'screenshot', description: 'Screenshot', icon: <Camera className="h-3 w-3" /> },
    ],
  },
  {
    name: 'Input',
    icon: <Keyboard className="h-4 w-4" />,
    commands: [
      { name: 'type', description: 'Type text', icon: <Keyboard className="h-3 w-3" /> },
      { name: 'key', description: 'Press key', icon: <Keyboard className="h-3 w-3" /> },
      { name: 'mouse', description: 'Move mouse', icon: <MousePointer className="h-3 w-3" /> },
    ],
  },
  {
    name: 'Processes',
    icon: <Cpu className="h-4 w-4" />,
    commands: [
      { name: 'processes', description: 'List processes', icon: <Cpu className="h-3 w-3" /> },
      { name: 'run', description: 'Run command', icon: <Terminal className="h-3 w-3" /> },
      { name: 'install', description: 'Install package', icon: <Package className="h-3 w-3" /> },
    ],
  },
];

interface CommandPaletteProps {
  onCommand: (command: string) => void;
  history: CommandResult[];
}

export function CommandPalette({ onCommand, history }: CommandPaletteProps) {
  const [input, setInput] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    if (input.trim()) {
      onCommand(input.trim());
      setInput('');
    }
  };

  const handleQuickCommand = (cmd: string, needsArg: boolean = false) => {
    if (needsArg) {
      setInput(`${cmd} `);
      inputRef.current?.focus();
    } else {
      onCommand(cmd);
    }
  };

  const needsArg = (name: string) => ['open', 'close', 'focus', 'type', 'key', 'mouse', 'run', 'install', 'files'].includes(name);

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Terminal className="h-4 w-4" />
          Command Palette
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Input */}
        <div className="flex gap-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            placeholder="Type a command..."
            className="font-mono text-sm"
          />
          <Button onClick={handleSubmit} size="icon" disabled={!input.trim()}>
            <Play className="h-4 w-4" />
          </Button>
        </div>

        {/* Command Categories */}
        <div className="space-y-3">
          {COMMAND_CATEGORIES.map((category) => (
            <div key={category.name}>
              <button
                onClick={() => setSelectedCategory(selectedCategory === category.name ? null : category.name)}
                className="flex items-center gap-2 w-full text-left text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                {category.icon}
                {category.name}
              </button>
              {selectedCategory === category.name && (
                <div className="grid grid-cols-2 gap-1 mt-2">
                  {category.commands.map((cmd) => (
                    <Button
                      key={cmd.name}
                      variant="outline"
                      size="sm"
                      className="h-8 justify-start text-xs"
                      onClick={() => handleQuickCommand(cmd.name, needsArg(cmd.name))}
                    >
                      {cmd.icon}
                      <span className="ml-1">{cmd.name}</span>
                    </Button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Recent History */}
        {history.length > 0 && (
          <div>
            <div className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Recent
            </div>
            <ScrollArea className="h-32">
              <div className="space-y-1">
                {history.slice(0, 5).map((item) => (
                  <button
                    key={item.id}
                    onClick={() => onCommand(item.command)}
                    className="w-full flex items-center gap-2 text-xs p-1.5 rounded hover:bg-muted text-left"
                  >
                    {item.success ? (
                      <CheckCircle className="h-3 w-3 text-green-500 shrink-0" />
                    ) : (
                      <XCircle className="h-3 w-3 text-red-500 shrink-0" />
                    )}
                    <span className="font-mono truncate">{item.command}</span>
                    <span className="text-muted-foreground ml-auto shrink-0">{item.duration}ms</span>
                  </button>
                ))}
              </div>
            </ScrollArea>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
