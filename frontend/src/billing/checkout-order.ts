import type { CheckoutOrder } from './types'

/** Validate the server quote before a third-party SDK receives it. */
export function validCheckoutOrder(value: unknown, plan: string, interval: string): value is CheckoutOrder {
  if (!value || typeof value !== 'object') return false
  const row = value as Record<string, unknown>
  return typeof row.key_id === 'string' && /^rzp_test_[A-Za-z0-9_]+$/.test(row.key_id)
    && typeof row.order_id === 'string' && /^order_[A-Za-z0-9]{1,80}$/.test(row.order_id)
    && Number.isSafeInteger(row.amount) && (row.amount as number) > 0
    && row.currency === 'INR' && row.plan === plan && row.interval === interval
    && typeof row.reservation_id === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(row.reservation_id)
    && typeof row.reservation_expires_at === 'string'
    && Date.parse(row.reservation_expires_at) > Date.now()
    && Number.isSafeInteger(row.service_period_days) && (row.service_period_days as number) > 0
    && Number.isSafeInteger(row.renewal_amount_minor) && (row.renewal_amount_minor as number) > 0
}
