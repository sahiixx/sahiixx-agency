import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface SystemChartsProps {
  cpuData: number[]
  memData: number[]
  diskData?: number[]
  netData?: { sent: number; recv: number }[]
  loading?: boolean
}

const CHART_COLORS = {
  cpu: '#00F0FF',
  mem: '#8B5CF6',
  disk: '#EAB308',
  netSent: '#00FF66',
  netRecv: '#3B82F6',
}

function ChartCard({
  title,
  color,
  gradientId,
  dataKey,
  data,
  formatter,
  secondary,
}: {
  title: string
  color: string
  gradientId: string
  dataKey: string
  data: any[]
  formatter?: (v: number) => string
  secondary?: { key: string; color: string; gradientId: string; name: string }
}) {
  const hasData = data.length >= 2
  const current = hasData ? data[data.length - 1][dataKey] : 0

  // Status color based on value
  const getStatusColor = (value: number) => {
    if (value >= 80) return '#FF1A1A'
    if (value >= 50) return '#EAB308'
    return color
  }

  const statusColor = hasData ? getStatusColor(current) : color

  return (
    <div
      className="jarvis-card corner-brackets p-4 space-y-3 hover:border-jarvis-cyan/30 transition-all duration-300"
      style={{ '--accent-color': statusColor } as React.CSSProperties}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="live-pulse" style={{ '--pulse-color': statusColor } as React.CSSProperties} />
          <div className="text-[10px] text-jarvis-text-muted uppercase font-semibold tracking-wider font-display">
            {title}
          </div>
        </div>
        {hasData && (
          <div
            className="text-lg font-mono font-bold text-glow"
            style={{ color: statusColor, '--glow-color': `${statusColor}66` } as React.CSSProperties}
          >
            {formatter ? formatter(current) : `${current}%`}
          </div>
        )}
      </div>

      {/* Chart */}
      {hasData ? (
        <ResponsiveContainer width="100%" height={100}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.5} />
                <stop offset="95%" stopColor={color} stopOpacity={0.02} />
              </linearGradient>
              {secondary && (
                <linearGradient id={secondary.gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={secondary.color} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={secondary.color} stopOpacity={0.02} />
                </linearGradient>
              )}
            </defs>
            <XAxis dataKey="time" hide />
            <YAxis domain={[0, 'auto']} hide />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(10, 10, 10, 0.95)',
                border: `1px solid ${color}33`,
                borderRadius: '8px',
                fontSize: '11px',
                padding: '8px 12px',
                boxShadow: `0 4px 20px ${color}33`,
                fontFamily: 'JetBrains Mono, monospace',
              }}
              itemStyle={{ color }}
              formatter={(value: number) => [formatter ? formatter(value) : `${value}%`, title]}
              labelStyle={{ display: 'none' }}
            />
            <Area
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              fill={`url(#${gradientId})`}
              dot={false}
              activeDot={{ r: 5, strokeWidth: 0, fill: color }}
              animationDuration={500}
            />
            {secondary && (
              <Area
                type="monotone"
                dataKey={secondary.key}
                stroke={secondary.color}
                strokeWidth={2}
                fill={`url(#${secondary.gradientId})`}
                dot={false}
                activeDot={{ r: 5, strokeWidth: 0, fill: secondary.color }}
                animationDuration={500}
                name={secondary.name}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-[100px] flex items-center justify-center">
          <div className="flex items-center gap-2 text-jarvis-text-muted">
            <div className="h-2 w-2 rounded-full bg-current animate-live-pulse" />
            <span className="text-xs font-mono">Collecting data...</span>
          </div>
        </div>
      )}
    </div>
  )
}

export function SystemCharts({ cpuData, memData, diskData = [], netData = [] }: SystemChartsProps) {
  const data = cpuData.map((cpu, i) => ({
    time: i,
    cpu: Math.round(cpu * 10) / 10,
    mem: Math.round((memData[i] ?? 0) * 10) / 10,
    disk: Math.round((diskData[i] ?? 0) * 10) / 10,
    netSent: Math.round((netData[i]?.sent ?? 0) / 1024 / 1024 * 10) / 10,
    netRecv: Math.round((netData[i]?.recv ?? 0) / 1024 / 1024 * 10) / 10,
  }))

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <ChartCard
        title="CPU Load"
        color={CHART_COLORS.cpu}
        gradientId="cpuGrad"
        dataKey="cpu"
        data={data}
      />
      <ChartCard
        title="Memory Usage"
        color={CHART_COLORS.mem}
        gradientId="memGrad"
        dataKey="mem"
        data={data}
      />
      <ChartCard
        title="Disk Activity"
        color={CHART_COLORS.disk}
        gradientId="diskGrad"
        dataKey="disk"
        data={data}
      />
      <ChartCard
        title="Network I/O"
        color={CHART_COLORS.netSent}
        gradientId="netSentGrad"
        dataKey="netSent"
        data={data}
        formatter={(v) => `${v} MB`}
        secondary={{
          key: 'netRecv',
          color: CHART_COLORS.netRecv,
          gradientId: 'netRecvGrad',
          name: 'Recv',
        }}
      />
    </div>
  )
}
