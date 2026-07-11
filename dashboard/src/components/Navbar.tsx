import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useTheme } from 'next-themes'
import { Sun, Moon, Menu, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useBrand } from '@/components/BrandProvider'

function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle cx="16" cy="16" r="3" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="8" cy="10" r="2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="24" cy="10" r="2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="8" cy="22" r="2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="24" cy="22" r="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10 11L14 14" stroke="currentColor" strokeWidth="1" opacity="0.6" />
      <path d="M22 11L18 14" stroke="currentColor" strokeWidth="1" opacity="0.6" />
      <path d="M10 21L14 18" stroke="currentColor" strokeWidth="1" opacity="0.6" />
      <path d="M22 21L18 18" stroke="currentColor" strokeWidth="1" opacity="0.6" />
      <path d="M16 13V9" stroke="currentColor" strokeWidth="1" opacity="0.4" />
      <path d="M16 19V23" stroke="currentColor" strokeWidth="1" opacity="0.4" />
    </svg>
  )
}

const links = [
  { label: 'Graph', path: '/' },
  { label: 'Marketplace', path: '/marketplace' },
  { label: 'LLM', path: '/llm' },
  { label: 'Workflows', path: '/workflows' },
  { label: 'Metrics', path: '/metrics' },
  { label: 'Todos', path: '/todos' },
  { label: 'About', path: '/about' },
  { label: 'Contact', path: '/contact' },
  { label: 'Patterns', path: '/patterns' },
  { label: 'Timeline', path: '/timeline' },
]

export default function Navbar() {
  const location = useLocation()
  const { theme, setTheme } = useTheme()
  const { brandName } = useBrand()
  const [scrolled, setScrolled] = useState(false)
  const [mounted, setMounted] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    // Defer mount state to avoid synchronous setState in render cycle
    const timer = setTimeout(() => setMounted(true), 0)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    // Defer mobile menu close to avoid synchronous setState during render
    const timer = setTimeout(() => setMobileOpen(false), 0)
    return () => clearTimeout(timer)
  }, [location.pathname])

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 100)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  const isDark = theme === 'dark'

  return (
    <>
      <nav
        className="fixed top-0 left-0 right-0 z-50 h-16 flex items-center justify-between px-4 md:px-6 transition-all duration-300"
        style={{
          background: isDark
            ? (scrolled ? 'rgba(10, 10, 18, 0.85)' : 'rgba(10, 10, 18, 0.72)')
            : (scrolled ? 'rgba(255, 255, 255, 0.9)' : 'rgba(255, 255, 255, 0.8)'),
          backdropFilter: 'blur(12px) saturate(1.2)',
          WebkitBackdropFilter: 'blur(12px) saturate(1.2)',
          borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'}`,
        }}
      >
        <div className="flex items-center gap-3">
          <LogoMark className="text-accent-cyan" />
          <span className="font-display font-semibold text-[18px] text-text-primary">
            {brandName}
          </span>
        </div>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8">
          {links.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              className="relative font-sans font-medium text-[14px] text-text-secondary transition-colors hover:text-text-primary"
            >
              {link.label}
              {isActive(link.path) && (
                <span
                  className="absolute -bottom-1 left-0 right-0 h-[2px] rounded-full"
                  style={{
                    background: 'var(--accent-cyan)',
                    boxShadow: '0 0 8px var(--accent-cyan)',
                  }}
                />
              )}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <div className="font-mono text-[11px] text-text-muted hidden lg:block mr-2">
            113 repos · 130 connections · 49 trending
          </div>
          {mounted && (
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9"
              onClick={() => setTheme(isDark ? 'light' : 'dark')}
            >
              {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 md:hidden"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </Button>
        </div>
      </nav>

      {/* Mobile menu */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        >
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            style={{ top: '64px' }}
          />
          <div
            className={cn(
              'absolute top-16 left-0 right-0 border-b p-4 space-y-1',
              isDark ? 'bg-[#0a0a12] border-white/6' : 'bg-white border-black/6'
            )}
            onClick={(e) => e.stopPropagation()}
          >
            {links.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={cn(
                  'block px-4 py-3 rounded-lg font-medium transition-colors',
                  isActive(link.path)
                    ? 'bg-accent-cyan/10 text-accent-cyan'
                    : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
                )}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
