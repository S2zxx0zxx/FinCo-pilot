import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './pwa/pwa.css'
import './transitions/finco-navigation-transition.css'
import { i18nReady } from './lib/i18n'
import { initRoutePreloading } from './transitions/route-preloader'
import App from './App.tsx'

// Warm lazy route chunks from hover/focus/pointer intent without prefetching
// private finance API data. The listener is installed once for the lifetime of
// the SPA, outside React StrictMode's development effect replay.
initRoutePreloading()

function retireBootSurface() {
  const boot = document.getElementById('finco-boot')
  if (!boot) return

  // Keep the zero-JS launch surface just long enough to bridge React's first
  // render and the 130ms lazy-route fallback threshold. This prevents a white
  // or empty flash on cold starts while remaining comfortably sub-second.
  requestAnimationFrame(() => {
    window.setTimeout(() => {
      boot.classList.add('finco-boot--leaving')
      window.setTimeout(() => boot.remove(), 220)
    }, 150)
  })
}

// Honour a persisted language before rendering any translated UI.
void i18nReady.then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
  retireBootSurface()
})
