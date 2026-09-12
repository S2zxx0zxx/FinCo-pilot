import { useTranslation } from 'react-i18next'
import { FinCoLogo } from '@/components/finco-logo'

// Left-hand brand panel for the auth/onboarding screens. A true-black graphite
// field with a slow neutral glow behind an oversized translucent FinCo-Pilot
// mark. Decorative only — hidden below `lg`, where the form takes the full
// width and carries its own compact header.
export function AuthBrandPanel() {
  const { t } = useTranslation()

  return (
    <div
      className="relative hidden overflow-hidden p-12 text-white lg:flex lg:flex-col lg:justify-between"
      style={{
        background:
          'linear-gradient(150deg, #000000 0%, #050505 54%, #101010 100%)',
      }}
    >
      {/* Slow monochrome ambient glow */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="fincopilot-aurora fincopilot-aurora-1" />
        <div className="fincopilot-aurora fincopilot-aurora-2" />
        <div className="fincopilot-aurora fincopilot-aurora-3" />
      </div>

      {/* Oversized supplied F mark, bleeding off the lower-right edge. */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-28 -bottom-24 opacity-[0.055]"
        style={{ transform: 'rotate(-8deg)' }}
      >
        <FinCoLogo size={640} mode="on-dark" />
      </div>

      {/* Depth: gentle vignette toward the edges */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(115% 90% at 78% 8%, transparent 42%, rgba(0, 0, 0, 0.58) 100%)',
        }}
      />

      {/* Wordmark */}
      <div className="relative flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/[0.06]">
          <FinCoLogo size={20} mode="on-dark" />
        </div>
        <span className="text-lg font-semibold tracking-tight">FinCo-Pilot</span>
      </div>

      {/* Tagline */}
      <div className="relative max-w-md space-y-5">
        <h2 className="text-[2.6rem] font-semibold leading-[1.08] tracking-tight">
          {t('setup.brandTagline')}
        </h2>
        <p className="max-w-sm text-base leading-relaxed text-white/70">
          {t('setup.brandSubtitle')}
        </p>
        <div className="flex items-center gap-2.5 pt-1 text-xs font-medium text-white/55">
          <span>{t('setup.brandOpen')}</span>
          <span className="h-1 w-1 rounded-full bg-white/35" />
          <span>{t('setup.brandSelfHosted')}</span>
          <span className="h-1 w-1 rounded-full bg-white/35" />
          <span>{t('setup.brandPrivate')}</span>
        </div>
      </div>
    </div>
  )
}
