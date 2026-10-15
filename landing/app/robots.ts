import type { MetadataRoute } from 'next'
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
