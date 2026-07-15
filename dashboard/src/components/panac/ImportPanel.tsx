import { useRef, useState, type ChangeEvent } from 'react'
import { FileUp, Loader2 } from 'lucide-react'

type Source = 'contracts' | 'subscriptions' | 'usage' | 'inventory'

interface ImportSummary { source: string; records_imported: number; imported_at: string; status: 'ready' }

interface ImportPanelProps { onImported: (summary: ImportSummary) => void }

function parseCsv(text: string): Record<string, string>[] {
  const [headerLine, ...lines] = text.trim().split(/\r?\n/)
  if (!headerLine || lines.length === 0) throw new Error('Your CSV needs a header and at least one data row.')
  const headers = headerLine.split(',').map((header) => header.trim())
  return lines.filter(Boolean).map((line) => {
    const values = line.split(',').map((value) => value.trim())
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? '']))
  })
}

export function ImportPanel({ onImported }: ImportPanelProps) {
  const [source, setSource] = useState<Source>('contracts')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    setBusy(true)
    setMessage(null)
    try {
      const records = parseCsv(await file.text())
      const response = await fetch('/api/panac/imports', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source, records }) })
      const data = await response.json() as ImportSummary | { detail?: string }
      if (!response.ok) throw new Error('detail' in data ? data.detail : 'Import failed')
      onImported(data as ImportSummary)
      setMessage(`${file.name}: ${records.length} records validated and ready.`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Import failed')
    } finally {
      setBusy(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return <section className="mt-9 rounded-2xl border border-dashed border-cyan-500/30 bg-cyan-500/5 p-5"><div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between"><div><h2 className="font-display text-lg font-semibold text-text-primary">Connect your operating data</h2><p className="mt-1 text-sm text-text-secondary">Import a CSV extract first. Panac validates it locally and does not write to source systems.</p></div><div className="flex items-center gap-2"><label className="sr-only" htmlFor="panac-source">Data source</label><select id="panac-source" value={source} onChange={(event) => setSource(event.target.value as Source)} className="h-10 rounded-lg border border-black/10 bg-bg-surface px-3 text-sm text-text-primary dark:border-white/10"><option value="contracts">Contracts</option><option value="subscriptions">Subscriptions</option><option value="usage">Usage</option><option value="inventory">Inventory</option></select><input ref={inputRef} className="hidden" id="panac-csv" type="file" accept=".csv,text/csv" onChange={handleFile} /><label htmlFor="panac-csv" className="inline-flex h-10 cursor-pointer items-center justify-center gap-2 rounded-lg bg-accent-cyan px-4 text-sm font-medium text-white hover:opacity-90">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}{busy ? 'Validating…' : 'Import CSV'}</label></div></div>{message && <p className="mt-3 text-sm text-text-secondary" role="status">{message}</p>}</section>
}
