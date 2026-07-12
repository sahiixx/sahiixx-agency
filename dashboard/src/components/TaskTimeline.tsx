import { Clock, CheckCircle2, Loader2, XCircle } from 'lucide-react';

interface TaskTimelineProps {
  status?: string;
  module?: string;
}

export function TaskTimeline({ status = 'pending', module }: TaskTimelineProps) {
  const steps = [
    { key: 'pending', label: 'Queued', icon: <Clock className="w-3 h-3" /> },
    { key: 'running', label: 'Running', icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    { key: 'completed', label: 'Done', icon: <CheckCircle2 className="w-3 h-3" /> },
  ];

  const currentIndex = steps.findIndex(s => s.key === status);
  const isFailed = status === 'failed' || status === 'cancelled';

  return (
    <div className="flex items-center gap-2 text-xs">
      <div className="flex items-center gap-1">
        {steps.map((step, idx) => {
          const isActive = idx <= currentIndex && !isFailed;
          const isCurrent = idx === currentIndex && !isFailed;
          return (
            <div key={step.key} className="flex items-center gap-1">
              <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded ${
                isActive ? 'bg-accent-cyan/20 text-accent-cyan' : 'bg-white/5 text-[var(--text-muted)]'
              } ${isCurrent ? 'ring-1 ring-accent-cyan/50' : ''}`}>
                {step.icon}
                <span className="text-[10px] uppercase font-semibold tracking-wider">{step.label}</span>
              </div>
              {idx < steps.length - 1 && (
                <div className={`w-3 h-px ${isActive ? 'bg-accent-cyan/40' : 'bg-white/10'}`} />
              )}
            </div>
          );
        })}
      </div>
      {isFailed && (
        <div className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">
          <XCircle className="w-3 h-3" />
          <span className="text-[10px] uppercase font-semibold tracking-wider">Failed</span>
        </div>
      )}
      {module && (
        <span className="text-[10px] text-[var(--text-muted)] ml-1">· {module}</span>
      )}
    </div>
  );
}
