import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Loader2, Send } from 'lucide-react'

interface Provider {
  id: string
  name: string
  default_model: string
  base_url: string
  env_var: string | null
  ready: boolean
}

interface Usage {
  input_tokens: number
  output_tokens: number
  total_tokens: number
}

interface LLMResponse {
  provider: string
  model: string
  content: string
  usage: Usage
  cost_usd: number | null
  latency_ms: number
}

interface CostSummary {
  total_calls: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  total_cost_usd: number
  cost_estimated: boolean
  by_provider: Record<string, { calls: number; tokens: number; cost_usd: number }>
  by_model: Record<string, { calls: number; tokens: number; cost_usd: number }>
  calls: Array<{
    id: string
    provider: string
    model: string
    input_tokens: number
    output_tokens: number
    total_tokens: number
    cost_usd: number | null
    latency_ms: number
    created_at: string
  }>
}

export default function LLMPage() {
  const [providers, setProviders] = useState<Provider[]>([])
  const [summary, setSummary] = useState<CostSummary | null>(null)
  const [prompt, setPrompt] = useState('')
  const [provider, setProvider] = useState('')
  const [model, setModel] = useState('')
  const [loadingProviders, setLoadingProviders] = useState(true)
  const [loadingCosts, setLoadingCosts] = useState(true)
  const [sending, setSending] = useState(false)
  const [response, setResponse] = useState<LLMResponse | null>(null)

  useEffect(() => {
    fetch('/llm/providers')
      .then((r) => r.json())
      .then((data) => {
        setProviders(data)
        setLoadingProviders(false)
      })
      .catch(() => {
        toast.error('Failed to load LLM providers')
        setLoadingProviders(false)
      })

    fetch('/llm/costs')
      .then((r) => r.json())
      .then((data) => {
        setSummary(data)
        setLoadingCosts(false)
      })
      .catch(() => {
        toast.error('Failed to load LLM costs')
        setLoadingCosts(false)
      })
  }, [response])

  const handleSend = async () => {
    if (!prompt.trim()) return
    setSending(true)
    try {
      const body = {
        messages: [
          { role: 'system', content: 'You are a helpful assistant.' },
          { role: 'user', content: prompt },
        ],
        provider: provider || undefined,
        model: model || undefined,
        temperature: 0.7,
      }
      const res = await fetch('/llm/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Chat request failed')
      }
      const data: LLMResponse = await res.json()
      setResponse(data)
      toast.success(`Response from ${data.provider}/${data.model}`)
    } catch (e: any) {
      toast.error(e.message || 'Chat request failed')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="min-h-[100dvh] px-4 py-6 md:px-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <div>
          <h1 className="font-display text-3xl font-bold text-text-primary">LLM Studio</h1>
          <p className="text-text-secondary mt-1">
            Pluggable providers, chat, and cost tracking.
          </p>
        </div>

        <Tabs defaultValue="chat" className="w-full">
          <TabsList className="mb-4">
            <TabsTrigger value="chat">Chat</TabsTrigger>
            <TabsTrigger value="providers">Providers</TabsTrigger>
            <TabsTrigger value="costs">Costs</TabsTrigger>
          </TabsList>

          <TabsContent value="chat" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-text-primary">Chat</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-text-secondary">Provider</label>
                    <Input
                      placeholder="default"
                      value={provider}
                      onChange={(e) => setProvider(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-text-secondary">Model</label>
                    <Input
                      placeholder="default"
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                </div>
                <Textarea
                  placeholder="Enter your prompt..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={4}
                />
                <Button onClick={handleSend} disabled={sending || !prompt.trim()}>
                  {sending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
                  Send
                </Button>
              </CardContent>
            </Card>

            {response && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-text-primary">Response</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="whitespace-pre-wrap text-text-primary">{response.content}</div>
                  <div className="flex flex-wrap gap-2 text-xs text-text-secondary">
                    <Badge variant="secondary">{response.provider}</Badge>
                    <Badge variant="secondary">{response.model}</Badge>
                    <Badge variant="secondary">{response.usage.total_tokens} tokens</Badge>
                    <Badge variant="secondary">
                      {response.cost_usd !== null ? `$${response.cost_usd.toFixed(6)}` : 'unknown cost'}
                    </Badge>
                    <Badge variant="secondary">{response.latency_ms}ms</Badge>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="providers">
            <Card>
              <CardHeader>
                <CardTitle className="text-text-primary">Providers</CardTitle>
              </CardHeader>
              <CardContent>
                {loadingProviders ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-accent-cyan" />
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Provider</TableHead>
                        <TableHead>Default Model</TableHead>
                        <TableHead>Env Var</TableHead>
                        <TableHead>Ready</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {providers.map((p) => (
                        <TableRow key={p.id}>
                          <TableCell className="font-medium">{p.name}</TableCell>
                          <TableCell>{p.default_model}</TableCell>
                          <TableCell>{p.env_var || '-'}</TableCell>
                          <TableCell>
                            <Badge variant={p.ready ? 'default' : 'destructive'}>
                              {p.ready ? 'Ready' : 'Missing key'}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="costs" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-text-primary">Usage Summary</CardTitle>
              </CardHeader>
              <CardContent>
                {loadingCosts || !summary ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-accent-cyan" />
                  </div>
                ) : (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="p-4 rounded-lg bg-surface-elevated">
                      <div className="text-sm text-text-secondary">Calls</div>
                      <div className="text-2xl font-bold text-text-primary">{summary.total_calls}</div>
                    </div>
                    <div className="p-4 rounded-lg bg-surface-elevated">
                      <div className="text-sm text-text-secondary">Tokens</div>
                      <div className="text-2xl font-bold text-text-primary">{summary.total_tokens}</div>
                    </div>
                    <div className="p-4 rounded-lg bg-surface-elevated">
                      <div className="text-sm text-text-secondary">Cost</div>
                      <div className="text-2xl font-bold text-text-primary">
                        ${summary.total_cost_usd.toFixed(4)}
                        {summary.cost_estimated && <span className="text-xs text-text-muted ml-1">*</span>}
                      </div>
                    </div>
                    <div className="p-4 rounded-lg bg-surface-elevated">
                      <div className="text-sm text-text-secondary">Recent Calls</div>
                      <div className="text-2xl font-bold text-text-primary">{summary.calls.length}</div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {summary && summary.calls.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-text-primary">Recent Calls</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Time</TableHead>
                        <TableHead>Provider</TableHead>
                        <TableHead>Model</TableHead>
                        <TableHead>Tokens</TableHead>
                        <TableHead>Cost</TableHead>
                        <TableHead>Latency</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {summary.calls.slice(0, 20).map((call) => (
                        <TableRow key={call.id}>
                          <TableCell>{new Date(call.created_at).toLocaleString()}</TableCell>
                          <TableCell>{call.provider}</TableCell>
                          <TableCell>{call.model}</TableCell>
                          <TableCell>{call.total_tokens}</TableCell>
                          <TableCell>
                            {call.cost_usd !== null ? `$${call.cost_usd.toFixed(6)}` : '-'}
                          </TableCell>
                          <TableCell>{call.latency_ms}ms</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
