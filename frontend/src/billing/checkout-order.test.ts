import { expect, it } from 'vitest'
import { validCheckoutOrder } from './checkout-order'
const quote = { key_id: 'rzp_test_synthetic', order_id: 'order_Synthetic123', amount: 1900, currency: 'INR', plan: 'pro', interval: 'monthly', reservation_id: '01234567-89ab-cdef-0123-456789abcdef', reservation_expires_at: new Date(Date.now()+600000).toISOString(), service_period_days: 60, renewal_amount_minor: 9900 }
it('accepts the server-selected key and immutable founder quote', () => {
  expect(validCheckoutOrder(quote, 'pro', 'monthly')).toBe(true)
})
it.each([{key_id:'rzp_live_synthetic'}, {key_id:''}, {order_id:'https://evil.example'}, {amount:19.5}, {amount:0}, {currency:'USD'}, {plan:'max'}, {interval:'annual'}, {reservation_id:'forged'}, {reservation_expires_at:'invalid'}, {reservation_expires_at:'2020-01-01T00:00:00Z'}, {renewal_amount_minor:-1}])('refuses invalid or mismatched checkout %j', change => {
  expect(validCheckoutOrder({...quote,...change}, 'pro', 'monthly')).toBe(false)
})
