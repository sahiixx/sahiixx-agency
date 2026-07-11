"""Jarvis Dashboard — React components for the OPA dashboard."""

from __future__ import annotations

# This file provides the component structure for the Jarvis dashboard.
# The actual React components are in dashboard/src/components/jarvis/

COMPONENT_STRUCTURE = """
dashboard/src/components/jarvis/
├── JarvisPanel.tsx          # Main Jarvis chat panel
├── JarvisInput.tsx          # Text input with voice toggle
├── JarvisMessage.tsx        # Message bubble component
├── JarvisStatus.tsx         # Status indicator
├── JarvisEvents.tsx         # Monitoring events feed
├── JarvisCommands.tsx       # Quick command buttons
└── JarvisVoice.tsx          # Voice input component
"""

JARVIS_PANEL_CODE = """
// JarvisPanel.tsx — Main chat interface
import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Send, Mic, MicOff, Bot, User, Activity } from 'lucide-react';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'jarvis';
  timestamp: Date;
  action?: string;
}

interface JarvisEvent {
  event_type: string;
  severity: string;
  title: string;
  description: string;
  suggested_action?: string;
  timestamp: string;
}

export function JarvisPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [status, setStatus] = useState<string>('idle');
  const [events, setEvents] = useState<JarvisEvent[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Connect to WebSocket
  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.hostname}:8082/api/jarvis/ws`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages(prev => [...prev, {
        id: data.timestamp,
        content: data.content,
        sender: 'jarvis',
        timestamp: new Date(data.timestamp),
        action: data.action,
      }]);
      setIsTyping(false);
    };

    ws.onclose = () => {
      console.log('Jarvis WebSocket disconnected');
    };

    return () => ws.close();
  }, []);

  // Fetch events
  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const resp = await fetch('/api/jarvis/events?limit=10');
        if (resp.ok) {
          setEvents(await resp.json());
        }
      } catch (e) {
        console.error('Failed to fetch events:', e);
      }
    };

    fetchEvents();
    const interval = setInterval(fetchEvents, 30000);
    return () => clearInterval(interval);
  }, []);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      const resp = await fetch('/api/jarvis/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input }),
      });

      if (resp.ok) {
        const data = await resp.json();
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          content: data.content,
          sender: 'jarvis',
          timestamp: new Date(),
          action: data.action,
        }]);
      }
    } catch (e) {
      console.error('Failed to send message:', e);
    } finally {
      setIsTyping(false);
    }
  };

  const quickCommands = [
    { label: 'Status', command: 'status' },
    { label: 'Health', command: 'health' },
    { label: 'Registry', command: 'registry' },
    { label: 'Tasks', command: 'tasks' },
    { label: 'Modules', command: 'modules' },
    { label: 'Help', command: 'help' },
  ];

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Jarvis 100x
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={status === 'idle' ? 'secondary' : 'default'}>
              {status}
            </Badge>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setVoiceEnabled(!voiceEnabled)}
            >
              {voiceEnabled ? <Mic className="h-4 w-4" /> : <MicOff className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col gap-3 overflow-hidden">
        {/* Messages */}
        <ScrollArea className="flex-1" ref={scrollRef}>
          <div className="space-y-3">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-3 py-2 ${
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

        {/* Quick Commands */}
        <div className="flex flex-wrap gap-1">
          {quickCommands.map((cmd) => (
            <Button
              key={cmd.command}
              variant="outline"
              size="sm"
              className="h-6 text-xs"
              onClick={() => {
                setInput(cmd.command);
                setTimeout(() => sendMessage(), 100);
              }}
            >
              {cmd.label}
            </Button>
          ))}
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Ask Jarvis anything..."
            className="flex-1"
          />
          <Button onClick={sendMessage} size="icon">
            <Send className="h-4 w-4" />
          </Button>
        </div>

        {/* Events Feed */}
        {events.length > 0 && (
          <div className="border-t pt-2">
            <div className="text-xs font-medium mb-1 opacity-70">Recent Events</div>
            <div className="space-y-1">
              {events.slice(0, 3).map((event, i) => (
                <div key={i} className="text-xs flex items-center gap-1">
                  <span>
                    {event.severity === 'critical' ? '🔴' : event.severity === 'warning' ? '⚠️' : 'ℹ️'}
                  </span>
                  <span className="opacity-70">{event.title}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
"""

# Export the component code for reference
__all__ = ["COMPONENT_STRUCTURE", "JARVIS_PANEL_CODE"]
