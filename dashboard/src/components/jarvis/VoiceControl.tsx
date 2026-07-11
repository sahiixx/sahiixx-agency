import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Mic, MicOff, Volume2, VolumeX } from 'lucide-react';
import { useVoiceRecognition } from '@/hooks/useVoiceRecognition';
import { useSpeechSynthesis } from '@/hooks/useSpeechSynthesis';
import { cn } from '@/lib/utils';

interface VoiceControlProps {
  onCommand: (text: string) => void;
  lastResponse?: string;
  autoSpeak?: boolean;
}

export function VoiceControl({ onCommand, lastResponse, autoSpeak = false }: VoiceControlProps) {
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [autoSpeakEnabled, setAutoSpeakEnabled] = useState(autoSpeak);

  const {
    isListening,
    transcript,
    interimTranscript,
    isSupported: sttSupported,
    error: sttError,
    startListening,
    stopListening,
    resetTranscript,
  } = useVoiceRecognition({
    lang: 'en-US',
    continuous: false,
    interimResults: true,
    onResult: (text, isFinal) => {
      if (isFinal && text.trim()) {
        onCommand(text.trim());
        resetTranscript();
      }
    },
    onError: (error) => {
      console.error('Voice error:', error);
    },
  });

  const {
    isSpeaking,
    isSupported: ttsSupported,
    error: ttsError,
    speak,
    stop: stopSpeaking,
  } = useSpeechSynthesis({
    lang: 'en-US',
    rate: 1.0,
    pitch: 1.0,
  });

  // Auto-speak responses
  useEffect(() => {
    if (autoSpeakEnabled && lastResponse && voiceEnabled && !isListening) {
      // Strip markdown formatting for speech
      const plainText = lastResponse
        .replace(/\*\*/g, '')
        .replace(/#{1,6}\s/g, '')
        .replace(/`/g, '')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .replace(/[-*]\s/g, '')
        .trim();

      if (plainText) {
        speak(plainText);
      }
    }
  }, [lastResponse, autoSpeakEnabled, voiceEnabled, isListening, speak]);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      stopSpeaking();
      startListening();
    }
  }, [isListening, startListening, stopListening, stopSpeaking]);

  const toggleVoice = useCallback(() => {
    if (voiceEnabled) {
      stopListening();
      stopSpeaking();
    }
    setVoiceEnabled(!voiceEnabled);
  }, [voiceEnabled, stopListening, stopSpeaking]);

  const isSupported = sttSupported || ttsSupported;

  if (!isSupported) {
    return (
      <Card className="bg-muted/50">
        <CardContent className="p-3">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <MicOff className="h-4 w-4" />
            <span>Voice not supported in this browser</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-muted/50">
      <CardContent className="p-3">
        <div className="flex items-center justify-between gap-3">
          {/* Voice Status */}
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {isListening && (
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                <span className="text-xs text-red-500">Listening...</span>
              </div>
            )}
            {isSpeaking && (
              <div className="flex items-center gap-1">
                <Volume2 className="h-3 w-3 text-green-500 animate-pulse" />
                <span className="text-xs text-green-500">Speaking...</span>
              </div>
            )}
            {!isListening && !isSpeaking && transcript && (
              <span className="text-xs text-muted-foreground truncate">{transcript}</span>
            )}
            {!isListening && !isSpeaking && !transcript && (
              <span className="text-xs text-muted-foreground">
                {voiceEnabled ? 'Click mic to speak' : 'Voice disabled'}
              </span>
            )}
            {interimTranscript && (
              <span className="text-xs text-cyan-500 truncate italic">{interimTranscript}</span>
            )}
          </div>

          {/* Controls */}
          <div className="flex items-center gap-1">
            {/* Auto-speak toggle */}
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setAutoSpeakEnabled(!autoSpeakEnabled)}
              title={autoSpeakEnabled ? 'Disable auto-speak' : 'Enable auto-speak'}
            >
              {autoSpeakEnabled ? (
                <Volume2 className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <VolumeX className="h-3.5 w-3.5 text-muted-foreground" />
              )}
            </Button>

            {/* Voice enable/disable */}
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={toggleVoice}
              title={voiceEnabled ? 'Disable voice' : 'Enable voice'}
            >
              {voiceEnabled ? (
                <Mic className="h-3.5 w-3.5" />
              ) : (
                <MicOff className="h-3.5 w-3.5 text-muted-foreground" />
              )}
            </Button>

            {/* Main mic button */}
            <Button
              size="icon"
              className={cn(
                "h-9 w-9 rounded-full transition-all",
                isListening
                  ? "bg-red-500 hover:bg-red-600 text-white animate-pulse"
                  : "bg-primary hover:bg-primary/90"
              )}
              onClick={toggleListening}
              disabled={!voiceEnabled || isSpeaking}
            >
              {isListening ? (
                <MicOff className="h-4 w-4" />
              ) : (
                <Mic className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        {/* Error display */}
        {(sttError || ttsError) && (
          <div className="mt-2 text-xs text-red-500">
            {sttError || ttsError}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
