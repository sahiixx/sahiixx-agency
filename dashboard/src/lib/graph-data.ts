export interface RepoNode {
  id: string
  name: string
  stars: number
  category: string
  era: string
  layer: string
  url: string
  description: string
  language: string
  why: string
}

export interface LinkData {
  source: string | RepoNode
  target: string | RepoNode
  type: string
  strength: number
}

export interface GraphData {
  nodes: RepoNode[]
  links: LinkData[]
  categories: string[]
  layers: string[]
  eras: string[]
  stats: {
    totalRepos: number
    totalConnections: number
    trendingCount: number
    [key: string]: unknown
  }
}

export const CATEGORY_COLORS: Record<string, { fill: string; glow: string }> = {
  LLMs: { fill: '#3b82f6', glow: 'rgba(59,130,246,0.4)' },
  Agents: { fill: '#ef4444', glow: 'rgba(239,68,68,0.4)' },
  CodeAI: { fill: '#22c55e', glow: 'rgba(34,197,94,0.4)' },
  Multimodal: { fill: '#a855f7', glow: 'rgba(168,85,247,0.4)' },
  'Diffusion/GenAI': { fill: '#ec4899', glow: 'rgba(236,72,153,0.4)' },
  'Infrastructure/Tools': { fill: '#06b6d4', glow: 'rgba(6,182,212,0.4)' },
  Frameworks: { fill: '#f59e0b', glow: 'rgba(245,158,11,0.4)' },
  Data: { fill: '#10b981', glow: 'rgba(16,185,129,0.4)' },
  Audio: { fill: '#f97316', glow: 'rgba(249,115,22,0.4)' },
  Robotics: { fill: '#6366f1', glow: 'rgba(99,102,241,0.4)' },
  Other: { fill: '#94a3b8', glow: 'rgba(148,163,184,0.4)' },
  // Agency-specific categories
  AgentFramework: { fill: '#ef4444', glow: 'rgba(239,68,68,0.4)' },
  VoiceAi: { fill: '#f97316', glow: 'rgba(249,115,22,0.4)' },
  RealEstate: { fill: '#22c55e', glow: 'rgba(34,197,94,0.4)' },
  Security: { fill: '#dc2626', glow: 'rgba(220,38,38,0.4)' },
  McpTool: { fill: '#06b6d4', glow: 'rgba(6,182,212,0.4)' },
  Cookbook: { fill: '#f59e0b', glow: 'rgba(245,158,11,0.4)' },
  OsPlatform: { fill: '#6366f1', glow: 'rgba(99,102,241,0.4)' },
  Infrastructure: { fill: '#0ea5e9', glow: 'rgba(14,165,233,0.4)' },
  Uncategorized: { fill: '#94a3b8', glow: 'rgba(148,163,184,0.4)' },
}

export const LAYER_COLORS: Record<string, string> = {
  Compute: '#0ea5e9',
  Model: '#6366f1',
  Framework: '#8b5cf6',
  Agent: '#ec4899',
  Tool: '#06b6d4',
  Application: '#22c55e',
  Data: '#10b981',
  Interface: '#f59e0b',
}

export const EDGE_STYLES: Record<string, { color: string; dash: string; width: number }> = {
  depends_on: { color: '#3b82f6', dash: '0', width: 2 },
  built_on: { color: '#8b5cf6', dash: '4 2', width: 2 },
  uses: { color: '#06b6d4', dash: '3 3', width: 1.5 },
  inspired_by: { color: '#f59e0b', dash: '1 3', width: 1.5 },
  extends: { color: '#22c55e', dash: '0', width: 2 },
  competes_with: { color: '#ef4444', dash: '4 2', width: 2 },
  complements: { color: '#94a3b8', dash: '1 2', width: 1 },
  alternative_to: { color: '#e879f9', dash: '4 1 1 1', width: 1.5 },
}

export const ERA_COLORS: Record<string, string> = {
  trending: '#ef4444',
  recent: '#f59e0b',
  landmark: '#22c55e',
}

export function nodeRadius(stars: number) {
  const min = 6
  const max = 28
  const scale = Math.sqrt(stars || 0) * 0.15
  return Math.min(max, Math.max(min, scale))
}

export function formatStars(n: number) {
  if (n >= 100000) return `${(n / 1000).toFixed(0)}K`
  if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/, '')}K`
  return `${n}`
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8082'

export async function loadGraphData(): Promise<GraphData> {
  try {
    const res = await fetch(`${API_BASE}/dashboard/graph-data`)
    if (!res.ok) throw new Error('API fetch failed')
    return res.json()
  } catch {
    // Fallback to static data if API is unavailable
    const res = await fetch('/graph_data.json')
    return res.json()
  }
}
