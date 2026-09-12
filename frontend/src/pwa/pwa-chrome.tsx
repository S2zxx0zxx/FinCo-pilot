import { useEffect, useMemo, useState } from 'react'
import { Download, RefreshCw, Share2, WifiOff, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { FinCoLogo } from '@/components/finco-logo'
import { Button } from '@/components/ui/button'
import { usePWA } from '@/pwa/pwa-provider'

const INSTALL_DISMISS_KEY = 'finco:pwa-install-dismissed-at'
const INSTALL_SNOOZE_MS = 7 * 24 * 60 * 60 * 1000

function isIOSDevice() {
  if (typeof navigator === 'undefined') return false
  return (
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  )
}

export function PWAChrome() {
  const { t } = useTranslation()
  const { isOnline, canInstall, isStandalone, updateReady, install, applyUpdate } = usePWA()
  const [showInstall, setShowInstall] = useState(false)
  const ios = useMemo(isIOSDevice, [])

  useEffect(() => {
    if (isStandalone || (!canInstall && !ios)) {
      setShowInstall(false)
      return
    }

    const dismissedAt = Number(localStorage.getItem(INSTALL_DISMISS_KEY) || 0)
    if (Date.now() - dismissedAt < INSTALL_SNOOZE_MS) return

    const timer = window.setTimeout(() => setShowInstall(true), 5000)
    return () => window.clearTimeout(timer)
  }, [canInstall, ios, isStandalone])

  const dismissInstall = () => {
    localStorage.setItem(INSTALL_DISMISS_KEY, String(Date.now()))
    setShowInstall(false)
  }

  const handleInstall = async () => {
    const outcome = await install()
    if (outcome !== 'unavailable') setShowInstall(false)
  }

  return (
    <>
      {!isOnline && (
        <div
          className="finco-network-banner"
          role="status"
          aria-live="polite"
        >
          <WifiOff size={14} aria-hidden="true" />
          <span>{t('pwa.offline', { defaultValue: 'Offline — reconnect to refresh financial data' })}</span>
        </div>
      )}

      {updateReady && (
        <aside className="finco-pwa-card" aria-live="polite">
          <div className="finco-pwa-card__mark" aria-hidden="true">
            <FinCoLogo size={22} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="finco-pwa-card__title">
              {t('pwa.updateReady', { defaultValue: 'FinCo-Pilot update ready' })}
            </p>
            <p className="finco-pwa-card__copy">
              {t('pwa.updateReadyHint', { defaultValue: 'Apply the new version when you are ready.' })}
            </p>
          </div>
          <Button size="sm" onClick={applyUpdate} className="shrink-0 gap-1.5">
            <RefreshCw size={13} aria-hidden="true" />
            {t('pwa.update', { defaultValue: 'Update' })}
          </Button>
        </aside>
      )}

      {!updateReady && showInstall && canInstall && (
        <aside className="finco-pwa-card" aria-live="polite">
          <div className="finco-pwa-card__mark" aria-hidden="true">
            <FinCoLogo size={22} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="finco-pwa-card__title">
              {t('pwa.installTitle', { defaultValue: 'Install FinCo-Pilot' })}
            </p>
            <p className="finco-pwa-card__copy">
              {t('pwa.installHint', { defaultValue: 'Launch faster in a clean standalone app window.' })}
            </p>
          </div>
          <Button size="sm" onClick={handleInstall} className="shrink-0 gap-1.5">
            <Download size={13} aria-hidden="true" />
            {t('pwa.install', { defaultValue: 'Install' })}
          </Button>
          <button
            type="button"
            className="finco-pwa-card__dismiss"
            onClick={dismissInstall}
            aria-label={t('common.close', { defaultValue: 'Close' })}
          >
            <X size={14} />
          </button>
        </aside>
      )}

      {!updateReady && showInstall && !canInstall && ios && (
        <aside className="finco-pwa-card" aria-live="polite">
          <div className="finco-pwa-card__mark" aria-hidden="true">
            <Share2 size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="finco-pwa-card__title">
              {t('pwa.installIOS', { defaultValue: 'Install FinCo-Pilot on iPhone' })}
            </p>
            <p className="finco-pwa-card__copy">
              {t('pwa.installIOSHint', { defaultValue: 'Open Share, then choose Add to Home Screen.' })}
            </p>
          </div>
          <button
            type="button"
            className="finco-pwa-card__dismiss"
            onClick={dismissInstall}
            aria-label={t('common.close', { defaultValue: 'Close' })}
          >
            <X size={14} />
          </button>
        </aside>
      )}
    </>
  )
}
