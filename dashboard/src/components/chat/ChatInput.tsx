import { useState, useCallback, useRef, useEffect } from 'react'
import { Send, Mic, MicOff, Loader2, Ear } from 'lucide-react'

interface ChatInputProps {
  onSend: (text: string) => void
  disabled?: boolean
}

interface SpeechRecognitionEvent {
  results: SpeechRecognitionResultList
}

interface SpeechRecognitionResultList {
  length: number
  [index: number]: {
    [index: number]: { transcript: string }
    isFinal: boolean
  }
}

const WAKE_WORDS = ['hey jarvis', 'ok agency', 'hello agency', 'jarvis']

function VoiceWaveform({ active }: { active: boolean }) {
  if (!active) return null
  return (
    <div className="flex items-center gap-0.5 h-5">
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="w-0.5 rounded-full bg-accent-cyan"
          style={{
            height: '100%',
            animation: `voiceWave 0.5s ease-in-out ${i * 0.1}s infinite alternate`,
          }}
        />
      ))}
      <style>{`
        @keyframes voiceWave {
          0% { transform: scaleY(0.3); opacity: 0.4; }
          100% { transform: scaleY(1); opacity: 1; }
        }
      `}</style>
    </div>
  )
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState('')
  const [listening, setListening] = useState(false)
  const [wakeMode, setWakeMode] = useState(false)
  const recognitionRef = useRef<any>(null)
  const wakeRecognitionRef = useRef<any>(null)
  const transcriptBuffer = useRef('')

  // Normal voice input (manual mic button)
  useEffect(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) return

    const recognition = new SR()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const last = event.results[event.results.length - 1]
      if (last.isFinal) {
        const transcript = last[0].transcript.trim()
        if (transcript) {
          setText((prev) => (prev ? prev + ' ' + transcript : transcript))
        }
        setListening(false)
      }
    }

    recognition.onerror = () => {
      setListening(false)
    }

    recognition.onend = () => {
      setListening(false)
    }

    recognitionRef.current = recognition
  }, [])

  // Wake-word detection (always listening when enabled)
  useEffect(() => {
    if (!wakeMode) return
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) return

    const recognition = new SR()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const last = event.results[event.results.length - 1]
      const transcript = last[0].transcript.toLowerCase().trim()
      
      // Check for wake word
      const hasWakeWord = WAKE_WORDS.some((w) => transcript.includes(w))
      
      if (hasWakeWord) {
        // Extract command after wake word
        let command = transcript
        for (const word of WAKE_WORDS) {
          const idx = command.indexOf(word)
          if (idx !== -1) {
            command = command.slice(idx + word.length).trim()
            break
          }
        }
        
        if (command) {
          onSend(command)
          transcriptBuffer.current = ''
        } else {
          // Wake word detected but no command yet — start active listening
          setListening(true)
          if (recognitionRef.current) {
            try { recognitionRef.current.start() } catch {}
          }
        }
      }
    }

    recognition.onerror = () => {
      // Restart on error
      if (wakeMode) {
        setTimeout(() => {
          try { wakeRecognitionRef.current?.start() } catch {}
        }, 500)
      }
    }

    recognition.onend = () => {
      if (wakeMode) {
        setTimeout(() => {
          try { wakeRecognitionRef.current?.start() } catch {}
        }, 200)
      }
    }

    wakeRecognitionRef.current = recognition
    try { recognition.start() } catch {}

    return () => {
      try { recognition.stop() } catch {}
    }
  }, [wakeMode, onSend])

  const toggleMic = useCallback(() => {
    if (!recognitionRef.current) return
    if (listening) {
      recognitionRef.current.stop()
      setListening(false)
    } else {
      try {
        recognitionRef.current.start()
        setListening(true)
      } catch {
        // already started
      }
    }
  }, [listening])

  const toggleWakeMode = useCallback(() => {
    setWakeMode((v) => {
      if (v) {
        // turning off
        try { wakeRecognitionRef.current?.stop() } catch {}
        try { recognitionRef.current?.stop() } catch {}
        setListening(false)
      }
      return !v
    })
  }, [])

  const handleSend = useCallback(() => {
    if (disabled || !text.trim()) return
    onSend(text.trim())
    setText('')
  }, [text, disabled, onSend])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  return (
    <div className="flex items-end gap-3">
      <div className="flex-1 relative">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={
            wakeMode
              ? 'Wake word active — say "Hey Jarvis"...'
              : listening
              ? 'Listening... speak now'
              : 'Type a command or question...'
          }
          rows={1}
          className="w-full resize-none rounded-xl bg-[var(--bg-elevated)] border border-white/8 px-4 py-3 pr-10 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-accent-cyan/30 focus:border-accent-cyan/30 disabled:opacity-50"
          style={{ minHeight: '48px', maxHeight: '160px' }}
        />
        {listening && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <VoiceWaveform active={listening} />
          </div>
        )}
      </div>
      <button
        onClick={toggleWakeMode}
        disabled={disabled}
        className={`flex h-12 w-12 items-center justify-center rounded-xl transition-colors ${
          wakeMode
            ? 'bg-accent-cyan text-white animate-pulse'
            : 'bg-white/10 text-[var(--text-muted)] hover:bg-white/15 hover:text-[var(--text-primary)]'
        } disabled:opacity-40 disabled:cursor-not-allowed`}
        title={wakeMode ? 'Wake word active — say "Hey Jarvis"' : 'Enable wake word detection'}
      >
        <Ear className="h-5 w-5" />
      </button>
      <button
        onClick={toggleMic}
        disabled={disabled}
        className={`flex h-12 w-12 items-center justify-center rounded-xl transition-colors ${
          listening
            ? 'bg-accent-red text-white'
            : 'bg-white/10 text-[var(--text-muted)] hover:bg-white/15 hover:text-[var(--text-primary)]'
        } disabled:opacity-40 disabled:cursor-not-allowed`}
        title={listening ? 'Stop listening' : 'Voice input'}
      >
        {listening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
      </button>
      <button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent-cyan text-white hover:bg-accent-cyan/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        {disabled ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
      </button>
    </div>
  )
}
