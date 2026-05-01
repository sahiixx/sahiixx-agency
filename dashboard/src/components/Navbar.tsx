import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'

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

export default function Navbar() {
  const location = useLocation()
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 100)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const links = [
    { label: 'Graph', path: '/' },
    { label: 'Patterns', path: '/patterns' },
    { label: 'Timeline', path: '/timeline' },
  ]

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 h-16 flex items-center justify-between px-6 transition-all duration-300"
      style={{
        background: scrolled
          ? 'rgba(10, 10, 18, 0.85)'
          : 'rgba(10, 10, 18, 0.72)',
        backdropFilter: 'blur(12px) saturate(1.2)',
        WebkitBackdropFilter: 'blur(12px) saturate(1.2)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      <div className="flex items-center gap-3">
        <LogoMark className="text-accent-cyan" />
        <span className="font-display font-semibold text-[18px] text-text-primary">
          AI Nexus
        </span>
      </div>

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

      <div className="font-mono text-[11px] text-text-muted hidden lg:block">
        113 repos · 130 connections · 49 trending
      </div>
    </nav>
  )
}
