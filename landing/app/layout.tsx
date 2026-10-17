import type { Metadata, Viewport } from 'next'
import localFont from 'next/font/local'
import { AntdRegistry } from '@ant-design/nextjs-registry'
import '../styles/antd.generated.css'
import './globals.css'
import {
  getMarketingConfig,
  marketingUrl,
  marketingSocialImage,
  serializeJsonLd,
  websiteSchema,
} from '@/lib/marketing'

const fincoFont = localFont({
  src: [
    {
      path: '../public/fonts/open-runde/open-runde-regular.woff2',
      weight: '400',
    },
    {
      path: '../public/fonts/open-runde/open-runde-semibold.woff2',
      weight: '600',
    },
    { path: '../public/fonts/open-runde/open-runde-bold.woff2', weight: '700' },
  ],
  variable: '--font-finco',
  display: 'optional',
  preload: true,
})

const marketing = getMarketingConfig()

export const metadata: Metadata = {
  metadataBase: new URL(marketing.origin),
  title: 'FinCo-Pilot | Your money, with context',
  description:
    'Understand accounts, track spending, plan budgets and keep your financial picture together in one thoughtful workspace.',
  applicationName: 'FinCo-Pilot',
  alternates: { canonical: marketingUrl('/') },
  robots: { index: marketing.indexable, follow: marketing.indexable },
  openGraph: {
    type: 'website',
    title: 'FinCo-Pilot | Your money, with context',
    description:
      'Bring accounts, bills, budgets and goals into focus before your next money decision.',
    siteName: 'FinCo-Pilot',
    url: marketingUrl('/'),
    images: [
      {
        url: marketingSocialImage(),
        width: 1200,
        height: 630,
        alt: 'FinCo-Pilot: Your money, with context.',
      },
    ],
  },
  twitter: { card: 'summary_large_image', images: [marketingSocialImage()] },
}
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#ffffff',
}
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={fincoFont.variable}>
      <body>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: serializeJsonLd(websiteSchema()) }}
        />
        <AntdRegistry>
          <div className="relative isolate min-h-svh">{children}</div>
        </AntdRegistry>
      </body>
    </html>
  )
}
