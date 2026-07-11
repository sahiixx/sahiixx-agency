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

export function useVoiceRecognition(options: VoiceRecognitionOptions = {}) {
  const {
    lang = 'en-US',
    continuous = false,
    interimResults = true,
    onResult,
    onError,
    onEnd,
  } = options;

  const [state, setState] = useState<VoiceRecognitionState>({
    isListening: false,
    transcript: '',
    interimTranscript: '',
    isSupported: false,
    error: null,
  });

  const recognitionRef = useRef<any>(null);

  // Check support on mount
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    setState(prev => ({ ...prev, isSupported: !!SpeechRecognition }));

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
      setState(prev => ({ ...prev, error: 'Speech recognition not supported' }));
      return;
    }

    recognition.onresult = (event: any) => {
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

      setState(prev => ({
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

    recognition.onerror = (event: any) => {
      const error = event.error === 'no-speech'
        ? 'No speech detected'
        : event.error === 'audio-capture'
        ? 'No microphone found'
        : event.error === 'not-allowed'
        ? 'Microphone permission denied'
        : `Speech recognition error: ${event.error}`;

      setState(prev => ({ ...prev, error, isListening: false }));
      onError?.(error);
    };

    recognition.onend = () => {
      setState(prev => ({ ...prev, isListening: false }));
      onEnd?.();
    };

    try {
      recognition.start();
      setState(prev => ({ ...prev, isListening: true, error: null, transcript: '', interimTranscript: '' }));
    } catch (e) {
      setState(prev => ({ ...prev, error: 'Failed to start speech recognition' }));
    }
  }, [onResult, onError, onEnd]);

  const stopListening = useCallback(() => {
    const recognition = recognitionRef.current;
    if (recognition && state.isListening) {
      recognition.stop();
      setState(prev => ({ ...prev, isListening: false }));
    }
  }, [state.isListening]);

  const resetTranscript = useCallback(() => {
    setState(prev => ({ ...prev, transcript: '', interimTranscript: '' }));
  }, []);

  return {
    ...state,
    startListening,
    stopListening,
    resetTranscript,
  };
}
