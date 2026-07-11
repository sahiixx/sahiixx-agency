import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Terminal, Globe, FileText, Code, MessageSquare,
  Music, Settings, Calculator, Palette
} from 'lucide-react';

interface AppLauncherProps {
  onOpen: (app: string) => void;
  onClose: (app: string) => void;
  openWindows: { name: string; title: string }[];
}

const APPS = [
  { name: 'vscode', label: 'VS Code', icon: Code, color: 'text-blue-500' },
  { name: 'chrome', label: 'Chrome', icon: Globe, color: 'text-green-500' },
  { name: 'edge', label: 'Edge', icon: Globe, color: 'text-blue-400' },
  { name: 'firefox', label: 'Firefox', icon: Globe, color: 'text-orange-500' },
  { name: 'notepad', label: 'Notepad', icon: FileText, color: 'text-yellow-500' },
  { name: 'explorer', label: 'Explorer', icon: FolderIcon, color: 'text-yellow-400' },
  { name: 'cmd', label: 'CMD', icon: Terminal, color: 'text-gray-500' },
  { name: 'powershell', label: 'PowerShell', icon: Terminal, color: 'text-blue-600' },
  { name: 'teams', label: 'Teams', icon: MessageSquare, color: 'text-indigo-500' },
  { name: 'slack', label: 'Slack', icon: MessageSquare, color: 'text-purple-500' },
  { name: 'spotify', label: 'Spotify', icon: Music, color: 'text-green-400' },
  { name: 'calculator', label: 'Calculator', icon: Calculator, color: 'text-gray-400' },
  { name: 'paint', label: 'Paint', icon: Palette, color: 'text-pink-500' },
  { name: 'settings', label: 'Settings', icon: Settings, color: 'text-gray-500' },
];

function FolderIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  );
}

export function AppLauncher({ onOpen, onClose, openWindows }: AppLauncherProps) {
  const isAppOpen = (appName: string) => {
    return openWindows.some(w => w.name.toLowerCase().includes(appName.toLowerCase()));
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <span className="text-base">🚀</span>
          Applications
          <Badge variant="outline" className="text-xs">{openWindows.length} open</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-4 gap-2">
          {APPS.map((app) => {
            const isOpen = isAppOpen(app.name);
            const Icon = app.icon;

            return (
              <Button
                key={app.name}
                variant="outline"
                className={`h-20 flex flex-col items-center justify-center gap-1.5 ${
                  isOpen ? 'border-green-500 bg-green-500/10' : ''
                }`}
                onClick={() => isOpen ? onClose(app.name) : onOpen(app.name)}
              >
                <Icon className={`h-5 w-5 ${app.color}`} />
                <span className="text-xs">{app.label}</span>
                {isOpen && (
                  <Badge variant="default" className="text-[10px] h-4 px-1">OPEN</Badge>
                )}
              </Button>
            );
          })}
        </div>

        {/* Open Windows List */}
        {openWindows.length > 0 && (
          <div className="mt-4 space-y-1">
            <div className="text-xs font-medium text-muted-foreground mb-2">Active Windows</div>
            {openWindows.map((w, i) => (
              <div
                key={`${w.name}-${i}`}
                className="flex items-center justify-between p-2 rounded bg-muted/50 text-xs"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  <span className="truncate">{w.title || w.name}</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 text-xs"
                  onClick={() => onClose(w.name)}
                >
                  Close
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
