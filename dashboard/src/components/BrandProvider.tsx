import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

interface WhiteLabelConfig {
  brandName: string
  logoUrl: string
  primaryColor: string
  faviconUrl: string
}

interface BrandContextValue extends WhiteLabelConfig {
  loading: boolean
  error: string | null
}

const defaultConfig: WhiteLabelConfig = {
  brandName: 'One Person Agency',
  logoUrl: '',
  primaryColor: '#6366f1',
  faviconUrl: '',
}

const BrandContext = createContext<BrandContextValue>({
  ...defaultConfig,
  loading: true,
  error: null,
})

export function useBrand() {
  return useContext(BrandContext)
}

function hexToHsl(hex: string): { h: number; s: number; l: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  if (!result) return null

  const r = parseInt(result[1], 16) / 255
  const g = parseInt(result[2], 16) / 255
  const b = parseInt(result[3], 16) / 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  let h = 0
  let s = 0
  const l = (max + min) / 2

  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0)
        break
      case g:
        h = (b - r) / d + 2
        break
      case b:
        h = (r - g) / d + 4
        break
    }
    h /= 6
  }

  return { h: Math.round(h * 360), s: Math.round(s * 100), l: Math.round(l * 100) }
}

function applyBrand(config: WhiteLabelConfig) {
  const { primaryColor, brandName, faviconUrl } = config
  const hsl = hexToHsl(primaryColor)

  if (hsl) {
    const { h, s, l } = hsl
    const hslValue = `${h} ${s}% ${l}%`
    document.documentElement.style.setProperty('--primary', hslValue)
    document.documentElement.style.setProperty('--ring', hslValue)
    document.documentElement.style.setProperty('--sidebar-primary', hslValue)
    document.documentElement.style.setProperty('--sidebar-ring', hslValue)
  }

  document.documentElement.style.setProperty('--accent-cyan', primaryColor)
  document.title = brandName

  if (faviconUrl) {
    let link = document.querySelector("link[rel~='icon']") as HTMLLinkElement | null
    if (!link) {
      link = document.createElement('link')
      link.rel = 'icon'
      document.head.appendChild(link)
    }
    link.href = faviconUrl
  }
}

export function BrandProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<WhiteLabelConfig>(defaultConfig)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    fetch('/api/config/white-label')
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load brand config: ${res.status}`)
        return res.json()
      })
      .then((data: WhiteLabelConfig) => {
        if (cancelled) return
        const merged = { ...defaultConfig, ...data }
        setConfig(merged)
        applyBrand(merged)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Unknown error')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <BrandContext.Provider value={{ ...config, loading, error }}>
      {children}
    </BrandContext.Provider>
  )
}
