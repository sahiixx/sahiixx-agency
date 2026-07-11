import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { CheckCircle, XCircle, Clock, Copy, Terminal } from 'lucide-react';

interface CommandResult {
  id: string;
  command: string;
  result: string;
  success: boolean;
  timestamp: Date;
  duration: number;
}

interface ResultsPanelProps {
  result: CommandResult | null;
}

export function ResultsPanel({ result }: ResultsPanelProps) {
  if (!result) {
    return (
      <Card className="h-full">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Terminal className="h-4 w-4" />
            Results
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12 text-muted-foreground">
            <Terminal className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Run a command to see results</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            {result.success ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : (
              <XCircle className="h-4 w-4 text-red-500" />
            )}
            Results
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={result.success ? 'default' : 'destructive'} className="text-xs">
              {result.success ? 'Success' : 'Failed'}
            </Badge>
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {result.duration}ms
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Command */}
        <div>
          <div className="text-xs text-muted-foreground mb-1">Command</div>
          <div className="p-2 bg-muted rounded font-mono text-sm">{result.command}</div>
        </div>

        {/* Result */}
        <div>
          <div className="text-xs text-muted-foreground mb-1">Output</div>
          <ScrollArea className="h-[300px]">
            <pre className="p-3 bg-black/90 text-green-400 rounded font-mono text-xs whitespace-pre-wrap overflow-auto">
              {result.result || '(no output)'}
            </pre>
          </ScrollArea>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => navigator.clipboard.writeText(result.result)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <Copy className="h-3 w-3" />
            Copy output
          </button>
          <span className="text-xs text-muted-foreground">
            {new Date(result.timestamp).toLocaleTimeString()}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
