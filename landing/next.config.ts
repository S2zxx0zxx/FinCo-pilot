import type { NextConfig } from 'next'
const exporting = process.env.FINCO_EXPORT_MARKETING === 'true'
const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  ...(exporting ? {
    output: 'export', basePath: '/welcome', trailingSlash: true,
    distDir: '.next-export', images: { unoptimized: true },
  } : {
    async headers() {
      return [{ source: '/:path*', headers: [
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
      ] }]
    },
  }),
}
export default nextConfig
