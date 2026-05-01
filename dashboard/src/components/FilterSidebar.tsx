import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import {
  CATEGORY_COLORS,
  LAYER_COLORS,
  ERA_COLORS,
  type RepoNode,
} from '@/lib/graph-data'

interface FilterSidebarProps {
  open: boolean
  onClose: () => void
  repos: RepoNode[]
  filters: {
    categories: string[]
    layers: string[]
    eras: string[]
    languages: string[]
    minStars: number
    maxStars: number
  }
  onFiltersChange: (f: FilterSidebarProps['filters']) => void
}

export default function FilterSidebar({
  open,
  onClose,
  repos,
  filters,
  onFiltersChange,
}: FilterSidebarProps) {
  const categories = Object.keys(CATEGORY_COLORS)
  const layers = Object.keys(LAYER_COLORS)
  const eras = Object.keys(ERA_COLORS)
  const languages = Array.from(new Set(repos.map((r) => r.language).filter(Boolean)))

  const hasActive =
    filters.categories.length > 0 ||
    filters.layers.length > 0 ||
    filters.eras.length > 0 ||
    filters.languages.length > 0 ||
    filters.minStars > 0 ||
    filters.maxStars < 210000

  function toggle<T>(arr: T[], val: T) {
    return arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val]
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <div
            className="fixed inset-0 bg-black/40 z-40 lg:hidden"
            onClick={onClose}
          />
          <motion.div
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ duration: 0.4, ease: [0.85, 0, 0.15, 1] }}
            className="fixed left-0 top-16 bottom-0 w-[280px] z-50 overflow-y-auto"
            style={{
              background: 'rgba(10, 10, 18, 0.85)',
              backdropFilter: 'blur(24px) saturate(1.2)',
              WebkitBackdropFilter: 'blur(24px) saturate(1.2)',
              borderRight: '1px solid rgba(255,255,255,0.08)',
              boxShadow: '8px 0 32px rgba(0,0,0,0.4)',
            }}
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-1">
                <h2 className="font-display font-medium text-[18px] text-text-primary">
                  Filters
                </h2>
                <button
                  onClick={onClose}
                  className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors"
                >
                  <X className="w-4 h-4 text-text-muted" />
                </button>
              </div>
              <p className="text-body-sm text-text-muted mb-4">
                Narrow the ecosystem
              </p>

              {hasActive && (
                <button
                  onClick={() =>
                    onFiltersChange({
                      categories: [],
                      layers: [],
                      eras: [],
                      languages: [],
                      minStars: 0,
                      maxStars: 210000,
                    })
                  }
                  className="text-[12px] text-accent-cyan hover:underline mb-4 block"
                >
                  Clear all
                </button>
              )}

              <div className="space-y-6">
                <div>
                  <h3 className="font-mono text-[11px] uppercase tracking-wider text-text-muted mb-3">
                    Category
                  </h3>
                  <div className="grid grid-cols-2 gap-2">
                    {categories.map((cat) => {
                      const active = filters.categories.includes(cat)
                      const count = repos.filter((r) => r.category === cat).length
                      const color = CATEGORY_COLORS[cat]?.fill || '#94a3b8'
                      return (
                        <button
                          key={cat}
                          onClick={() =>
                            onFiltersChange({
                              ...filters,
                              categories: toggle(filters.categories, cat),
                            })
                          }
                          className={`flex items-center gap-2 px-2 py-1.5 rounded-[6px] text-[12px] transition-all ${
                            active
                              ? 'text-white'
                              : 'text-text-secondary hover:text-text-primary bg-white/5 border border-white/10'
                          }`}
                          style={
                            active
                              ? { background: color, borderColor: color }
                              : {}
                          }
                        >
                          <span
                            className="w-2 h-2 rounded-full shrink-0"
                            style={{ background: color }}
                          />
                          <span className="truncate">{cat}</span>
                          <span className="ml-auto text-[10px] font-mono opacity-60">
                            {count}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div>
                  <h3 className="font-mono text-[11px] uppercase tracking-wider text-text-muted mb-3">
                    Layer
                  </h3>
                  <div className="flex flex-col gap-1.5">
                    {layers.map((layer) => {
                      const active = filters.layers.includes(layer)
                      const color = LAYER_COLORS[layer] || '#94a3b8'
                      return (
                        <button
                          key={layer}
                          onClick={() =>
                            onFiltersChange({
                              ...filters,
                              layers: toggle(filters.layers, layer),
                            })
                          }
                          className={`flex items-center gap-2 px-2 py-1.5 rounded-[6px] text-[12px] transition-all text-left ${
                            active
                              ? 'text-white bg-white/10'
                              : 'text-text-secondary hover:text-text-primary bg-white/5 border border-white/10'
                          }`}
                          style={
                            active
                              ? {
                                  background: `${color}33`,
                                  borderLeft: `4px solid ${color}`,
                                }
                              : { borderLeft: `4px solid ${color}44` }
                          }
                        >
                          {layer}
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div>
                  <h3 className="font-mono text-[11px] uppercase tracking-wider text-text-muted mb-3">
                    Era
                  </h3>
                  <div className="flex flex-col gap-1.5">
                    {eras.map((era) => {
                      const active = filters.eras.includes(era)
                      const color = ERA_COLORS[era]
                      const label =
                        era === 'trending'
                          ? 'Trending Now'
                          : era === 'recent'
                          ? 'Recent (2024-26)'
                          : 'Landmarks'
                      return (
                        <button
                          key={era}
                          onClick={() =>
                            onFiltersChange({
                              ...filters,
                              eras: toggle(filters.eras, era),
                            })
                          }
                          className={`flex items-center gap-2 px-2 py-1.5 rounded-[6px] text-[12px] transition-all text-left ${
                            active
                              ? 'text-white bg-white/10'
                              : 'text-text-secondary hover:text-text-primary bg-white/5 border border-white/10'
                          }`}
                        >
                          <span
                            className="w-2 h-2 rounded-full shrink-0"
                            style={{ background: color }}
                          />
                          {label}
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div>
                  <h3 className="font-mono text-[11px] uppercase tracking-wider text-text-muted mb-3">
                    Language
                  </h3>
                  <div className="flex flex-wrap gap-1.5">
                    {languages.slice(0, 10).map((lang) => {
                      const active = filters.languages.includes(lang)
                      return (
                        <button
                          key={lang}
                          onClick={() =>
                            onFiltersChange({
                              ...filters,
                              languages: toggle(filters.languages, lang),
                            })
                          }
                          className={`px-2 py-1 rounded-full text-[11px] transition-all ${
                            active
                              ? 'bg-accent-cyan text-text-inverse'
                              : 'bg-white/5 text-text-muted hover:text-text-secondary border border-white/10'
                          }`}
                        >
                          {lang}
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div>
                  <h3 className="font-mono text-[11px] uppercase tracking-wider text-text-muted mb-3">
                    Star Count
                  </h3>
                  <div className="px-1">
                    <input
                      type="range"
                      min={0}
                      max={210000}
                      step={1000}
                      value={filters.maxStars}
                      onChange={(e) =>
                        onFiltersChange({
                          ...filters,
                          maxStars: Number(e.target.value),
                        })
                      }
                      className="w-full accent-accent-cyan"
                    />
                    <div className="flex justify-between font-mono text-[11px] text-text-muted mt-1">
                      <span>0</span>
                      <span>{(filters.maxStars / 1000).toFixed(0)}K</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
