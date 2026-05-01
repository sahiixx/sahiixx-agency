import { motion } from 'framer-motion'
import { Database, GitBranch, Zap, Star } from 'lucide-react'

export default function StatsDashboard() {
  const cards = [
    {
      icon: Database,
      color: '#00d4ff',
      value: '113',
      label: 'Repositories',
      detail: '49 trending · 29 recent · 35 landmarks',
    },
    {
      icon: GitBranch,
      color: '#8b5cf6',
      value: '130',
      label: 'Connections',
      detail: '8 relationship types mapped',
    },
    {
      icon: Zap,
      color: '#ef4444',
      value: 'Agents',
      label: 'Hottest Category · 21 repos',
      detail: '+12 this week',
      detailColor: '#22c55e',
    },
    {
      icon: Star,
      color: '#f59e0b',
      value: 'OpenClaw',
      label: '210K stars · Trending #1',
      isTextValue: true,
      glow: true,
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.6 }}
      className="fixed bottom-4 left-4 z-30 flex flex-wrap gap-3 max-w-[640px]"
    >
      {cards.map((card, i) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.5,
            delay: 0.6 + i * 0.1,
            ease: [0.16, 1, 0.3, 1] as [number, number, number, number],
          }}
          className="glass-panel rounded-[16px] p-4 min-w-[160px] transition-transform hover:scale-[1.03] cursor-default"
          style={card.glow ? { borderColor: `${card.color}40` } : {}}
        >
          <div className="flex items-center gap-2 mb-2">
            <card.icon className="w-4 h-4" style={{ color: card.color }} />
            <span className="font-mono text-[11px] uppercase tracking-wider text-text-muted">
              {card.label}
            </span>
          </div>
          <div
            className={`font-display font-bold ${
              card.isTextValue ? 'text-[22px]' : 'text-[32px]'
            } text-text-primary leading-[1]`}
          >
            {card.value}
          </div>
          {card.detail && (
            <div
              className="font-mono text-[11px] mt-1.5"
              style={{ color: card.detailColor || 'var(--text-muted)' }}
            >
              {card.detail}
            </div>
          )}
        </motion.div>
      ))}
    </motion.div>
  )
}
