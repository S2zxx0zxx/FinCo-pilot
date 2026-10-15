import type { MetadataRoute } from 'next'
import { sitemapEntries } from '@/lib/marketing'

export default function sitemap(): MetadataRoute.Sitemap {
  return sitemapEntries()
}
