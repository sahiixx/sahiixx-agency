import { useEffect, useState } from 'react'
import { Play, Wrench, Loader2, AlertCircle, CheckCircle2, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { toast } from 'sonner'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8082'

interface Skill {
  id: string
  name: string
  description?: string
  tags?: string[]
  category?: string
  version?: string
  [key: string]: unknown
}

interface SkillRunResponse {
  success?: boolean
  result?: unknown
  error?: string
  [key: string]: unknown
}

async function loadSkills(): Promise<Skill[]> {
  const res = await fetch(`${API_BASE}/api/skills`)
  if (!res.ok) throw new Error(`Failed to fetch skills: ${res.status}`)
  const json = await res.json()
  return json.skills ?? []
}

async function runSkill(skillId: string, payload: Record<string, unknown>): Promise<SkillRunResponse> {
  const res = await fetch(`${API_BASE}/api/skills/${skillId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Run failed: ${res.status}`)
  return res.json()
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(false)
  const [runningId, setRunningId] = useState<string | null>(null)
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null)
  const [payloadJson, setPayloadJson] = useState('{}')
  const [result, setResult] = useState<SkillRunResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)

  const fetchSkills = async () => {
    setLoading(true)
    try {
      const data = await loadSkills()
      setSkills(data)
      setError(null)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load skills'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSkills()
  }, [])

  const openRunDialog = (skill: Skill) => {
    setSelectedSkill(skill)
    setPayloadJson('{}')
    setResult(null)
    setError(null)
    setOpen(true)
  }

  const handleRun = async () => {
    if (!selectedSkill) return
    let payload: Record<string, unknown>
    try {
      payload = JSON.parse(payloadJson)
    } catch {
      toast.error('Invalid JSON payload')
      return
    }

    setRunningId(selectedSkill.id)
    setResult(null)
    setError(null)
    try {
      const data = await runSkill(selectedSkill.id, payload)
      const displayResult = data.result !== undefined ? data.result : data
      setResult(displayResult as SkillRunResponse)
      toast.success(`Skill "${selectedSkill.name}" ran successfully`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to run skill'
      setError(msg)
      toast.error(msg)
    } finally {
      setRunningId(null)
    }
  }

  return (
    <div className="min-h-[100dvh] px-4 py-6 md:px-8 md:py-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Wrench className="h-6 w-6 text-accent-cyan" />
            <h1 className="font-display text-2xl font-bold text-text-primary">GCC Outbound Skills</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-text-secondary">{skills.length} skills</span>
            <Button variant="outline" onClick={fetchSkills} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Refresh'}
            </Button>
          </div>
        </div>

        {error && !open && (
          <div className="flex items-center gap-3 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {skills.map((skill) => (
            <Card key={skill.id} className="glass-panel transition-colors hover:border-accent-cyan/40">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <CardTitle className="text-base truncate">{skill.name}</CardTitle>
                    <CardDescription className="text-xs font-mono mt-1">{skill.id}</CardDescription>
                  </div>
                  <Dialog open={open && selectedSkill?.id === skill.id} onOpenChange={setOpen}>
                    <DialogTrigger asChild>
                      <Button size="sm" onClick={() => openRunDialog(skill)} className="gap-1 shrink-0">
                        <Play className="h-3.5 w-3.5" /> Run
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-xl">
                      <DialogHeader>
                        <DialogTitle>Run {selectedSkill?.name}</DialogTitle>
                        <DialogDescription>
                          POST /api/skills/{selectedSkill?.id}/run with the JSON payload below.
                        </DialogDescription>
                      </DialogHeader>

                      <div className="space-y-3">
                        <div>
                          <label className="text-sm font-medium text-text-secondary mb-1.5 block">JSON Payload</label>
                          <Textarea
                            value={payloadJson}
                            onChange={(e) => setPayloadJson(e.target.value)}
                            rows={8}
                            className="font-mono text-sm glass-input"
                            placeholder='{"key": "value"}'
                          />
                        </div>

                        {result && (
                          <div className="rounded-lg border border-accent-green/30 bg-accent-green/10 p-3">
                            <div className="flex items-center gap-2 text-sm font-medium text-accent-green mb-2">
                              <CheckCircle2 className="h-4 w-4" /> Result
                            </div>
                            <pre className="text-xs font-mono text-text-secondary overflow-auto max-h-48 p-2 rounded bg-black/20">
                              {JSON.stringify(result, null, 2)}
                            </pre>
                          </div>
                        )}

                        {error && open && (
                          <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3">
                            <div className="flex items-center gap-2 text-sm font-medium text-destructive mb-2">
                              <XCircle className="h-4 w-4" /> Error
                            </div>
                            <p className="text-xs font-mono text-text-secondary">{error}</p>
                          </div>
                        )}
                      </div>

                      <DialogFooter className="gap-2">
                        <DialogClose asChild>
                          <Button variant="outline">Close</Button>
                        </DialogClose>
                        <Button onClick={handleRun} disabled={runningId === selectedSkill?.id} className="gap-1">
                          {runningId === selectedSkill?.id && <Loader2 className="h-4 w-4 animate-spin" />}
                          <Play className="h-4 w-4" /> Run Skill
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {skill.category && (
                  <Badge variant="secondary" className="text-xs">
                    {skill.category}
                  </Badge>
                )}
                {skill.description && (
                  <p className="text-sm text-text-secondary line-clamp-3">{skill.description}</p>
                )}
                {skill.tags && skill.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {skill.tags.map((tag) => (
                      <span key={tag} className="glass-tag px-2.5 py-0.5 text-[11px] text-text-secondary">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                {skill.version && (
                  <div className="text-xs text-text-muted font-mono">v{skill.version}</div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        {!loading && skills.length === 0 && !error && (
          <div className="text-center py-16 text-text-secondary">
            <Wrench className="h-10 w-10 mx-auto mb-3 opacity-50" />
            <p>No skills available. The API may not be running.</p>
          </div>
        )}
      </div>
    </div>
  )
}
