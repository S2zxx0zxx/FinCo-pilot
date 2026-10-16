import type { MetadataRoute } from 'next'
import { sitemapEntries } from '@/lib/marketing'

// Build-time indexability remains controlled by getMarketingConfig().
export const dynamic = 'force-static'

export default function sitemap(): MetadataRoute.Sitemap {
  return sitemapEntries()
}
