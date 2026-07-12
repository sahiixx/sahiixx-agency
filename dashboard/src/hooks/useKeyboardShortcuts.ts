import { useEffect, useCallback, useRef, useLayoutEffect } from 'react';

export interface Shortcut {
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

export const JARVIS_SHORTCUTS: Record<string, Shortcut> = {
  VOICE_TOGGLE: { key: 'v', alt: true, description: 'Toggle voice input', action: () => {} },
  QUICK_STATUS: { key: '1', alt: true, description: 'Status command', action: () => {} },
  QUICK_HEALTH: { key: '2', alt: true, description: 'Health command', action: () => {} },
  QUICK_REGISTRY: { key: '3', alt: true, description: 'Registry command', action: () => {} },
  QUICK_TASKS: { key: '4', alt: true, description: 'Tasks command', action: () => {} },
  QUICK_MODULES: { key: '5', alt: true, description: 'Modules command', action: () => {} },
  QUICK_HELP: { key: '6', alt: true, description: 'Help command', action: () => {} },
  CLEAR_CHAT: { key: 'c', alt: true, description: 'Clear chat', action: () => {} },
  FOCUS_INPUT: { key: 'f', alt: true, description: 'Focus input', action: () => {} },
  DISMISS: { key: 'Escape', description: 'Close shortcuts', action: () => {} },
};

export type ShortcutKey = keyof typeof JARVIS_SHORTCUTS;

export function useKeyboardShortcuts({ shortcuts, enabled = true }: UseKeyboardShortcutsOptions) {
  const shortcutsRef = useRef(shortcuts);
  useLayoutEffect(() => {
    shortcutsRef.current = shortcuts;
  });

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
