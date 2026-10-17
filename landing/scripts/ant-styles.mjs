import { mkdir, writeFile } from 'node:fs/promises'
import React from 'react'
import { ConfigProvider } from 'antd'
import { extractStyle } from '@ant-design/static-style-extract'
import { marketingTheme } from '../lib/ant-theme.ts'

// Compile only the public page's components. Runtime consumes these same tokens.
const css = extractStyle({
  includes: [
    'Alert',
    'Button',
    'Card',
    'Collapse',
    'Divider',
    'Drawer',
    'Flex',
    'InputNumber',
    'Progress',
    'Statistic',
    'Steps',
    'Tabs',
    'Tag',
  ],
  customTheme: (node) =>
    React.createElement(
      ConfigProvider,
      {
        theme: { ...marketingTheme, zeroRuntime: false },
      },
      node
    ),
})
if (
  css.length < 10000 ||
  !css.includes('.ant-btn') ||
  !css.includes('.ant-drawer')
) {
  throw new Error('Ant static stylesheet is incomplete')
}
await mkdir(new URL('../styles/', import.meta.url), { recursive: true })
await writeFile(new URL('../styles/antd.generated.css', import.meta.url), css)
console.log(`Generated ${Buffer.byteLength(css)} bytes of Ant component CSS`)
