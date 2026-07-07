import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import '@testing-library/jest-dom/vitest'
import MarketplacePage from './Marketplace'

describe('MarketplacePage', () => {
  it('renders the page title', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    }) as unknown as typeof fetch

    render(
      <MemoryRouter>
        <MarketplacePage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Module Marketplace')).toBeInTheDocument()
  })
})
