import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import Layout from './components/Layout'
import Home from './pages/Home'

function PatternsPage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="flex min-h-[100dvh] items-center justify-center"
    >
      <div className="text-center">
        <h1 className="font-display text-h1 mb-4 text-text-primary">Patterns</h1>
        <p className="text-body text-text-secondary">Coming Soon</p>
      </div>
    </motion.div>
  )
}

function TimelinePage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="flex min-h-[100dvh] items-center justify-center"
    >
      <div className="text-center">
        <h1 className="font-display text-h1 mb-4 text-text-primary">Timeline</h1>
        <p className="text-body text-text-secondary">Coming Soon</p>
      </div>
    </motion.div>
  )
}

export default function App() {
  const location = useLocation()

  return (
    <Layout>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Home />} />
          <Route path="/patterns" element={<PatternsPage />} />
          <Route path="/timeline" element={<TimelinePage />} />
        </Routes>
      </AnimatePresence>
    </Layout>
  )
}
