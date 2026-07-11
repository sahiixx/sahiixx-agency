import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Keyboard } from 'lucide-react';
import { JARVIS_SHORTCUTS, type ShortcutKey } from '@/hooks/useKeyboardShortcuts';

interface ShortcutsHelpProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function ShortcutsHelp({ open: controlledOpen, onOpenChange }: ShortcutsHelpProps) {
  const [internalOpen, setInternalOpen] = useState(false);

  const isOpen = controlledOpen ?? internalOpen;
  const setIsOpen = onOpenChange ?? setInternalOpen;

  const formatKey = (shortcut: { key: string; ctrl?: boolean; alt?: boolean; shift?: boolean }) => {
    const parts: string[] = [];
    if (shortcut.ctrl) parts.push('Ctrl');
    if (shortcut.alt) parts.push('Alt');
    if (shortcut.shift) parts.push('Shift');
    parts.push(shortcut.key === ' ' ? 'Space' : shortcut.key.toUpperCase());
    return parts.join(' + ');
  };

  const shortcutEntries = Object.entries(JARVIS_SHORTCUTS) as [ShortcutKey, typeof JARVIS_SHORTCUTS[ShortcutKey]][];

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-7 w-7" title="Keyboard shortcuts (?)">
          <Keyboard className="h-3.5 w-3.5" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Keyboard className="h-5 w-5" />
            Keyboard Shortcuts
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <h4 className="text-sm font-medium mb-2 text-muted-foreground">General</h4>
            <div className="space-y-1">
              {shortcutEntries
                .filter(([key]) => ['VOICE_TOGGLE', 'CLEAR_CHAT', 'FOCUS_INPUT', 'DISMISS'].includes(key))
                .map(([key, shortcut]) => (
                  <div key={key} className="flex items-center justify-between py-1">
                    <span className="text-sm">{shortcut.description}</span>
                    <kbd className="px-2 py-0.5 text-xs font-mono bg-muted rounded border">
                      {formatKey(shortcut)}
                    </kbd>
                  </div>
                ))}
            </div>
          </div>
          <div>
            <h4 className="text-sm font-medium mb-2 text-muted-foreground">Quick Commands</h4>
            <div className="space-y-1">
              {shortcutEntries
                .filter(([key]) => key.startsWith('QUICK_'))
                .map(([key, shortcut]) => (
                  <div key={key} className="flex items-center justify-between py-1">
                    <span className="text-sm">{shortcut.description}</span>
                    <kbd className="px-2 py-0.5 text-xs font-mono bg-muted rounded border">
                      {formatKey(shortcut)}
                    </kbd>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
