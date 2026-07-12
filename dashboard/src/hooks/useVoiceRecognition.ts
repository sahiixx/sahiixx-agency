import { useState, useEffect, useCallback, useRef } from 'react';

interface VoiceRecognitionOptions {
  lang?: string;
  continuous?: boolean;
  interimResults?: boolean;
  onResult?: (transcript: string, isFinal: boolean) => void;
  onError?: (error: string) => void;
  onEnd?: () => void;
}

interface VoiceRecognitionState {
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
  isSupported: boolean;
  error: string | null;
}

interface SpeechRecognitionEvent {
  resultIndex: number;
  results: {
    [index: number]: {
      [index: number]: { transcript: string };
      isFinal: boolean;
    };
    length: number;
  };
}

interface SpeechRecognitionErrorEvent {
  error: string;
}

interface SpeechRecognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

interface SpeechRecognitionStatic {
  new (): SpeechRecognition;
}

interface WindowWithSpeechRecognition extends Window {
  SpeechRecognition?: SpeechRecognitionStatic;
  webkitSpeechRecognition?: SpeechRecognitionStatic;
}

function getSpeechRecognition(): SpeechRecognitionStatic | undefined {
  if (typeof window === 'undefined') return undefined;
  const win = window as unknown as WindowWithSpeechRecognition;
  return win.SpeechRecognition || win.webkitSpeechRecognition;
}

export function useVoiceRecognition(options: VoiceRecognitionOptions = {}) {
  const {
    lang = 'en-US',
    continuous = false,
    interimResults = true,
    onResult,
    onError,
    onEnd,
  } = options;

  const [state, setState] = useState<VoiceRecognitionState>(() => ({
    isListening: false,
    transcript: '',
    interimTranscript: '',
    isSupported: !!getSpeechRecognition(),
    error: null,
  }));

  const recognitionRef = useRef<SpeechRecognition | null>(null);

  // Create recognition instance once support is known
  useEffect(() => {
    const SpeechRecognition = getSpeechRecognition();
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.lang = lang;
      recognition.continuous = continuous;
      recognition.interimResults = interimResults;
      recognitionRef.current = recognition;
    }
  }, [lang, continuous, interimResults]);

  const startListening = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition) {
      setState((prev) => ({ ...prev, error: 'Speech recognition not supported' }));
      return;
    }

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = '';
      let final = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcript;
        } else {
          interim += transcript;
        }
      }

      setState((prev) => ({
        ...prev,
        transcript: final || prev.transcript,
        interimTranscript: interim,
      }));

      if (final) {
        onResult?.(final, true);
      } else if (interim) {
        onResult?.(interim, false);
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      const error = event.error === 'no-speech'
        ? 'No speech detected'
        : event.error === 'audio-capture'
        ? 'No microphone found'
        : event.error === 'not-allowed'
        ? 'Microphone permission denied'
        : `Speech recognition error: ${event.error}`;

      setState((prev) => ({ ...prev, error, isListening: false }));
      onError?.(error);
    };

    recognition.onend = () => {
      setState((prev) => ({ ...prev, isListening: false }));
      onEnd?.();
    };

    try {
      recognition.start();
      setState((prev) => ({ ...prev, isListening: true, error: null, transcript: '', interimTranscript: '' }));
    } catch {
      setState((prev) => ({ ...prev, error: 'Failed to start speech recognition' }));
    }
  }, [onResult, onError, onEnd]);

  const stopListening = useCallback(() => {
    const recognition = recognitionRef.current;
    if (recognition && state.isListening) {
      recognition.stop();
      setState((prev) => ({ ...prev, isListening: false }));
    }
  }, [state.isListening]);

  const resetTranscript = useCallback(() => {
    setState((prev) => ({ ...prev, transcript: '', interimTranscript: '' }));
  }, []);

  return {
    ...state,
    startListening,
    stopListening,
    resetTranscript,
  };
}
