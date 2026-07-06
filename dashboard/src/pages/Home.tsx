import { useState, useEffect, useMemo, useCallback } from 'react'
import { motion } from 'framer-motion'
import HeroBar from '@/components/HeroBar'
import FilterSidebar from '@/components/FilterSidebar'
import DetailDrawer from '@/components/DetailDrawer'
import StatsDashboard from '@/components/StatsDashboard'
import PatternBar from '@/components/PatternBar'
import GraphCanvas from '@/components/graph/GraphCanvas'
import { TrendingPanel } from '@/components/discovery/TrendingPanel'
import {
  loadGraphData,
  type RepoNode,
  type GraphData,
} from '@/lib/graph-data'

const PATTERN_REPOS: Record<string, string[]> = {
  'agent-ecosystem': [
    'anthropics/skills',
    'NousResearch/hermes-agent',
    'bytedance/deer-flow',
    'FoundationAgents/OpenManus',
    '666ghj/MiroFish',
    'openclaw/openclaw',
    'n8n-io/n8n',
    'karpathy/autoresearch',
    'langchain-ai/langchain',
    'openai/swarm',
    'paperclipai/paperclip',
    'code-yeongyu/oh-my-openagent',
    'koala73/worldmonitor',
    'simular-ai/Agent-S',
    'kagent-dev/kagent',
    'google-gemini/gemini-cli',
    'sansan0/TrendRadar',
  ],
  'local-ai': [
    'ollama/ollama',
    'openclaw/openclaw',
    'secret-ai-labs/awesome-local-llm',
    'karpathy/nanochat',
    'gensyn-ai/codeassist',
    'anomalyco/opencode',
    'ComposioHQ/awesome-codex-skills',
    'ComposioHQ/awesome-claude-skills',
  ],
  'multimodal': [
    'MeiGen-AI/MultiTalk',
    'OpenGVLab/V2PE',
    'yunncheng/MMRL',
    'Wings-Of-Disaster/VaLiK',
    'AUTOMATIC1111/stable-diffusion-webui',
    'hustvl/DiffusionDrive',
    'hustvl/DiG',
    'Picsart-AI-Research/StreamingT2V',
    'microsoft/VibeVoice',
    'resemble-ai/chatterbox',
    'KoljaB/RealtimeSTT',
  ],
  'training-inference': [
    'tensorflow/tensorflow',
    'pytorch/pytorch',
    'huggingface/transformers',
    'volcengine/verl',
    'karpathy/nanochat',
    'weizhepei/InstructRAG',
    'alexzhang13/rlm',
    'hustvl/DiG',
    'luccachiang/robots-pretrain-robots',
  ],
}

export default function Home() {
  const [data, setData] = useState<GraphData | null>(null)
  const [viewMode, setViewMode] = useState<'category' | 'layer' | 'era'>('category')
  const [filterOpen, setFilterOpen] = useState(false)
  const [selectedRepo, setSelectedRepo] = useState<RepoNode | null>(null)
  const [hoveredRepo, setHoveredRepo] = useState<string | null>(null)
  const [activePattern, setActivePattern] = useState<string | null>(null)
  const [filters, setFilters] = useState({
    categories: [] as string[],
    layers: [] as string[],
    eras: [] as string[],
    languages: [] as string[],
    minStars: 0,
    maxStars: 210000,
  })

  useEffect(() => {
    loadGraphData().then(setData)
  }, [])

  const filteredNodes = useMemo(() => {
    if (!data) return []
    return data.nodes.filter((n) => {
      if (filters.categories.length > 0 && !filters.categories.includes(n.category))
        return false
      if (filters.layers.length > 0 && !filters.layers.includes(n.layer)) return false
      if (filters.eras.length > 0 && !filters.eras.includes(n.era)) return false
      if (filters.languages.length > 0 && !filters.languages.includes(n.language))
        return false
      if (n.stars < filters.minStars || n.stars > filters.maxStars) return false
      return true
    })
  }, [data, filters])

  const filteredLinks = useMemo(() => {
    if (!data) return []
    const nodeIds = new Set(filteredNodes.map((n) => n.id))
    return data.links.filter(
      (l) => {
        const s = typeof l.source === 'string' ? l.source : l.source.id
        const t = typeof l.target === 'string' ? l.target : l.target.id
        return nodeIds.has(s) && nodeIds.has(t)
      }
    )
  }, [data, filteredNodes])

  const patternNodes = useMemo(() => {
    if (!activePattern) return new Set<string>()
    const ids = PATTERN_REPOS[activePattern] || []
    return new Set(ids)
  }, [activePattern])

  const handlePatternToggle = useCallback((pattern: string) => {
    setActivePattern((prev) => (prev === pattern ? null : pattern))
  }, [])

  const handleHighlight = useCallback((repoId: string) => {
    setHoveredRepo(repoId)
    const repo = data?.nodes.find((n) => n.id === repoId) || null
    setSelectedRepo(repo)
  }, [data])

  const handleOpenRepo = useCallback((repoId: string) => {
    const repo = data?.nodes.find((n) => n.id === repoId) || null
    setSelectedRepo(repo)
  }, [data])

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-[100dvh]">
        <div className="text-text-muted font-mono text-[14px] animate-pulse">
          Loading graph data...
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="relative min-h-[100dvh] overflow-hidden"
    >
      <HeroBar
        repos={data.nodes}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onFilterToggle={() => setFilterOpen((v) => !v)}
        onSearchSelect={(repo) => {
          setSelectedRepo(repo)
          setHoveredRepo(repo.id)
        }}
      />

      <PatternBar activePattern={activePattern} onPatternToggle={handlePatternToggle} />

      <GraphCanvas
        nodes={filteredNodes}
        links={filteredLinks}
        viewMode={viewMode}
        selectedRepo={selectedRepo}
        hoveredRepo={hoveredRepo}
        onHover={setHoveredRepo}
        onClick={setSelectedRepo}
        activePattern={activePattern}
        patternNodes={patternNodes}
      />

      <FilterSidebar
        open={filterOpen}
        onClose={() => setFilterOpen(false)}
        repos={data.nodes}
        filters={filters}
        onFiltersChange={setFilters}
      />

      <DetailDrawer
        repo={selectedRepo}
        links={data.links}
        repos={data.nodes}
        onClose={() => setSelectedRepo(null)}
        onHighlight={handleHighlight}
        onOpenRepo={handleOpenRepo}
      />

      <StatsDashboard />

      <aside className="fixed top-32 right-4 z-30 w-80 max-h-[calc(100dvh-9rem)] overflow-y-auto p-4">
        <TrendingPanel />
      </aside>

      {/* Tooltip */}
      {hoveredRepo && !selectedRepo && (
        <div className="fixed z-[35] pointer-events-none hidden lg:block">
          <TooltipContent
            repo={data.nodes.find((n) => n.id === hoveredRepo)!}
          />
        </div>
      )}
    </motion.div>
  )
}

function TooltipContent({ repo }: { repo: RepoNode }) {
  if (!repo) return null
  return (
    <div
      className="glass-panel rounded-[10px] p-3 max-w-[280px]"
      style={{ transform: 'translate(16px, 16px)' }}
    >
      <div className="text-[14px] font-medium text-text-primary mb-1">
        {repo.name}
      </div>
      <div className="text-[11px] font-mono text-text-muted mb-1">
        {repo.stars.toLocaleString()} ★ · {repo.category} · {repo.language}
      </div>
      <div className="text-[13px] text-text-secondary leading-[1.5] line-clamp-2">
        {repo.description}
      </div>
    </div>
  )
}
