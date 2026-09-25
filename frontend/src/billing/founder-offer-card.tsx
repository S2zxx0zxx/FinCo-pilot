import { CheckCircle2, Clock3, Users } from 'lucide-react'
import { formatInrMinor } from '@/billing/catalog'
import type { FounderCampaignStatus } from '@/billing/types'

export function FounderOfferCard({
  campaign,
}: {
  campaign: FounderCampaignStatus | null
}) {
  if (!campaign?.live || campaign.current_wave == null || campaign.current_amount_minor == null) {
    return null
  }

  const wave = campaign.waves.find((item) => item.wave === campaign.current_wave)
  if (!wave) return null

  const progress = wave.capacity > 0
    ? Math.min(100, Math.max(0, (wave.claimed / wave.capacity) * 100))
    : 0

  return (
    <section
      className="mb-5 overflow-hidden rounded-[26px] border border-foreground/20 bg-card shadow-[0_18px_55px_rgba(0,0,0,.08)]"
      aria-label={'Founder Wave ' + wave.wave + ' offer'}
    >
      <div className="p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
              Founding access · Wave {wave.wave}
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-4xl font-semibold tracking-[-0.04em]">
                {formatInrMinor(wave.amount_minor)}
              </span>
              <span className="text-sm text-muted-foreground">first 60 days of Pro</span>
            </div>
          </div>
          <div className="rounded-full border bg-background px-3 py-1.5 text-xs font-semibold">
            Next price {formatInrMinor(wave.next_amount_minor)}
          </div>
        </div>

        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          Pay the founder price once during pre-sale. Your 60-day Pro period starts
          at public launch, then the standard Pro price is ₹99/month until cancelled.
          Eligibility is confirmed by the server at checkout.
        </p>

        <div className="mt-5 h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-foreground transition-[width] duration-500"
            style={{ width: String(progress) + '%' }}
            aria-hidden="true"
          />
        </div>

        <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-3">
          <span className="inline-flex items-center gap-1.5">
            <CheckCircle2 className="size-3.5" />
            {wave.claimed.toLocaleString('en-IN')} verified
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Clock3 className="size-3.5" />
            {wave.held.toLocaleString('en-IN')} temporarily held
          </span>
          <span className="inline-flex items-center gap-1.5 sm:justify-end">
            <Users className="size-3.5" />
            {wave.available.toLocaleString('en-IN')} available
          </span>
        </div>
      </div>
    </section>
  )
}
