import type { MetadataRoute } from 'next'

// Required for Next.js static export of the same-origin /welcome landing.
// Build-time indexability remains controlled by getMarketingConfig().
export const dynamic = 'force-static'
import { sitemapEntries } from '@/lib/marketing'

export default function sitemap(): MetadataRoute.Sitemap {
  return sitemapEntries()
}
