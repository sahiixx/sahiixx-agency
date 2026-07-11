import { Component, type ReactNode } from 'react'
import { Routes, Route, useLocation, Navigate } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Toaster } from 'sonner'
import Layout from './components/Layout'
import Home from './pages/Home'
import Agency from './pages/Agency'
import Workflows from './pages/Workflows'
import Metrics from './pages/Metrics'
import LLMPage from './components/llm/LLMPage'
import MarketplacePage from './pages/Marketplace'
import { JarvisPage } from './components/jarvis/JarvisPage'
import { JarvisGUI } from './components/jarvis/JarvisGUI'
import { TodoPage } from './components/todos/TodoPage'
import { ContactPage } from './components/contact/ContactPage'
import { AboutPage } from './components/about/AboutPage'
import { NotFoundPage } from './components/NotFoundPage'
import { useNotificationStream } from './hooks/useNotificationStream'

function NotificationProvider({ children }: { children: ReactNode }) {
  useNotificationStream()
  return children
}

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[100dvh] flex items-center justify-center">
          <div className="text-center">
            <h1 className="font-display text-2xl text-text-primary mb-2">Something went wrong</h1>
            <p className="text-text-secondary mb-4">An unexpected error occurred.</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-lg bg-accent-cyan text-white"
            >
              Reload Page
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

function PatternsPage() {
  return (
    <div className="min-h-[100dvh] flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="rounded-full bg-accent-purple/10 p-4 inline-flex mb-6">
          <span className="text-4xl">🔬</span>
        </div>
        <h1 className="font-display text-3xl font-bold text-text-primary mb-2">Patterns</h1>
        <p className="text-text-secondary">
          Explore emerging patterns and trends across the AI landscape. Coming soon.
        </p>
      </div>
    </div>
  )
}

function TimelinePage() {
  return (
    <div className="min-h-[100dvh] flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="rounded-full bg-accent-amber/10 p-4 inline-flex mb-6">
          <span className="text-4xl">📅</span>
        </div>
        <h1 className="font-display text-3xl font-bold text-text-primary mb-2">Timeline</h1>
        <p className="text-text-secondary">
          Track the evolution of AI technologies over time. Coming soon.
        </p>
      </div>
    </div>
  )
}

export default function App() {
  const location = useLocation()

  return (
    <ErrorBoundary>
      <Toaster position="bottom-right" richColors />
      <NotificationProvider>
        <Layout>
          <AnimatePresence mode="wait">
            <Routes location={location} key={location.pathname}>
              <Route path="/" element={<Agency />} />
              <Route path="/graph" element={<Home />} />
              <Route path="/chat" element={<Navigate to="/" replace />} />
              <Route path="/tasks" element={<Agency />} />
              <Route path="/discovery" element={<Agency />} />
              <Route path="/approvals" element={<Agency />} />
              <Route path="/memory" element={<Agency />} />
              <Route path="/workflows" element={<Workflows />} />
              <Route path="/metrics" element={<Metrics />} />
              <Route path="/llm" element={<LLMPage />} />
              <Route path="/marketplace" element={<MarketplacePage />} />
              <Route path="/jarvis" element={<JarvisPage />} />
              <Route path="/jarvis/gui" element={<JarvisGUI />} />
              <Route path="/todos" element={<TodoPage />} />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="/patterns" element={<PatternsPage />} />
              <Route path="/timeline" element={<TimelinePage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </AnimatePresence>
        </Layout>
      </NotificationProvider>
    </ErrorBoundary>
  )
}
