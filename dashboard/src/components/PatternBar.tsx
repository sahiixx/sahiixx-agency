import { motion } from 'framer-motion'

interface PatternBarProps {
  activePattern: string | null
  onPatternToggle: (pattern: string) => void
}

const PATTERNS = [
  { id: 'agent-ecosystem', label: 'Agent Ecosystem', color: '#ef4444' },
  { id: 'local-ai', label: 'Local AI Stack', color: '#22c55e' },
  { id: 'multimodal', label: 'Multimodal Pipeline', color: '#a855f7' },
  { id: 'training-inference', label: 'Training → Inference', color: '#00d4ff' },
]

export default function PatternBar({ activePattern, onPatternToggle }: PatternBarProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.8 }}
      className="fixed top-[120px] left-1/2 -translate-x-1/2 z-30 flex items-center gap-2"
    >
      {PATTERNS.map((p) => {
        const active = activePattern === p.id
        return (
          <button
            key={p.id}
            onClick={() => onPatternToggle(p.id)}
            className={`glass-tag h-9 px-4 flex items-center gap-2 text-[13px] font-medium transition-all ${
              active
                ? 'text-white border-opacity-40'
                : 'text-text-secondary hover:text-text-primary'
            }`}
            style={
              active
                ? {
                    background: `${p.color}33`,
                    borderColor: `${p.color}80`,
                    boxShadow: `0 0 12px ${p.color}40`,
                  }
                : {}
            }
          >
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ background: p.color }}
            />
            {p.label}
          </button>
        )
      })}
      {activePattern && (
        <button
          onClick={() => onPatternToggle(activePattern)}
          className="glass-tag h-9 px-3 text-[12px] text-text-muted hover:text-text-primary transition-colors"
        >
          Reset View
        </button>
      )}
    </motion.div>
  )
}
