import { Link } from 'react-router-dom'

function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      width="24"
      height="24"
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
    </svg>
  )
}

export default function Footer() {
  return (
    <footer className="w-full border-t border-white/[0.06] bg-bg-base py-12 px-6">
      <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <LogoMark className="text-accent-cyan" />
            <span className="font-display font-semibold text-[16px] text-text-primary">
              AI Nexus
            </span>
          </div>
          <p className="text-body-sm text-text-muted">
            Mapping the architecture of AI
          </p>
        </div>

        <div>
          <h4 className="font-sans font-medium text-[14px] text-text-primary mb-3">
            Quick Links
          </h4>
          <div className="flex flex-col gap-2">
            <Link to="/" className="text-body-sm text-text-muted hover:text-text-secondary transition-colors">
              Graph
            </Link>
            <Link to="/patterns" className="text-body-sm text-text-muted hover:text-text-secondary transition-colors">
              Patterns
            </Link>
            <Link to="/timeline" className="text-body-sm text-text-muted hover:text-text-secondary transition-colors">
              Timeline
            </Link>
          </div>
        </div>

        <div>
          <h4 className="font-sans font-medium text-[14px] text-text-primary mb-3">
            Attribution
          </h4>
          <p className="text-body-sm text-text-muted">
            Data sourced from GitHub API · Updated in real-time
          </p>
        </div>
      </div>
    </footer>
  )
}
