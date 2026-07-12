import { useState, useCallback, useRef } from 'react';

interface SpeechSynthesisOptions {
  lang?: string;
  rate?: number;
  pitch?: number;
  volume?: number;
  voice?: string;
  voiceId?: string;
  onEnd?: () => void;
}

interface SpeechSynthesisState {
  isSpeaking: boolean;
  isSupported: boolean;
  error: string | null;
}

export function useSpeechSynthesis(options: SpeechSynthesisOptions = {}) {
  const { voiceId = '21m00Tcm4TlvDq8ikWAM', onEnd } = options;

  const [state, setState] = useState<SpeechSynthesisState>({
    isSpeaking: false,
    isSupported: true,
    error: null,
  });

  const audioRef = useRef<HTMLAudioElement | null>(null);

  const speak = useCallback(async (text: string) => {
    setState(prev => ({ ...prev, isSpeaking: true, error: null }));

    try {
      const resp = await fetch('/api/jarvis/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voice_id: voiceId }),
      });

      if (!resp.ok) {
        throw new Error('TTS request failed');
      }

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);

      // Stop any current audio
      if (audioRef.current) {
        audioRef.current.pause();
        URL.revokeObjectURL(audioRef.current.src);
      }

      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onended = () => {
        setState(prev => ({ ...prev, isSpeaking: false }));
        URL.revokeObjectURL(url);
        onEnd?.();
      };

      audio.onerror = () => {
        setState(prev => ({ ...prev, isSpeaking: false, error: 'Audio playback failed' }));
        URL.revokeObjectURL(url);
      };

      await audio.play();
    } catch (e) {
      setState(prev => ({
        ...prev,
        isSpeaking: false,
        error: e instanceof Error ? e.message : 'TTS failed',
      }));
    }
  }, [voiceId, onEnd]);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setState(prev => ({ ...prev, isSpeaking: false }));
  }, []);

  return {
    ...state,
    speak,
    stop,
  };
}
