import type { Metadata } from 'next'
import { marketingSocialImage, marketingUrl } from './marketing'

export function pageMetadata(path: string, title: string, description: string): Metadata {
  const url = marketingUrl(path)
  const image = marketingSocialImage()
  return {
    title, description, alternates: { canonical: url },
    openGraph: { type: 'website', siteName: 'FinCo-Pilot', title, description, url,
      images: [{ url: image, width: 1200, height: 630, alt: 'FinCo-Pilot financial workspace' }] },
    twitter: { card: 'summary_large_image', title, description, images: [image] },
  }
}
