import type { Metadata, Viewport } from 'next'
import localFont from 'next/font/local'
import './globals.css'

const fincoFont = localFont({
  src: [
    { path: '../public/fonts/open-runde/open-runde-regular.woff2', weight: '400' },
    { path: '../public/fonts/open-runde/open-runde-semibold.woff2', weight: '600' },
    { path: '../public/fonts/open-runde/open-runde-bold.woff2', weight: '700' },
  ], variable: '--font-finco', display: 'optional', preload: true,
})

const indexingEnabled = process.env.VERCEL_ENV === 'production' && process.env.NEXT_PUBLIC_MARKETING_INDEXABLE === 'true'

export const metadata: Metadata = {
  metadataBase: new URL('https://fincopilot.app'),
  title: 'FinCo-Pilot | Make sense of all your money',
  description: 'Understand accounts, track spending, plan budgets and keep your financial picture together in one thoughtful workspace.',
  applicationName: 'FinCo-Pilot',
  alternates: { canonical: '/' },
  robots: { index: indexingEnabled, follow: indexingEnabled },
  openGraph: {
    type: 'website',
    title: 'FinCo-Pilot | Clarity for your everyday finances',
    description: 'Less switching. Less second-guessing. One place to see, plan and understand your money.',
    siteName: 'FinCo-Pilot',
    url: '/',
    images: [{ url: '/social-card.png', width: 1200, height: 630, alt: 'FinCo-Pilot: Money makes more sense together.' }],
  },
  twitter: { card: 'summary_large_image', images: ['/social-card.png'] },
}
export const viewport: Viewport = { width: 'device-width', initialScale: 1, themeColor: '#080b0c' }
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className={fincoFont.variable}><body><div className="relative isolate min-h-svh">{children}</div></body></html>
}
