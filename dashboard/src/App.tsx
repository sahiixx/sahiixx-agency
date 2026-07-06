import { Component, type ReactNode } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Toaster } from 'sonner'
import Layout from './components/Layout'
import Home from './pages/Home'
import { TodoPage } from './components/todos/TodoPage'
import { ContactPage } from './components/contact/ContactPage'
import { AboutPage } from './components/about/AboutPage'
import { NotFoundPage } from './components/NotFoundPage'

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
      <Layout>
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<Home />} />
            <Route path="/todos" element={<TodoPage />} />
            <Route path="/contact" element={<ContactPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/patterns" element={<PatternsPage />} />
            <Route path="/timeline" element={<TimelinePage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AnimatePresence>
      </Layout>
    </ErrorBoundary>
  )
}
