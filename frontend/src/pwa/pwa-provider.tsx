import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import {
  PWAContext,
  type InstallOutcome,
  type PWAContextValue,
} from '@/pwa/pwa-context'

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>
}

function getDisplayModeQuery() {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return null
  return window.matchMedia('(display-mode: standalone)')
}

function standaloneMode() {
  if (typeof window === 'undefined') return false
  const iosStandalone = Boolean((window.navigator as Navigator & { standalone?: boolean }).standalone)
  return iosStandalone || Boolean(getDisplayModeQuery()?.matches)
}

function serviceWorkerContextAllowed() {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return false
  if (!('serviceWorker' in navigator)) return false

  // Service workers require a secure context. Browsers treat localhost as a
  // trustworthy development origin, so allow it explicitly for real install
  // testing without requiring a special Vite flag. A LAN http://192.168.x.x
  // URL is intentionally excluded: browsers cannot install a real PWA there;
  // use HTTPS for device testing instead of silently falling back to a shortcut.
  const hostname = window.location.hostname
  const localTrustworthyHost = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1'
  return window.isSecureContext || localTrustworthyHost
}

function syncThemeColor() {
  if (typeof document === 'undefined') return
  const dark = document.documentElement.classList.contains('dark')
  const color = dark ? '#000000' : '#FAFAFA'
  let meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"][data-finco-dynamic]')
  if (!meta) {
    meta = document.createElement('meta')
    meta.name = 'theme-color'
    meta.dataset.fincoDynamic = 'true'
    document.head.appendChild(meta)
  }
  meta.content = color
}

export function PWAProvider({ children }: { children: ReactNode }) {
  const [isOnline, setIsOnline] = useState(() => (typeof navigator === 'undefined' ? true : navigator.onLine))
  const [isStandalone, setIsStandalone] = useState(standaloneMode)
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null)
  const [updateReady, setUpdateReady] = useState(false)
  const registrationRef = useRef<ServiceWorkerRegistration | null>(null)
  const reloadForUpdateRef = useRef(false)

  useEffect(() => {
    const online = () => setIsOnline(true)
    const offline = () => setIsOnline(false)
    const installed = () => {
      setInstallPrompt(null)
      setIsStandalone(true)
    }
    const beforeInstall = (event: Event) => {
      const promptEvent = event as BeforeInstallPromptEvent
      promptEvent.preventDefault()
      setInstallPrompt(promptEvent)
    }
    const displayMode = getDisplayModeQuery()
    const displayChanged = () => setIsStandalone(standaloneMode())

    window.addEventListener('online', online)
    window.addEventListener('offline', offline)
    window.addEventListener('appinstalled', installed)
    window.addEventListener('beforeinstallprompt', beforeInstall)
    displayMode?.addEventListener?.('change', displayChanged)

    return () => {
      window.removeEventListener('online', online)
      window.removeEventListener('offline', offline)
      window.removeEventListener('appinstalled', installed)
      window.removeEventListener('beforeinstallprompt', beforeInstall)
      displayMode?.removeEventListener?.('change', displayChanged)
    }
  }, [])

  useEffect(() => {
    syncThemeColor()
    if (typeof MutationObserver === 'undefined') return
    const observer = new MutationObserver(syncThemeColor)
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const pwaEnabled = import.meta.env.PROD || import.meta.env.VITE_PWA_DEV === 'true' || ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)
    if (!pwaEnabled || !serviceWorkerContextAllowed()) return

    let disposed = false

    const watchRegistration = (registration: ServiceWorkerRegistration) => {
      registrationRef.current = registration
      if (registration.waiting && navigator.serviceWorker.controller) setUpdateReady(true)

      registration.addEventListener('updatefound', () => {
        const installing = registration.installing
        if (!installing) return
        installing.addEventListener('statechange', () => {
          if (installing.state === 'installed' && navigator.serviceWorker.controller) {
            setUpdateReady(true)
          }
        })
      })
    }

    navigator.serviceWorker
      .register('/sw.js', { scope: '/', updateViaCache: 'none' })
      .then(async (registration) => {
        if (disposed) return
        watchRegistration(registration)
        // `ready` confirms the worker is active for this origin. This matters
        // for installability on Chromium/WebAPK flows and avoids presenting a
        // browser-home-screen shortcut as if it were an installed app.
        await navigator.serviceWorker.ready
        if (!disposed) void registration.update()
      })
      .catch(() => {
        // PWA enhancement must never stop the finance app from booting.
      })

    const controllerChanged = () => {
      if (reloadForUpdateRef.current) window.location.reload()
    }
    navigator.serviceWorker.addEventListener('controllerchange', controllerChanged)

    const refreshWorker = () => {
      if (document.visibilityState === 'visible' && navigator.onLine) {
        void registrationRef.current?.update()
      }
    }
    document.addEventListener('visibilitychange', refreshWorker)
    window.addEventListener('online', refreshWorker)

    return () => {
      disposed = true
      navigator.serviceWorker.removeEventListener('controllerchange', controllerChanged)
      document.removeEventListener('visibilitychange', refreshWorker)
      window.removeEventListener('online', refreshWorker)
    }
  }, [])

  const install = useCallback(async (): Promise<InstallOutcome> => {
    if (!installPrompt) return 'unavailable'
    await installPrompt.prompt()
    const choice = await installPrompt.userChoice
    if (choice.outcome === 'accepted') setInstallPrompt(null)
    return choice.outcome
  }, [installPrompt])

  const applyUpdate = useCallback(() => {
    const waiting = registrationRef.current?.waiting
    if (!waiting) return
    reloadForUpdateRef.current = true
    waiting.postMessage({ type: 'SKIP_WAITING' })
  }, [])

  const value = useMemo<PWAContextValue>(
    () => ({
      isOnline,
      isStandalone,
      canInstall: Boolean(installPrompt) && !isStandalone,
      updateReady,
      install,
      applyUpdate,
    }),
    [applyUpdate, install, installPrompt, isOnline, isStandalone, updateReady],
  )

  return <PWAContext.Provider value={value}>{children}</PWAContext.Provider>
}
