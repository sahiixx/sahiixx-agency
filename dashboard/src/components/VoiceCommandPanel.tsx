import { useState, useEffect, useRef } from 'react'
import { Mic, Volume2, Loader2, Command, Play } from 'lucide-react'
import { useVoiceCommand } from '../hooks/useVoiceCommand'

export function VoiceCommandPanel() {
  const { state, transcript, response, error, startListening, stopListening, executeCommand } = useVoiceCommand()
  const [waveform, setWaveform] = useState<number[]>(Array(20).fill(0))
  const animationRef = useRef<number>(0)

  // Simulated waveform animation when listening
  useEffect(() => {
    if (state === 'listening') {
      const animate = () => {
        setWaveform(prev => prev.map(() => Math.random() * 0.8 + 0.1))
        animationRef.current = requestAnimationFrame(animate)
      }
      animationRef.current = requestAnimationFrame(animate)
    } else {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      setWaveform(Array(20).fill(0.05))
    }
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [state])

  const stateConfig = {
    idle: { color: '#525252', text: 'Hold Space to Speak', icon: <Mic className="h-5 w-5" /> },
    listening: { color: '#FF1A1A', text: 'Listening...', icon: <Mic className="h-5 w-5 animate-pulse" /> },
    processing: { color: '#00F0FF', text: 'Processing...', icon: <Loader2 className="h-5 w-5 animate-spin" /> },
    speaking: { color: '#00FF66', text: 'Speaking...', icon: <Volume2 className="h-5 w-5 animate-pulse" /> },
    executing: { color: '#EAB308', text: 'Executing...', icon: <Play className="h-5 w-5 animate-pulse" /> },
  }

  const config = stateConfig[state]

  return (
    <div className="jarvis-card corner-brackets p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Command className="h-4 w-4 text-jarvis-cyan" />
        <span className="text-xs font-display uppercase tracking-wider text-jarvis-text-secondary">
          Jarvis Voice Interface
        </span>
        <div className="live-pulse" style={{ '--pulse-color': config.color } as React.CSSProperties} />
      </div>

      {/* Waveform visualization */}
      <div className="flex items-center justify-center gap-1 h-24">
        {waveform.map((height, i) => (
          <div
            key={i}
            className="w-2 rounded-full transition-all duration-100"
            style={{
              height: `${height * 100}%`,
              backgroundColor: config.color,
              boxShadow: `0 0 8px ${config.color}66`,
              opacity: state === 'idle' ? 0.3 : 1,
            }}
          />
        ))}
      </div>

      {/* Status */}
      <div className="text-center">
        <div
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full border text-xs font-mono uppercase tracking-wider"
          style={{
            borderColor: `${config.color}66`,
            color: config.color,
            backgroundColor: `${config.color}11`,
          }}
        >
          {config.icon}
          {config.text}
        </div>
      </div>

      {/* Transcript */}
      {transcript && (
        <div className="space-y-2">
          <div className="text-[10px] text-jarvis-text-muted uppercase font-display tracking-wider">Transcript</div>
          <div className="p-3 rounded bg-white/5 border border-white/10 font-mono text-sm text-jarvis-text-primary">
            {transcript}
          </div>
        </div>
      )}

      {/* Response */}
      {response && (
        <div className="space-y-2">
          <div className="text-[10px] text-jarvis-text-muted uppercase font-display tracking-wider">Response</div>
          <div className="p-3 rounded bg-jarvis-green/10 border border-jarvis-green/30 font-mono text-sm text-jarvis-green">
            {response}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-3 rounded bg-jarvis-red/10 border border-jarvis-red/30 font-mono text-sm text-jarvis-red">
          {error}
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center justify-center gap-4">
        <button
          onMouseDown={startListening}
          onMouseUp={stopListening}
          onTouchStart={startListening}
          onTouchEnd={stopListening}
          className="flex items-center gap-2 px-6 py-3 rounded-lg border-2 border-jarvis-cyan/50 text-jarvis-cyan hover:bg-jarvis-cyan/20 hover:border-jarvis-cyan transition-all active:scale-95"
        >
          <Mic className="h-5 w-5" />
          <span className="text-xs font-display uppercase tracking-wider">Hold to Speak</span>
        </button>
      </div>

      {/* Quick commands */}
      <div className="space-y-2">
        <div className="text-[10px] text-jarvis-text-muted uppercase font-display tracking-wider">Quick Commands</div>
        <div className="flex flex-wrap gap-2">
          {['System status', 'Kill process', 'Restart service', 'Check updates'].map((cmd) => (
            <button
              key={cmd}
              onClick={() => executeCommand(cmd)}
              className="px-3 py-1.5 rounded border border-white/10 text-xs font-mono text-jarvis-text-secondary hover:border-jarvis-cyan/50 hover:text-jarvis-cyan transition-colors"
            >
              {cmd}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
