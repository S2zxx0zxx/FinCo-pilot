import { useTranslation } from 'react-i18next'
import { useBilling } from '@/contexts/billing-context'
import { useDisplayLocale } from '@/hooks/use-display-locale'
import { METRIC_LABELS } from '@/billing/catalog'
import type { Metric } from '@/billing/types'
import { Frame, FrameHeader, FrameTitle, FramePanel } from '@/components/ui/frame'
import { Meter, MeterTrack, MeterIndicator } from '@/components/ui/meter'
import { IdentityAvatar } from '@/components/spaceui/identity-avatar'

const DISPLAY_METRICS: Metric[] = ['accounts', 'active_budgets', 'active_goals', 'imports_monthly', 'ai_actions_monthly']

/** Space UI usage interaction composed with genuine server entitlement data.
 * No showcase presets, autonomous toggles or invented telemetry are imported.
 */
export function UsageCard() {
  const { entitlements } = useBilling()
  const { t } = useTranslation()
  const locale = useDisplayLocale()
  if (!entitlements) return null
  const metrics = DISPLAY_METRICS.filter(metric => typeof entitlements.usage[metric] === 'number')
  if (!metrics.length) return null
  const number = new Intl.NumberFormat(locale)
  return <Frame className="mx-auto my-6 max-w-3xl rounded-3xl p-1.5 shadow-none">
    <FrameHeader className="flex-row items-center gap-3 px-3 py-3">
      <IdentityAvatar seed="finco-plan-usage" size={28} className="size-7" />
      <FrameTitle>{t('frontend.planUsage')}</FrameTitle>
      <span className="ml-auto text-xs font-medium uppercase text-muted-foreground">{entitlements.plan}</span>
    </FrameHeader>
    <FramePanel className="finco-surface grid gap-5 p-5 sm:grid-cols-2">
      {metrics.map(metric => {
        const used = entitlements.usage[metric]!
        const limit = entitlements.limits[metric]
        const bounded = limit > 0
        return <div key={metric} className="space-y-2">
          <div className="flex items-center justify-between gap-3 text-sm">
            <span>{t(`frontend.metrics.${metric}`, { defaultValue: METRIC_LABELS[metric] })}</span>
            <span className="tabular-nums text-muted-foreground">{number.format(used)}{bounded ? ` / ${number.format(limit)}` : ''}</span>
          </div>
          {bounded && <Meter aria-label={t(`frontend.metrics.${metric}`, { defaultValue: METRIC_LABELS[metric] })}
            value={Math.min(used, limit)} min={0} max={limit}>
            <MeterTrack className="h-1.5 rounded-full bg-muted"><MeterIndicator className="rounded-full" /></MeterTrack>
          </Meter>}
        </div>
      })}
    </FramePanel>
  </Frame>
}
