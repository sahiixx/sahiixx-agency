import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Clipboard, Copy, Trash2, Clock } from 'lucide-react';

interface ClipboardItem {
  id: string;
  content: string;
  timestamp: Date;
}

interface ClipboardManagerProps {
  currentClipboard: string;
  history: ClipboardItem[];
  onCopy?: (text: string) => Promise<void>;
  onClear: () => void;
}

export function ClipboardManager({ currentClipboard, history, onClear }: ClipboardManagerProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <Clipboard className="w-4 h-4" />
          Clipboard Manager
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {/* Current Clipboard */}
        <div className="px-4 pb-2">
          <div className="text-xs text-muted-foreground mb-1">Current</div>
          <div className="p-2 rounded bg-muted/50 text-xs font-mono break-all min-h-[2rem]">
            {currentClipboard || 'Empty'}
          </div>
        </div>

        {/* History */}
        <div className="px-4 pb-2">
          <div className="text-xs text-muted-foreground mb-1">History ({history.length})</div>
        </div>
        <ScrollArea className="h-[200px] px-4">
          {history.length === 0 ? (
            <div className="text-center text-muted-foreground text-xs py-4">No history</div>
          ) : (
            <div className="space-y-1">
              {history.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center gap-2 p-2 rounded bg-muted/30 hover:bg-muted/50 transition-colors group"
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-mono truncate">{item.content}</div>
                    <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {item.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => handleCopy(item.content, item.id)}
                  >
                    <Copy className="w-3 h-3" />
                  </Button>
                  {copiedId === item.id && (
                    <Badge variant="outline" className="text-[10px] h-5">Copied</Badge>
                  )}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>

        <div className="px-4 pt-2 pb-4">
          <Button
            variant="outline"
            size="sm"
            className="w-full text-xs"
            onClick={onClear}
          >
            <Trash2 className="w-3 h-3 mr-1" />
            Clear History
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
