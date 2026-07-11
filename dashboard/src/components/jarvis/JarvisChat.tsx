import { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Send, Bot, User, Zap, Activity } from 'lucide-react';
import { VoiceControl } from './VoiceControl';
import { ShortcutsHelp } from './ShortcutsHelp';
import { useKeyboardShortcuts, JARVIS_SHORTCUTS } from '@/hooks/useKeyboardShortcuts';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'jarvis';
  timestamp: Date;
  action?: string;
}

const QUICK_COMMANDS = [
  { label: 'Status', command: 'status', icon: '📊', shortcut: 'Alt+1' },
  { label: 'Health', command: 'health', icon: '🏥', shortcut: 'Alt+2' },
  { label: 'Registry', command: 'registry', icon: '📦', shortcut: 'Alt+3' },
  { label: 'Tasks', command: 'tasks', icon: '📋', shortcut: 'Alt+4' },
  { label: 'Modules', command: 'modules', icon: '🧩', shortcut: 'Alt+5' },
  { label: 'Help', command: 'help', icon: '❓', shortcut: 'Alt+6' },
];

export function JarvisChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      content: 'Hello! I\'m Jarvis 100x — your AI assistant for OPA.\n\nType a command, click a quick action, or use voice to speak.\nKeyboard shortcuts available — press `?` or click the keyboard icon.',
      sender: 'jarvis',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [connected, setConnected] = useState(false);
  const [lastResponse, setLastResponse] = useState<string>('');
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Send message function
  const sendMessage = useCallback(async (text?: string) => {
    const content = text || input.trim();
    if (!content) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    // Try WebSocket first, fall back to REST
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(content);
    } else {
      try {
        const resp = await fetch('/api/jarvis/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: content }),
        });

        if (resp.ok) {
          const data = await resp.json();
          const response = data.content;
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            content: response,
            sender: 'jarvis',
            timestamp: new Date(),
            action: data.action,
          }]);
          setLastResponse(response);
        }
      } catch {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          content: 'Failed to connect to Jarvis. Is the API server running?',
          sender: 'jarvis',
          timestamp: new Date(),
        }]);
      } finally {
        setIsTyping(false);
      }
    }
  }, [input]);

  // Keyboard shortcuts
  const shortcuts = [
    {
      ...JARVIS_SHORTCUTS.VOICE_TOGGLE,
      action: () => {
        // Trigger voice toggle via button click
        const micButton = document.querySelector('[title="Toggle voice input"]') as HTMLButtonElement;
        micButton?.click();
      },
    },
    {
      ...JARVIS_SHORTCUTS.QUICK_STATUS,
      action: () => sendMessage('status'),
    },
    {
      ...JARVIS_SHORTCUTS.QUICK_HEALTH,
      action: () => sendMessage('health'),
    },
    {
      ...JARVIS_SHORTCUTS.QUICK_REGISTRY,
      action: () => sendMessage('registry'),
    },
    {
      ...JARVIS_SHORTCUTS.QUICK_TASKS,
      action: () => sendMessage('tasks'),
    },
    {
      ...JARVIS_SHORTCUTS.QUICK_MODULES,
      action: () => sendMessage('modules'),
    },
    {
      ...JARVIS_SHORTCUTS.QUICK_HELP,
      action: () => sendMessage('help'),
    },
    {
      ...JARVIS_SHORTCUTS.CLEAR_CHAT,
      action: () => setMessages([messages[0]]),
    },
    {
      ...JARVIS_SHORTCUTS.FOCUS_INPUT,
      action: () => inputRef.current?.focus(),
    },
    {
      ...JARVIS_SHORTCUTS.DISMISS,
      action: () => setShortcutsOpen(false),
    },
    {
      key: '?',
      description: 'Show keyboard shortcuts',
      action: () => setShortcutsOpen(true),
    },
  ];

  useKeyboardShortcuts({ shortcuts });

  // WebSocket connection
  useEffect(() => {
    const connect = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.hostname}:8082/api/jarvis/ws`);

        ws.onopen = () => setConnected(true);
        ws.onclose = () => {
          setConnected(false);
          setTimeout(connect, 3000);
        };
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            const response = data.content;
            setMessages(prev => [...prev, {
              id: Date.now().toString(),
              content: response,
              sender: 'jarvis',
              timestamp: new Date(),
              action: data.action,
            }]);
            setLastResponse(response);
            setIsTyping(false);
          } catch {
            // Ignore parse errors
          }
        };

        wsRef.current = ws;
      } catch {
        setTimeout(connect, 3000);
      }
    };

    connect();
    return () => {
      wsRef.current?.close();
    };
  }, []);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Bot className="h-4 w-4" />
            Jarvis Chat
          </CardTitle>
          <div className="flex items-center gap-2">
            <ShortcutsHelp open={shortcutsOpen} onOpenChange={setShortcutsOpen} />
            <Badge variant={connected ? 'default' : 'destructive'} className="text-xs">
              {connected ? 'Connected' : 'Disconnected'}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col gap-3 overflow-hidden p-4">
        {/* Messages */}
        <ScrollArea className="flex-1" ref={scrollRef}>
          <div className="space-y-3">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 ${
                    msg.sender === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  }`}
                >
                  <div className="flex items-center gap-1 text-xs opacity-70 mb-1">
                    {msg.sender === 'jarvis' ? <Bot className="h-3 w-3" /> : <User className="h-3 w-3" />}
                    {msg.sender === 'jarvis' ? 'Jarvis' : 'You'}
                  </div>
                  <div className="whitespace-pre-wrap text-sm">{msg.content}</div>
                  {msg.action && (
                    <Badge variant="outline" className="mt-1 text-xs">
                      <Zap className="h-3 w-3 mr-1" />
                      {msg.action}
                    </Badge>
                  )}
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-lg px-3 py-2">
                  <div className="flex items-center gap-1 text-xs opacity-70">
                    <Activity className="h-3 w-3 animate-pulse" />
                    Jarvis is thinking...
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Voice Control */}
        <VoiceControl
          onCommand={sendMessage}
          lastResponse={lastResponse}
          autoSpeak={false}
        />

        {/* Quick Commands */}
        <div className="flex flex-wrap gap-1">
          {QUICK_COMMANDS.map((cmd) => (
            <Button
              key={cmd.command}
              variant="outline"
              size="sm"
              className="h-6 text-xs group relative"
              onClick={() => sendMessage(cmd.command)}
              title={`${cmd.label} (${cmd.shortcut})`}
            >
              <span className="mr-1">{cmd.icon}</span>
              {cmd.label}
            </Button>
          ))}
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Ask Jarvis anything..."
            className="flex-1"
            disabled={isTyping}
          />
          <Button onClick={() => sendMessage()} size="icon" disabled={isTyping || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
