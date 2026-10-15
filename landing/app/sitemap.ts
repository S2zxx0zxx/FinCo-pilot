import type { MetadataRoute } from 'next'
import { sitemapEntries } from '@/lib/marketing'

export const dynamic = 'force-static'

export default function sitemap(): MetadataRoute.Sitemap {
  return sitemapEntries()
}
