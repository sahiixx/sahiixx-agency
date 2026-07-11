import { useState, useEffect, useCallback, useRef } from 'react';

interface SpeechSynthesisOptions {
  lang?: string;
  rate?: number;
  pitch?: number;
  volume?: number;
  voice?: string;
  onEnd?: () => void;
}

interface SpeechSynthesisState {
  isSpeaking: boolean;
  isSupported: boolean;
  voices: SpeechSynthesisVoice[];
  error: string | null;
}

export function useSpeechSynthesis(options: SpeechSynthesisOptions = {}) {
  const {
    lang = 'en-US',
    rate = 1.0,
    pitch = 1.0,
    volume = 1.0,
    voice,
    onEnd,
  } = options;

  const [state, setState] = useState<SpeechSynthesisState>({
    isSpeaking: false,
    isSupported: false,
    voices: [],
    error: null,
  });

  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Check support and load voices
  useEffect(() => {
    const synth = window.speechSynthesis;
    const isSupported = !!synth;

    setState(prev => ({ ...prev, isSupported }));

    if (isSupported) {
      const loadVoices = () => {
        const voices = synth.getVoices();
        setState(prev => ({ ...prev, voices }));
      };

      loadVoices();
      synth.onvoiceschanged = loadVoices;
    }
  }, []);

  const speak = useCallback((text: string) => {
    const synth = window.speechSynthesis;
    if (!synth) {
      setState(prev => ({ ...prev, error: 'Speech synthesis not supported' }));
      return;
    }

    // Cancel any ongoing speech
    synth.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    utterance.rate = rate;
    utterance.pitch = pitch;
    utterance.volume = volume;

    // Find specific voice if requested
    if (voice) {
      const selectedVoice = state.voices.find(v =>
        v.name.includes(voice) || v.lang.startsWith(voice)
      );
      if (selectedVoice) {
        utterance.voice = selectedVoice;
      }
    }

    utterance.onstart = () => {
      setState(prev => ({ ...prev, isSpeaking: true, error: null }));
    };

    utterance.onend = () => {
      setState(prev => ({ ...prev, isSpeaking: false }));
      onEnd?.();
    };

    utterance.onerror = (event) => {
      setState(prev => ({
        ...prev,
        isSpeaking: false,
        error: `Speech synthesis error: ${event.error}`,
      }));
    };

    utteranceRef.current = utterance;
    synth.speak(utterance);
  }, [lang, rate, pitch, volume, voice, state.voices, onEnd]);

  const stop = useCallback(() => {
    const synth = window.speechSynthesis;
    if (synth) {
      synth.cancel();
      setState(prev => ({ ...prev, isSpeaking: false }));
    }
  }, []);

  const pause = useCallback(() => {
    const synth = window.speechSynthesis;
    if (synth) {
      synth.pause();
    }
  }, []);

  const resume = useCallback(() => {
    const synth = window.speechSynthesis;
    if (synth) {
      synth.resume();
    }
  }, []);

  return {
    ...state,
    speak,
    stop,
    pause,
    resume,
  };
}
