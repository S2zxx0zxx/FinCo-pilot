import { z } from 'zod'
import { policySchema } from './privacy-policy'

const decisions = z.object({ en: z.string().nullable(), hi: z.string().nullable() })
const termsSchema = policySchema.omit({ deployment: true }).extend({
  contact: policySchema.shape.contact.extend({ phone: z.string().nullable(), designation: z.string().nullable(), website: z.string().nullable() }),
  commercial: z.object({
    refund_policy: decisions, cancellation_policy: decisions,
    live_payments: z.literal(false), automatic_paid_activation: z.literal(false), recurring_billing: z.literal(false), automated_refunds: z.literal(false),
    tax_display_mode: z.string(),
    prices: z.array(z.object({ plan: z.string(), interval: z.string(), amount_minor: z.number().int().nonnegative(), currency: z.literal('INR') })),
  }),
})
export type TermsNotice = z.infer<typeof termsSchema>

export async function fetchTerms(): Promise<TermsNotice> {
  const response = await fetch('/api/terms', { cache: 'no-store', credentials: 'omit', headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error('Terms unavailable')
  return termsSchema.parse(await response.json())
}
