import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Cpu, Search, X, ArrowUpDown } from 'lucide-react';

interface Process {
  pid: number;
  name: string;
  cpu_percent: number;
  memory_mb: number;
  status: string;
}

interface ProcessManagerProps {
  processes: Process[];
  loading: boolean;
  onRefresh: () => void;
  onKill: (pid: number) => void;
}

export function ProcessManager({ processes, loading, onRefresh, onKill }: ProcessManagerProps) {
  const [filter, setFilter] = useState('');
  const [sortBy, setSortBy] = useState<'cpu' | 'memory' | 'name'>('cpu');

  const filtered = processes
    .filter(p => !filter || p.name.toLowerCase().includes(filter.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === 'cpu') return b.cpu_percent - a.cpu_percent;
      if (sortBy === 'memory') return b.memory_mb - a.memory_mb;
      return a.name.localeCompare(b.name);
    });

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Cpu className="h-4 w-4" />
            Processes
            <Badge variant="outline" className="text-xs">{processes.length}</Badge>
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={onRefresh} className="h-7 text-xs">
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Filter */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
            <Input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter processes..."
              className="h-7 pl-7 text-xs"
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => setSortBy(sortBy === 'cpu' ? 'memory' : sortBy === 'memory' ? 'name' : 'cpu')}
          >
            <ArrowUpDown className="h-3 w-3 mr-1" />
            {sortBy.toUpperCase()}
          </Button>
        </div>

        {/* Process List */}
        <ScrollArea className="h-[300px]">
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="h-10 bg-muted animate-pulse rounded" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">
              No processes found
            </div>
          ) : (
            <div className="space-y-1">
              {filtered.map((proc) => (
                <div
                  key={proc.pid}
                  className="flex items-center justify-between p-2 rounded hover:bg-muted text-xs"
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="font-mono text-muted-foreground w-12">{proc.pid}</span>
                    <span className="truncate">{proc.name}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-cyan-500 w-16 text-right">{proc.cpu_percent.toFixed(1)}%</span>
                    <span className="text-purple-500 w-16 text-right">{proc.memory_mb.toFixed(0)}MB</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => onKill(proc.pid)}
                      title="Kill process"
                    >
                      <X className="h-3 w-3 text-red-500" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
