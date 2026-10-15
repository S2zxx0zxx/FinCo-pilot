import type { Metadata } from 'next'

export function pageMetadata(path: string, title: string, description: string): Metadata {
  return {
    title, description, alternates: { canonical: path },
    openGraph: { type: 'website', siteName: 'FinCo-Pilot', title, description, url: path,
      images: [{ url: '/social-card.png', width: 1200, height: 630, alt: 'FinCo-Pilot financial workspace' }] },
    twitter: { card: 'summary_large_image', title, description, images: ['/social-card.png'] },
  }
}
