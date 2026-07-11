import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      'react-refresh/only-export-components': ['warn', { allowExportNames: ['badgeVariants', 'buttonVariants', 'toggleVariants', 'navigationMenuTriggerStyle', 'sidebarMenuButtonVariants', 'useBrand'] }],
    },
  },
  {
    files: ['src/components/ui/**/*.{ts,tsx}'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
  {
    files: ['src/components/graph/**/*.{ts,tsx}', 'src/components/llm/**/*.{ts,tsx}'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
  {
    files: ['src/components/todos/**/*.{ts,tsx}'],
    rules: {
      'react-hooks/incompatible-library': 'off',
    },
  },
])
