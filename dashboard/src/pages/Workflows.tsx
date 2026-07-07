import { useEffect, useState } from 'react'
import { Play, Plus, Trash2, Workflow } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { toast } from 'sonner'

interface WorkflowDefinition {
  id: string
  name: string
  description?: string
  trigger: string
  steps: Array<{
    id: string
    name: string
    action: string
    target?: string
    intent_template?: string
    next_on_success?: string
    next_on_failure?: string
    payload?: Record<string, unknown>
  }>
  enabled: boolean
}

interface WorkflowInstance {
  id: string
  workflow_id: string
  status: string
  current_step_id?: string
  created_at: string
  completed_at?: string
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<WorkflowDefinition[]>([])
  const [instances, setInstances] = useState<Record<string, WorkflowInstance[]>>({})
  const [loading, setLoading] = useState(false)
  const [newJson, setNewJson] = useState('')

  const fetchWorkflows = async () => {
    try {
      const res = await fetch('/api/workflows')
      if (!res.ok) throw new Error('Failed to fetch workflows')
      const data = await res.json()
      setWorkflows(data)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load workflows')
    }
  }

  const fetchInstances = async (workflowId: string) => {
    try {
      const res = await fetch(`/api/workflows/${workflowId}/instances`)
      if (!res.ok) return
      const data = await res.json()
      setInstances((prev) => ({ ...prev, [workflowId]: data }))
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    fetchWorkflows()
  }, [])

  const runWorkflow = async (workflowId: string) => {
    setLoading(true)
    try {
      const res = await fetch(`/api/workflows/${workflowId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context: {} }),
      })
      if (!res.ok) throw new Error('Failed to run workflow')
      const data = await res.json()
      toast.success(`Workflow ${workflowId} finished: ${data.status}`)
      fetchInstances(workflowId)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to run workflow')
    } finally {
      setLoading(false)
    }
  }

  const createWorkflow = async () => {
    try {
      const payload = JSON.parse(newJson)
      const res = await fetch('/api/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error('Failed to create workflow')
      toast.success('Workflow created')
      setNewJson('')
      fetchWorkflows()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Invalid JSON')
    }
  }

  const deleteWorkflow = async (workflowId: string) => {
    try {
      const res = await fetch(`/api/workflows/${workflowId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete workflow')
      toast.success('Workflow deleted')
      fetchWorkflows()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete workflow')
    }
  }

  return (
    <div className="min-h-[100dvh] px-4 py-6 md:px-8 md:py-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Workflow className="h-6 w-6 text-accent-cyan" />
            <h1 className="font-display text-2xl font-bold text-text-primary">Workflows</h1>
          </div>
          <div className="text-sm text-text-secondary">{workflows.length} definitions</div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Create Workflow</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              placeholder='{"id":"my-wf","name":"My Workflow","trigger":"manual","steps":[{"id":"s1","name":"Notify","action":"notify","payload":{"channel":"sse","title":"Hello","body":"World"}}]}'
              value={newJson}
              onChange={(e) => setNewJson(e.target.value)}
              rows={4}
            />
            <Button onClick={createWorkflow} disabled={!newJson.trim()} className="gap-2">
              <Plus className="h-4 w-4" /> Create
            </Button>
          </CardContent>
        </Card>

        <div className="grid gap-4">
          {workflows.map((wf) => (
            <Card key={wf.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{wf.name}</CardTitle>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => fetchInstances(wf.id)}
                    >
                      Instances
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => runWorkflow(wf.id)}
                      disabled={loading}
                      className="gap-1"
                    >
                      <Play className="h-3.5 w-3.5" /> Run
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => deleteWorkflow(wf.id)}
                      className="text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-3 text-sm text-text-secondary">
                  <span className="font-mono text-xs bg-muted px-2 py-1 rounded">{wf.id}</span>
                  <span>Trigger: {wf.trigger}</span>
                  <span>Steps: {wf.steps.length}</span>
                  <span>{wf.enabled ? 'Enabled' : 'Disabled'}</span>
                </div>
                {wf.description && <p className="text-sm text-text-secondary">{wf.description}</p>}
                <div className="space-y-1">
                  {wf.steps.map((step) => (
                    <div key={step.id} className="text-sm border-l-2 border-accent-cyan pl-3 py-1">
                      <span className="font-medium">{step.name}</span>
                      <span className="text-text-secondary ml-2">({step.action})</span>
                    </div>
                  ))}
                </div>

                {instances[wf.id] && instances[wf.id].length > 0 && (
                  <div className="pt-2 border-t">
                    <div className="text-xs font-medium text-text-secondary mb-2">Recent Instances</div>
                    <div className="space-y-1">
                      {instances[wf.id].slice(0, 5).map((inst) => (
                        <div key={inst.id} className="flex items-center justify-between text-sm">
                          <span className="font-mono text-xs">{inst.id}</span>
                          <span className="text-xs px-2 py-0.5 rounded bg-muted">{inst.status}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
