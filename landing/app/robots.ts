import type { MetadataRoute } from 'next'
import { getMarketingConfig, RESTRICTED_CRAWLERS } from '@/lib/marketing'

// Prerender metadata for the same-origin static export; indexing stays opt-in.
export const dynamic = 'force-static'

export default function robots(): MetadataRoute.Robots {
  const { origin, indexable, basePath } = getMarketingConfig()
  if (!indexable) return { rules: { userAgent: '*', disallow: '/' } }
  return {
    rules: [
      { userAgent: '*', allow: '/', disallow: ['/api/', '/auth/', '/oauth/', '/i/'] },
      { userAgent: [...RESTRICTED_CRAWLERS], disallow: '/' },
    ],
    sitemap: `${origin}${basePath}/sitemap.xml`,
  }
}
