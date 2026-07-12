import { useEffect, useCallback, useRef } from 'react';

interface Shortcut {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  shift?: boolean;
  alt?: boolean;
  description: string;
  action: () => void;
}

interface UseKeyboardShortcutsOptions {
  shortcuts: Shortcut[];
  enabled?: boolean;
}

export function useKeyboardShortcuts({ shortcuts, enabled = true }: UseKeyboardShortcutsOptions) {
  const shortcutsRef = useRef(shortcuts);
  shortcutsRef.current = shortcuts;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      // Don't trigger shortcuts when typing in input/textarea
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        // Allow Escape and Ctrl/Cmd shortcuts in inputs
        if (event.key !== 'Escape' && !event.ctrlKey && !event.metaKey) {
          return;
        }
      }

      for (const shortcut of shortcutsRef.current) {
        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase();
        const ctrlMatch = shortcut.ctrl ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey;
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey;
        const altMatch = shortcut.alt ? event.altKey : !event.altKey;

        if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
          event.preventDefault();
          event.stopPropagation();
          shortcut.action();
          return;
        }
      }
    },
    [enabled]
  );

  useEffect(() => {
    if (enabled) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [handleKeyDown, enabled]);
}

// Predefined Jarvis shortcuts
export const JARVIS_SHORTCUTS = {
  VOICE_TOGGLE: { key: 'v', ctrl: true, description: 'Toggle voice input' },
  SEND_MESSAGE: { key: 'Enter', description: 'Send message' },
  QUICK_STATUS: { key: '1', alt: true, description: 'Quick status check' },
  QUICK_HEALTH: { key: '2', alt: true, description: 'Quick health check' },
  QUICK_REGISTRY: { key: '3', alt: true, description: 'Show registry' },
  QUICK_TASKS: { key: '4', alt: true, description: 'Show tasks' },
  QUICK_MODULES: { key: '5', alt: true, description: 'Show modules' },
  QUICK_HELP: { key: '6', alt: true, description: 'Show help' },
  CLEAR_CHAT: { key: 'k', ctrl: true, description: 'Clear chat' },
  FOCUS_INPUT: { key: '/', description: 'Focus input field' },
  DISMISS: { key: 'Escape', description: 'Dismiss/close' },
} as const;

export type ShortcutKey = keyof typeof JARVIS_SHORTCUTS;
