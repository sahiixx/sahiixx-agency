import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Activity, Cpu, HardDrive, Wifi } from 'lucide-react';

export function LiveMetricsHUD() {
  const [metrics, setMetrics] = useState({ cpu: 12, memory: 45, disk: 62, network: 8 });

  useEffect(() => {
    const t = setInterval(() => {
      setMetrics({
        cpu: Math.floor(Math.random() * 40) + 5,
        memory: Math.floor(Math.random() * 30) + 30,
        disk: Math.floor(Math.random() * 20) + 50,
        network: Math.floor(Math.random() * 50) + 1,
      });
    }, 3000);
    return () => clearInterval(t);
  }, []);

  const items = [
    { label: 'CPU', value: metrics.cpu, unit: '%', icon: <Cpu className="w-3 h-3" />, color: 'text-blue-400' },
    { label: 'RAM', value: metrics.memory, unit: '%', icon: <Activity className="w-3 h-3" />, color: 'text-green-400' },
    { label: 'Disk', value: metrics.disk, unit: '%', icon: <HardDrive className="w-3 h-3" />, color: 'text-amber-400' },
    { label: 'Net', value: metrics.network, unit: 'Mb', icon: <Wifi className="w-3 h-3" />, color: 'text-purple-400' },
  ];

  const barColor = (val: number) => {
    if (val > 80) return 'bg-red-500';
    if (val > 50) return 'bg-amber-500';
    return 'bg-green-500';
  };

  return (
    <Card className="bg-black/80 border-white/10 backdrop-blur-sm">
      <CardContent className="p-3">
        <div className="grid grid-cols-4 gap-2">
          {items.map((m) => (
            <div key={m.label} className="text-center">
              <div className={`flex items-center justify-center gap-1 ${m.color} mb-1`}>
                {m.icon}
                <span className="text-[10px] font-bold uppercase tracking-wider">{m.label}</span>
              </div>
              <div className="text-lg font-mono font-bold text-white leading-none">
                {m.value}{m.unit}
              </div>
              <div className="w-full h-1 bg-white/10 rounded-full mt-1 overflow-hidden">
                <div className={`h-full rounded-full transition-all duration-500 ${barColor(m.value)}`} style={{ width: `${Math.min(m.value, 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
