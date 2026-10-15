import test from 'node:test'
import assert from 'node:assert/strict'
import { marketingEvent, referralSource } from '../lib/attribution.ts'

test('event construction requires consent and fixed public identifiers', () => {
  assert.equal(marketingEvent({ consented: false, page: '/', action: 'signup' }), null)
  assert.equal(marketingEvent({ consented: 'false', page: '/', action: 'signup' }), null)
  assert.equal(marketingEvent({ consented: true, page: '/accounts/private', action: 'signup' }), null)
  assert.equal(marketingEvent({ consented: true, page: '/?email=private', action: 'signup' }), null)
  assert.equal(marketingEvent({ consented: true, page: '/', action: 'custom-private-text' }), null)
})

test('referrer values and extraneous financial or identity data never reach an event', () => {
  const event = marketingEvent({ consented: true, page: '/features', action: 'signup',
    referrer: 'https://www.google.com/search?q=private-financial-text&token=secret', balance: 123, email: 'private' })
  assert.deepEqual(event, { name: 'marketing_cta_click', page_id: '/features', cta_id: 'signup', source: 'google' })
  assert.ok(!JSON.stringify(event).includes('private'))
  assert.equal(referralSource('https://google.com.evil.test/'), 'other')
  assert.equal(referralSource('https://user:secret@google.com/'), 'other')
  assert.equal(referralSource('javascript:alert(1)'), 'other')
  assert.equal(referralSource('https://chatgpt.com/?token=secret'), 'chatgpt')
  assert.equal(referralSource(undefined), 'direct_or_unknown')
})
