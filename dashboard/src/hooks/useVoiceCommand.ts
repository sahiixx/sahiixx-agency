import { useState, useRef, useCallback } from 'react'

export type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking' | 'executing'

export interface VoiceCommand {
  transcript: string
  intent: string
  entities: Record<string, string>
}

export function useVoiceCommand() {
  const [state, setState] = useState<VoiceState>('idle')
  const [transcript, setTranscript] = useState('')
  const [response, setResponse] = useState('')
  const [error, setError] = useState<string | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  const startListening = useCallback(async () => {
    try {
      setState('listening')
      setTranscript('')
      setResponse('')
      setError(null)

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        setState('processing')
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        
        try {
          // Send to backend for STT processing
          const formData = new FormData()
          formData.append('audio', audioBlob)
          
          const res = await fetch('/api/device/voice', {
            method: 'POST',
            body: formData,
          })
          
          if (!res.ok) throw new Error('Voice processing failed')
          
          const result = await res.json()
          setTranscript(result.transcript || '')
          setResponse(result.response || '')
          setState('speaking')
          
          // Auto-play TTS response if available
          if (result.audio_url) {
            const audio = new Audio(result.audio_url)
            await audio.play()
          }
          
          setTimeout(() => setState('idle'), 2000)
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Unknown error')
          setState('idle')
        }
      }

      mediaRecorder.start()
      
      // Stop after 10 seconds max
      setTimeout(() => {
        if (mediaRecorderRef.current?.state === 'recording') {
          mediaRecorderRef.current.stop()
          stream.getTracks().forEach(track => track.stop())
        }
      }, 10000)
    } catch (err) {
      setError('Microphone access denied')
      setState('idle')
    }
  }, [])

  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop())
    }
  }, [])

  const executeCommand = useCallback(async (command: string) => {
    setState('executing')
    try {
      const res = await fetch('/api/device/terminal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command }),
      })
      const result = await res.json()
      setResponse(result.output || 'Command executed')
      setState('idle')
      return result
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Execution failed')
      setState('idle')
      return null
    }
  }, [])

  return {
    state,
    transcript,
    response,
    error,
    startListening,
    stopListening,
    executeCommand,
  }
}
