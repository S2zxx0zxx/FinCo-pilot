import type { Metadata, Viewport } from 'next'
import './globals.css'

const indexingEnabled = process.env.VERCEL_ENV === 'production' && process.env.NEXT_PUBLIC_MARKETING_INDEXABLE === 'true'

export const metadata: Metadata = {
  metadataBase: new URL('https://fincopilot.app'),
  title: 'FinCo-Pilot | Make sense of all your money',
  description: 'Understand accounts, track spending, plan budgets and keep your financial picture together in one thoughtful workspace.',
  applicationName: 'FinCo-Pilot',
  robots: { index: indexingEnabled, follow: indexingEnabled },
  openGraph: {
    type: 'website',
    title: 'FinCo-Pilot | Clarity for your everyday finances',
    description: 'Less switching. Less second-guessing. One place to see, plan and understand your money.',
    siteName: 'FinCo-Pilot',
  },
  twitter: { card: 'summary_large_image' },
}
export const viewport: Viewport = { width: 'device-width', initialScale: 1, themeColor: '#080b0c' }
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><div className="relative isolate min-h-svh">{children}</div></body></html>
}
