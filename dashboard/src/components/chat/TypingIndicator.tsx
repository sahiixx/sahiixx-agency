export function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 text-sm text-[var(--text-muted)] mt-2">
      <div className="flex items-center gap-1 rounded-full bg-white/5 px-3 py-1.5">
        <span className="text-xs">Agency is thinking</span>
        <div className="flex gap-0.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-1 w-1 rounded-full bg-accent-cyan"
              style={{
                animation: `typingBounce 1.4s ease-in-out ${i * 0.16}s infinite`,
              }}
            />
          ))}
        </div>
      </div>
      <style>{`
        @keyframes typingBounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
          30% { transform: translateY(-4px); opacity: 1; }
        }
      `}</style>
    </div>
  )
}
