import { useState, useRef, useEffect, useCallback } from 'react'
import { Mic, MicOff, Loader2, Radio } from 'lucide-react'

type VoiceState = 'idle' | 'listening' | 'processing' | 'error'

interface VoiceCommandPanelProps {
  onCommand?: (command: string) => void
  compact?: boolean
}

interface SpeechRecognitionEvent {
  resultIndex: number
  results: {
    [index: number]: {
      [index: number]: { transcript: string }
      isFinal: boolean
    }
    length: number
  }
}

interface SpeechRecognition {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
}

interface SpeechRecognitionStatic {
  new (): SpeechRecognition
}

interface WindowWithSpeechRecognition extends Window {
  SpeechRecognition?: SpeechRecognitionStatic
  webkitSpeechRecognition?: SpeechRecognitionStatic
}

const stateConfig: Record<VoiceState, { icon: React.ElementType; color: string; label: string }> = {
  idle: { icon: Mic, color: 'text-accent-cyan', label: 'Tap to speak' },
  listening: { icon: MicOff, color: 'text-accent-red', label: 'Listening...' },
  processing: { icon: Loader2, color: 'text-accent-amber', label: 'Processing...' },
  error: { icon: MicOff, color: 'text-red-400', label: 'Error' },
}

function getSpeechRecognition(): SpeechRecognitionStatic | undefined {
  if (typeof window === 'undefined') return undefined
  const win = window as unknown as WindowWithSpeechRecognition
  return win.SpeechRecognition || win.webkitSpeechRecognition
}

export function VoiceCommandPanel({ onCommand, compact = false }: VoiceCommandPanelProps) {
  const [state, setState] = useState<VoiceState>('idle')
  const [transcript, setTranscript] = useState('')
  const [waveform, setWaveform] = useState<number[]>(Array(20).fill(0))
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const animationRef = useRef<number>(0)

  const resetWaveform = useCallback(() => {
    setWaveform(Array(20).fill(0.05))
  }, [])

  // Simulated waveform animation when listening
  useEffect(() => {
    if (state !== 'listening') return

    const animate = () => {
      setWaveform((prev) => prev.map(() => Math.random() * 0.8 + 0.1))
      animationRef.current = requestAnimationFrame(animate)
    }
    animationRef.current = requestAnimationFrame(animate)

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current)
    }
  }, [state])

  useEffect(() => {
    if (state !== 'listening') {
      window.setTimeout(resetWaveform, 0)
    }
  }, [state, resetWaveform])

  const startListening = () => {
    const SR = getSpeechRecognition()
    if (!SR) {
      setState('error')
      return
    }

    setState('listening')
    setTranscript('')

    const recognition = new SR()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const last = event.results[event.results.length - 1]
      if (last.isFinal) {
        const text = last[0].transcript.trim()
        setTranscript(text)
        if (text) {
          setState('processing')
          onCommand?.(text)
          window.setTimeout(() => setState('idle'), 1500)
        } else {
          setState('idle')
        }
      }
    }

    recognition.onerror = () => {
      setState('error')
      window.setTimeout(() => setState('idle'), 2000)
    }

    recognition.onend = () => {
      setState('idle')
    }

    recognitionRef.current = recognition
    try { recognition.start() } catch { /* already started */ }
  }

  const stopListening = () => {
    try { recognitionRef.current?.stop() } catch { /* already stopped */ }
    recognitionRef.current = null
    setState('idle')
  }

  const toggle = () => {
    if (state === 'listening') stopListening()
    else startListening()
  }

  const { icon: Icon, color, label } = stateConfig[state]
  const isListening = state === 'listening'
  const isProcessing = state === 'processing'

  if (compact) {
    return (
      <button
        onClick={toggle}
        className={`relative p-2 rounded-lg transition-colors ${
          isListening ? 'bg-accent-red/20 text-accent-red' : 'bg-white/5 hover:bg-white/10 text-[var(--text-muted)]'
        }`}
        title={label}
      >
        {isProcessing ? <Loader2 className="h-5 w-5 animate-spin" /> : <Icon className={`h-5 w-5 ${color}`} />}
        {isListening && (
          <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-accent-red animate-pulse" />
        )}
      </button>
    )
  }

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radio className="h-4 w-4 text-accent-cyan" />
          <span className="text-sm font-semibold text-[var(--text-primary)]">Voice Command</span>
        </div>
        <div className="text-xs text-[var(--text-muted)]">{label}</div>
      </div>

      <div className="h-12 flex items-center gap-0.5">
        {waveform.map((amp, i) => (
          <div
            key={i}
            className="flex-1 rounded-full transition-all duration-75"
            style={{
              height: `${amp * 100}%`,
              backgroundColor: isListening ? 'var(--accent-red)' : 'var(--accent-cyan)',
              opacity: isListening ? 1 : 0.3,
            }}
          />
        ))}
      </div>

      {transcript && (
        <div className="text-xs text-[var(--text-muted)] bg-white/5 rounded p-2">
          “{transcript}”
        </div>
      )}

      <button
        onClick={toggle}
        className={`w-full py-2.5 rounded-lg flex items-center justify-center gap-2 font-medium transition-colors ${
          isListening
            ? 'bg-accent-red text-white hover:bg-accent-red/90'
            : 'bg-accent-cyan text-white hover:bg-accent-cyan/90'
        }`}
      >
        {isProcessing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
        {isListening ? 'Stop Listening' : isProcessing ? 'Processing...' : 'Start Listening'}
      </button>
    </div>
  )
}
