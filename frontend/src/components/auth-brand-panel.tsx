import { useTranslation } from 'react-i18next'
import { FinCoLogo } from '@/components/finco-logo'
import { IdentityAvatar } from '@/components/spaceui/identity-avatar'
import { BlurRevealText } from '@/components/spaceui/blur-reveal-text'

// Space UI two-tone sign-in brand composition, hidden below lg so the real
// authentication form owns the entire mobile screen.
export function AuthBrandPanel() {
  const { t } = useTranslation()

  return (
    <div
      className="relative rounded-3xl bg-muted [corner-shape:superellipse(1.25)] hidden overflow-hidden p-12 text-foreground lg:flex lg:flex-col lg:justify-between min-h-[36rem]"
    >

      {/* Oversized supplied F mark, bleeding off the lower-right edge. */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-28 -bottom-24 opacity-[0.055]"
        style={{ transform: 'rotate(-8deg)' }}
      >
        <FinCoLogo size={640} mode="on-dark" />
      </div>


      {/* Wordmark */}
      <div className="relative flex items-center gap-2.5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-card">
          <FinCoLogo size={20} />
        </div>
        <span className="text-lg font-semibold tracking-tight">FinCo-Pilot</span>
      </div>

      {/* Tagline */}
      <div className="relative max-w-md space-y-5">
        <IdentityAvatar seed="finco-welcome" size={72} className="size-[72px] mb-6" />
        <h2 className="text-[2.6rem] font-semibold leading-[1.08] tracking-tight">
          <BlurRevealText text={t('setup.brandTagline')} />
        </h2>
        <p className="max-w-sm text-base leading-relaxed text-muted-foreground">
          {t('setup.brandSubtitle')}
        </p>
        <div className="flex items-center gap-2.5 pt-1 text-xs font-medium text-muted-foreground">
          <span>{t('setup.brandOpen')}</span>
          <span className="h-1 w-1 rounded-full bg-foreground/30" />
          <span>{t('setup.brandSelfHosted')}</span>
          <span className="h-1 w-1 rounded-full bg-foreground/30" />
          <span>{t('setup.brandPrivate')}</span>
        </div>
      </div>
    </div>
  )
}
