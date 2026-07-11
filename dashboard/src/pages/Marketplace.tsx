import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Package, Star, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'

interface RepoNode {
  id: string
  name: string
  full_name: string
  description: string | null
  category: string
  stars: number
  risk_level: string
  capabilities: string[]
}

interface MarketplaceListing {
  module: RepoNode
  install_count: number
  average_rating: number
  rating_count: number
  installed_globally: boolean
  enabled_projects: string[]
}

const CATEGORIES = [
  { value: '_all', label: 'All categories' },
  { value: 'agent_framework', label: 'Agent Framework' },
  { value: 'voice_ai', label: 'Voice AI' },
  { value: 'security', label: 'Security' },
  { value: 'career', label: 'Career' },
  { value: 'content_media', label: 'Content Media' },
  { value: 'knowledge', label: 'Knowledge' },
  { value: 'cookbook', label: 'Cookbook' },
]

export default function MarketplacePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const projectId = searchParams.get('project_id') || ''
  const [listings, setListings] = useState<MarketplaceListing[]>([])
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [projectInput, setProjectInput] = useState(projectId)
  const [loading, setLoading] = useState(false)
  const [actionId, setActionId] = useState<string | null>(null)

  const fetchListings = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (projectId) params.set('project_id', projectId)
      if (query) params.set('q', query)
      if (category) params.set('category', category)
      const res = await fetch(`/api/marketplace?${params.toString()}`)
      if (!res.ok) throw new Error('Failed to fetch marketplace listings')
      const data = (await res.json()) as MarketplaceListing[]
      setListings(data)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load marketplace')
    } finally {
      setLoading(false)
    }
  }, [projectId, query, category])

  useEffect(() => {
    fetchListings()
  }, [fetchListings])

  useEffect(() => {
    setProjectInput(projectId)
  }, [projectId])

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        if (projectInput) {
          next.set('project_id', projectInput)
        } else {
          next.delete('project_id')
        }
        return next
      })
    }, 300)
    return () => clearTimeout(timer)
  }, [projectInput, setSearchParams])

  const install = async (moduleId: string) => {
    setActionId(moduleId)
    try {
      const res = await fetch(`/api/marketplace/${encodeURIComponent(moduleId)}/install`, { method: 'POST' })
      if (!res.ok) throw new Error('Install failed')
      toast.success('Module installed')
      await fetchListings()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Install failed')
    } finally {
      setActionId(null)
    }
  }

  const enable = async (moduleId: string) => {
    if (!projectId) {
      toast.error('Select a project to enable this module')
      return
    }
    setActionId(moduleId)
    try {
      const res = await fetch(`/api/marketplace/${moduleId}/enable?project_id=${encodeURIComponent(projectId)}`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error('Enable failed')
      toast.success('Module enabled for project')
      await fetchListings()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Enable failed')
    } finally {
      setActionId(null)
    }
  }

  const disable = async (moduleId: string) => {
    if (!projectId) {
      toast.error('Select a project to disable this module')
      return
    }
    setActionId(moduleId)
    try {
      const res = await fetch(`/api/marketplace/${moduleId}/disable?project_id=${encodeURIComponent(projectId)}`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error('Disable failed')
      toast.success('Module disabled for project')
      await fetchListings()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Disable failed')
    } finally {
      setActionId(null)
    }
  }

  return (
    <div className="min-h-[100dvh] px-4 py-6 md:px-8 md:py-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Package className="h-6 w-6 text-accent-cyan" />
            <h1 className="font-display text-2xl font-bold text-text-primary">Module Marketplace</h1>
          </div>
          <div className="text-sm text-text-secondary">{listings.length} modules</div>
        </div>

        <div className="flex flex-col md:flex-row gap-4">
          <Input
            type="text"
            placeholder="Search modules..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="md:max-w-sm"
          />
          <Select value={category || '_all'} onValueChange={(val) => setCategory(val === '_all' ? '' : val)}>
            <SelectTrigger className="md:w-48">
              <SelectValue placeholder="All categories" />
            </SelectTrigger>
            <SelectContent>
              {CATEGORIES.map((cat) => (
                <SelectItem key={cat.value} value={cat.value}>
                  {cat.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            type="text"
            placeholder="Project ID (optional)"
            value={projectInput}
            onChange={(e) => setProjectInput(e.target.value)}
            className="md:max-w-sm md:ml-auto"
          />
        </div>

        {loading && listings.length === 0 && (
          <div className="text-sm text-text-secondary">Loading marketplace...</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {listings.map((listing) => (
            <Card key={listing.module.id} className="flex flex-col">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{listing.module.name}</CardTitle>
              </CardHeader>
              <CardContent className="flex-1 space-y-3">
                <p className="text-sm text-text-secondary">
                  {listing.module.description || 'No description'}
                </p>
                <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
                  <Badge variant="secondary">{listing.module.category}</Badge>
                  <span className="flex items-center gap-1">
                    <Star className="h-3 w-3" /> {listing.module.stars}
                  </span>
                  <span className="flex items-center gap-1">
                    <Download className="h-3 w-3" /> {listing.install_count}
                  </span>
                  <span>
                    {listing.average_rating.toFixed(1)} ({listing.rating_count})
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {listing.module.capabilities.slice(0, 5).map((cap) => (
                    <Badge key={cap} variant="outline" className="text-xs">
                      {cap}
                    </Badge>
                  ))}
                </div>
                <div className="pt-2">
                  {!listing.installed_globally ? (
                    <Button
                      size="sm"
                      onClick={() => install(listing.module.id)}
                      disabled={actionId === listing.module.id}
                    >
                      Install
                    </Button>
                  ) : projectId && !listing.enabled_projects.includes(projectId) ? (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => enable(listing.module.id)}
                      disabled={actionId === listing.module.id}
                    >
                      Enable
                    </Button>
                  ) : projectId ? (
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => disable(listing.module.id)}
                      disabled={actionId === listing.module.id}
                    >
                      Disable
                    </Button>
                  ) : (
                    <span className="text-xs text-text-muted">Installed globally</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {!loading && listings.length === 0 && (
          <div className="text-center py-12 text-text-secondary">
            No marketplace modules found.
          </div>
        )}
      </div>
    </div>
  )
}
