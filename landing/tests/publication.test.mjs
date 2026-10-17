import test from 'node:test'
import assert from 'node:assert/strict'
import { CANONICAL_MARKETING_ORIGIN, marketingPublicationEnv } from '../../frontend/scripts/marketing-publication-policy.mjs'

const release = {
  VERCEL_ENV: 'production',
  NEXT_PUBLIC_MARKETING_URL: CANONICAL_MARKETING_ORIGIN,
  FINCO_MARKETING_PUBLICATION_APPROVED: 'true',
}

test('all unapproved, preview and unknown environments are excluded', () => {
  assert.equal(marketingPublicationEnv({}).NEXT_PUBLIC_MARKETING_INDEXABLE, 'false')
  assert.equal(marketingPublicationEnv({ VERCEL_ENV: 'production' }).NEXT_PUBLIC_MARKETING_INDEXABLE, 'false')
  for (const env of [{ VERCEL_ENV: 'preview' }, { VERCEL_ENV: 'development' }]) {
    assert.equal(marketingPublicationEnv(env).NEXT_PUBLIC_MARKETING_INDEXABLE, 'false')
  }
  assert.throws(() => marketingPublicationEnv({ NEXT_PUBLIC_MARKETING_INDEXABLE: 'true' }))
})

test('publication requires both an approved apex and actual production release', () => {
  assert.deepEqual(marketingPublicationEnv(release), {
    NEXT_PUBLIC_MARKETING_INDEXABLE: 'true',
    NEXT_PUBLIC_MARKETING_URL: CANONICAL_MARKETING_ORIGIN,
  })
  for (const alteration of [
    { VERCEL_ENV: 'preview' }, { VERCEL_ENV: undefined },
    { NEXT_PUBLIC_MARKETING_URL: 'https://www.fincopilot.app' },
    { NEXT_PUBLIC_MARKETING_URL: 'https://some-branch.vercel.app' },
    { NEXT_PUBLIC_MARKETING_URL: undefined },
  ]) {
    assert.throws(() => marketingPublicationEnv({ ...release, ...alteration }))
  }
  assert.throws(() => marketingPublicationEnv({ ...release, FINCO_MARKETING_PUBLICATION_APPROVED: 'false', NEXT_PUBLIC_MARKETING_INDEXABLE: 'true' }))
})
