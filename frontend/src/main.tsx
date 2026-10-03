import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './pwa/pwa.css'
import './transitions/finco-navigation-transition.css'
import { i18nReady } from './lib/i18n'
import { initRoutePreloading } from './transitions/route-preloader'
import App from './App.tsx'
import { AppErrorBoundary } from '@/components/app-error-boundary'

// Warm lazy route chunks from hover/focus/pointer intent without prefetching
// private finance API data. The listener is installed once for the lifetime of
// the SPA, outside React StrictMode's development effect replay.
initRoutePreloading()

function retireBootSurface() {
  const boot = document.getElementById('finco-boot')
  if (!boot) return

  // React has committed its first UI. Fade the zero-JS boot surface immediately
  // instead of holding it on screen for an artificial minimum duration.
  window.requestAnimationFrame(() => {
    boot.classList.add('finco-boot--leaving')
    window.setTimeout(() => boot.remove(), 120)
  })
}

// Honour a persisted language before rendering any translated UI.
void i18nReady.then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <AppErrorBoundary><App /></AppErrorBoundary>
    </StrictMode>,
  )
  retireBootSurface()
})
