import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import '@testing-library/jest-dom/vitest'
import Panac from './Panac'

const overview = {
  workspace: 'Northstar Industries',
  period: 'Q3 operating view',
  metrics: [],
  signals: [],
  recommendations: [
    {
      id: 'rec_price_001',
      title: 'Protect renewal margin for high-usage accounts',
      owner: 'Revenue strategy agent',
      domain: 'Pricing & retention',
      expected_impact: '+$184k annualized gross margin',
      rationale: 'Usage is 34% above contracted capacity across 18 accounts.',
      status: 'review' as const,
      requires_approval: true,
    },
  ],
  agents: [],
  demo_mode: true,
}

function mockFetch(impl: (input: string) => Partial<Response>) {
  globalThis.fetch = vi.fn((input: string) =>
    Promise.resolve({
      ok: true,
      json: async () => {
        if (input.includes('/revenue-recognition')) {
          return { as_of: '2026-07-15', contract_value: 0, recognized_value: 0, deferred_value: 0, schedules: [], disclaimer: 'demo' }
        }
        if (input.includes('/demand-planning')) {
          return { horizon_days: 30, forecasts: [], disclaimer: 'demo' }
        }
        return undefined
      },
      ...impl(input),
    }),
  ) as unknown as typeof fetch
}

describe('Panac', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page title and workspace header', async () => {
    mockFetch(() => ({ json: async () => overview }))
    render(
      <MemoryRouter>
        <Panac />
      </MemoryRouter>,
    )
    expect(await screen.findByText('Panac')).toBeInTheDocument()
    expect(screen.getByText('Northstar Industries · Q3 operating view')).toBeInTheDocument()
  })

  it('shows the demo-mode badge when no systems are connected', async () => {
    mockFetch(() => ({ json: async () => overview }))
    render(
      <MemoryRouter>
        <Panac />
      </MemoryRouter>,
    )
    expect(await screen.findByText(/Demo workspace/i)).toBeInTheDocument()
  })

  it('records approval when an operator approves a recommendation', async () => {
    let approved = false
    globalThis.fetch = vi.fn((input: string) => {
      if (input.includes('/approve')) {
        approved = true
        return Promise.resolve({
          ok: true,
          json: async () => ({ ...overview.recommendations[0], status: 'approved' }),
        })
      }
      return Promise.resolve({ ok: true, json: async () => overview })
    }) as unknown as typeof fetch

    render(
      <MemoryRouter>
        <Panac />
      </MemoryRouter>,
    )

    const approveButtons = await screen.findAllByRole('button', { name: /Approve for execution/i })
    approveButtons[0].click()
    await waitFor(() => expect(approved).toBe(true))
    expect(await screen.findByText(/Approval recorded/i)).toBeInTheDocument()
  })
})
