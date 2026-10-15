import type { MetadataRoute } from 'next'

// The Vite deployment statically exports /welcome; Next.js must prerender this
// metadata route rather than treating it as a dynamic route handler.
export const dynamic = 'force-static'
import { getMarketingConfig, RESTRICTED_CRAWLERS } from '@/lib/marketing'

export default function robots(): MetadataRoute.Robots {
  const { origin, indexable } = getMarketingConfig()
  if (!indexable) return { rules: { userAgent: '*', disallow: '/' } }
  return {
    rules: [
      { userAgent: '*', allow: '/', disallow: ['/api/', '/auth/', '/oauth/', '/i/'] },
      { userAgent: [...RESTRICTED_CRAWLERS], disallow: '/' },
    ],
    sitemap: `${origin}/sitemap.xml`,
  }
}
