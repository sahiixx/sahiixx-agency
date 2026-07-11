import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Terminal, CheckCircle, XCircle, Copy, Trash2, ChevronDown, ChevronRight } from 'lucide-react';

interface CommandResult {
  id: string;
  command: string;
  result: string;
  success: boolean;
  timestamp: Date;
  duration: number;
}

interface CommandHistoryProps {
  history: CommandResult[];
  onClear: () => void;
  onRerun: (command: string) => void;
}

export function CommandHistory({ history, onClear, onRerun }: CommandHistoryProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Terminal className="h-4 w-4" />
            Command History
            <Badge variant="outline" className="text-xs">{history.length}</Badge>
          </CardTitle>
          {history.length > 0 && (
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={onClear}>
              <Trash2 className="h-3 w-3 mr-1" />
              Clear
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px]">
          {history.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Terminal className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No commands yet</p>
              <p className="text-xs">Run a command to see results here</p>
            </div>
          ) : (
            <div className="space-y-2">
              {history.map((item) => (
                <div
                  key={item.id}
                  className="border rounded-lg overflow-hidden"
                >
                  {/* Command Header */}
                  <button
                    onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                    className="w-full flex items-center gap-2 p-2 hover:bg-muted text-left"
                  >
                    {expandedId === item.id ? (
                      <ChevronDown className="h-3 w-3 shrink-0" />
                    ) : (
                      <ChevronRight className="h-3 w-3 shrink-0" />
                    )}
                    {item.success ? (
                      <CheckCircle className="h-3 w-3 text-green-500 shrink-0" />
                    ) : (
                      <XCircle className="h-3 w-3 text-red-500 shrink-0" />
                    )}
                    <span className="font-mono text-xs truncate flex-1">{item.command}</span>
                    <span className="text-xs text-muted-foreground shrink-0">{item.duration}ms</span>
                  </button>

                  {/* Expanded Result */}
                  {expandedId === item.id && (
                    <div className="border-t bg-muted/30 p-2">
                      <pre className="text-xs font-mono whitespace-pre-wrap max-h-48 overflow-auto">
                        {item.result}
                      </pre>
                      <div className="flex gap-1 mt-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 text-xs"
                          onClick={() => copyToClipboard(item.result)}
                        >
                          <Copy className="h-3 w-3 mr-1" />
                          Copy
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 text-xs"
                          onClick={() => onRerun(item.command)}
                        >
                          <Terminal className="h-3 w-3 mr-1" />
                          Rerun
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
