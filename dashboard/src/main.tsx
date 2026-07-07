import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import { ThemeProvider } from 'next-themes'
import './index.css'
import App from './App.tsx'
import { BrandProvider } from './components/BrandProvider'

createRoot(document.getElementById('root')!).render(
  <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
    <HashRouter>
      <BrandProvider>
        <App />
      </BrandProvider>
    </HashRouter>
  </ThemeProvider>,
)
