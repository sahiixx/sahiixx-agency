import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { TrendingPanel } from './TrendingPanel'

function mockFetch(handler: (url: string) => { ok?: boolean; status?: number; json: () => Promise<unknown> }) {
  globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString()
    const res = handler(url)
    return Promise.resolve({
      ok: res.ok ?? true,
      status: res.status ?? 200,
      json: res.json,
    }) as unknown as Promise<Response>
  }) as unknown as typeof fetch
}

describe('TrendingPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('renders the heading and Scout Now button', async () => {
    mockFetch(() => ({ json: async () => [] }))
    render(<TrendingPanel />)
    expect(await screen.findByText('Trending Repos')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Scout Now/i })).toBeInTheDocument()
  })

  it('shows empty-state prompt when no repos in snapshot', async () => {
    mockFetch(() => ({ json: async () => [] }))
    render(<TrendingPanel />)
    expect(await screen.findByText(/No repos yet/i)).toBeInTheDocument()
  })

  it('loads repos from the snapshot on mount', async () => {
    mockFetch((url) => {
      if (url.includes('/discovery/trending')) {
        return {
          json: async () => [
            {
              full_name: 'octo/snap-repo',
              url: 'https://github.com/octo/snap-repo',
              description: 'from snapshot',
              stars: 42,
              language: 'Go',
              category: 'infrastructure',
              risk_level: 'low',
            },
          ],
        }
      }
      return { json: async () => ({}) }
    })
    render(<TrendingPanel />)
    expect(await screen.findByText('octo/snap-repo')).toBeInTheDocument()
    expect(screen.getByText('from snapshot')).toBeInTheDocument()
  })

  it('runs a live scout and renders results with a live badge', async () => {
    mockFetch((url) => {
      if (url.includes('/discovery/trending')) {
        return { json: async () => [] }
      }
      if (url.includes('/intel')) {
        return {
          json: async () => ({
            repos: [
              {
                full_name: 'octo/live-repo',
                url: 'https://github.com/octo/live-repo',
                description: 'freshly scouted',
                stars: 999,
                language: 'Rust',
                category: 'agent_framework',
                risk_level: 'low',
              },
            ],
          }),
        }
      }
      return { json: async () => ({}) }
    })

    render(<TrendingPanel />)
    const scoutBtn = await screen.findByRole('button', { name: /Scout Now/i })
    fireEvent.click(scoutBtn)

    expect(await screen.findByText('octo/live-repo')).toBeInTheDocument()
    expect(screen.getByText('freshly scouted')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('live')).toBeInTheDocument())
  })

  it('surfaces an error when the scout call fails', async () => {
    mockFetch((url) => {
      if (url.includes('/discovery/trending')) {
        return { json: async () => [] }
      }
      if (url.includes('/intel')) {
        return { ok: false, status: 500, json: async () => ({}) }
      }
      return { json: async () => ({}) }
    })

    render(<TrendingPanel />)
    const scoutBtn = await screen.findByRole('button', { name: /Scout Now/i })
    fireEvent.click(scoutBtn)

    expect(await screen.findByText(/Scout failed \(HTTP 500\)/i)).toBeInTheDocument()
  })
})
