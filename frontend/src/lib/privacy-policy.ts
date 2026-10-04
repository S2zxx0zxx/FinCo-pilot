import { z } from 'zod'

export interface PrivacyPolicy {
  version: string
  reviewed_on: string
  status: 'draft' | 'published'
  effective_date: string | null
  operator: { brand_name: string; legal_name: string | null; entity_type: string; country_code: string }
  contact: { name: string | null; email: string | null; address: string | null }
  deployment: { providers: string | null; locations: string | null }
  sections: Array<{ id: string; title: { en: string; hi: string }; body: { en: string; hi: string } }>
}

const bilingual = z.object({ en: z.string(), hi: z.string() })
const policySchema = z.object({
  version: z.string(), reviewed_on: z.string(), status: z.enum(['draft', 'published']), effective_date: z.string().nullable(),
  operator: z.object({ brand_name: z.string(), legal_name: z.string().nullable(), entity_type: z.string(), country_code: z.string() }),
  contact: z.object({ name: z.string().nullable(), email: z.string().nullable(), address: z.string().nullable() }),
  deployment: z.object({ providers: z.string().nullable(), locations: z.string().nullable() }),
  sections: z.array(z.object({ id: z.string().regex(/^[a-z][a-z0-9-]*$/), title: bilingual, body: bilingual })),
})

export async function fetchPrivacyPolicy(): Promise<PrivacyPolicy> {
  // A public notice never needs auth/workspace headers or browser credentials.
  const response = await fetch('/api/privacy-policy', { cache: 'no-store', credentials: 'omit', headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error('Privacy notice unavailable')
  return policySchema.parse(await response.json())
}
