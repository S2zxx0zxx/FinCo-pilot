'use client'

import ConfigProvider from 'antd/es/config-provider'
import type { ReactNode } from 'react'
import { marketingTheme } from '@/lib/ant-theme'

/** Public-only Ant tokens; component CSS is generated during the build. */
export function LandingTheme({ children }: { children: ReactNode }) {
  return <ConfigProvider theme={marketingTheme}>{children}</ConfigProvider>
}
