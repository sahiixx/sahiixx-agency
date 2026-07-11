import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import { inspectAttr } from 'plugin-inspect-react-code'

// https://vite.dev/config/
export default defineConfig({
  base: './',
  plugins: [inspectAttr(), react()],
  server: {
    port: 3000,
    proxy: {
      '/dashboard/graph-data': 'http://localhost:8082',
      '/api': {
        target: 'http://localhost:8082',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-ui': ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu', '@radix-ui/react-tabs', '@radix-ui/react-select', '@radix-ui/react-popover', '@radix-ui/react-navigation-menu', '@radix-ui/react-tooltip', 'framer-motion'],
          'vendor-charts': ['recharts', 'd3'],
          'vendor-utils': ['fuse.js', 'zod', 'sonner', 'date-fns', 'react-hook-form', '@hookform/resolvers'],
          'vendor-icons': ['lucide-react'],
          'vendor-gsap': ['gsap', '@gsap/react', 'lenis'],
        },
      },
    },
  },
});
