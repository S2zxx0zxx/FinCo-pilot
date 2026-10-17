import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { landingAsset } from '../lib/asset.ts'
const read = (path) =>
  readFileSync(new URL('../' + path, import.meta.url), 'utf8')

test('product sign-in and registration stay in the original Vite application', () => {
  const links = read('lib/links.ts')
  assert.match(links, /new URL\('\/login', APP_URL\)/)
  assert.match(links, /new URL\('\/register', APP_URL\)/)
  assert.match(links, /https:\/\/fincopilot\.app/)
  assert.doesNotMatch(links, /CLERK_SECRET_KEY|DATABASE_URL/)
})
test('real sections, metadata, and no fabricated social proof', () => {
  const p =
    read('components/landing-experience.tsx') +
    read('components/product-screens.tsx')
  for (const section of [
    'why-finco',
    'experience',
    'how-it-works',
    'questions',
  ])
    assert.ok(p.includes(section))
  for (const section of [
    'Hero',
    'ProductPreview',
    'WhyFinCo',
    'Experience',
    'HowItWorks',
    'Privacy',
    'Questions',
    'FinalCTA',
  ])
    assert.ok(p.includes('function ' + section))
  assert.match(p, /Illustrative interface/)
  assert.doesNotMatch(
    p,
    /10,000 users trust|as seen on|SOC 2 certified|RBI approved/
  )
  assert.match(read('app/layout.tsx'), /export const metadata/)
})
test('all CTA links stay on established product routes', () => {
  const p = read('components/landing-experience.tsx')
  for (const name of ['register', 'login', 'privacy', 'terms'])
    assert.ok(p.includes('APP_LINKS.' + name))
})
test('Ant Design controls replace the homepage Space UI layer with SSR styles', () => {
  const home = read('components/landing-experience.tsx')
  const product = read('components/product-screens.tsx')
  assert.doesNotMatch(
    home + product,
    /components\/spaceui|motion\/react|landing-sound|hero-backdrop/
  )
  assert.match(home, /from 'antd\/es\//)
  for (const component of [
    'Drawer',
    'Collapse',
    'Steps',
    'InputNumber',
    'Statistic',
  ])
    assert.ok(home.includes(component))
  assert.match(product, /from 'antd\/es\//)
  assert.match(read('app/layout.tsx'), /<AntdRegistry>/)
  assert.match(read('components/landing-theme.tsx'), /<ConfigProvider/)
  assert.match(read('app/globals.css'), /prefers-reduced-motion/)
  assert.match(home, /aria-expanded/)
  assert.match(home, /Skip to content/)
  assert.ok(
    existsSync(new URL('../SPACEUI-LICENSE.txt', import.meta.url)),
    'Retain licenses for historical unused components'
  )
})

// Production Vite's /welcome export must keep Next.js metadata routes static.
// The route content remains build-time derived from the existing marketing policy.
test('robots and sitemap support Next.js 16 static marketing export', () => {
  for (const page of ['robots', 'sitemap']) {
    assert.match(
      read(`app/${page}.ts`),
      /export const dynamic = 'force-static'/
    )
  }
  assert.match(read('lib/marketing.ts'), /NEXT_PUBLIC_MARKETING_INDEXABLE/)
})

test('homepage footer links remain in the actual exported marketing namespace', () => {
  const original = process.env.NEXT_PUBLIC_FINCO_LANDING_BASE_PATH
  try {
    process.env.NEXT_PUBLIC_FINCO_LANDING_BASE_PATH = '/welcome'
    assert.equal(landingAsset('/features/'), '/welcome/features/')
    assert.equal(landingAsset('/how-it-works/'), '/welcome/how-it-works/')
    assert.equal(
      landingAsset('/guides/import-transactions/'),
      '/welcome/guides/import-transactions/'
    )
    delete process.env.NEXT_PUBLIC_FINCO_LANDING_BASE_PATH
    assert.equal(landingAsset('/features/'), '/features/')
  } finally {
    if (original === undefined)
      delete process.env.NEXT_PUBLIC_FINCO_LANDING_BASE_PATH
    else process.env.NEXT_PUBLIC_FINCO_LANDING_BASE_PATH = original
  }
  const home = read('components/landing-experience.tsx')
  for (const destination of [
    'features/',
    'how-it-works/',
    'guides/import-transactions/',
  ]) {
    assert.ok(
      home.includes(`landingAsset('/${destination}')`),
      `Missing crawlable homepage link to ${destination}`
    )
  }
})

test('the SSR hero heading has text nodes before hydration, not hidden-only tokens', () => {
  const reveal = read('components/spaceui/blur-reveal-text.tsx')
  assert.match(reveal, /staticReveal\s*\? <span key=\{/)
  assert.doesNotMatch(reveal, /staticReveal\s*\? <span[^>]+aria-hidden/)
  assert.match(
    read('components/landing-experience.tsx'),
    /<h1>\s*Bank balance\.\s*<br \/>\s*<span>Meet real life\.<\/span>\s*<\/h1>/
  )
})


test('Ant runtime and static stylesheet share the same fixed theme', () => {
  const theme = read('lib/ant-theme.ts')
  assert.match(theme, /zeroRuntime: true/)
  assert.match(theme, /hashed: false/)
  assert.match(theme, /key: 'finco-marketing'/)
  assert.match(read('scripts/ant-styles.mjs'), /includes:/)
  assert.match(read('scripts/ant-styles.mjs'), /marketingTheme, zeroRuntime: false/)
  assert.match(read('app/layout.tsx'), /antd.generated.css/)
  assert.match(read('package.json'), /\"prebuild\": \"node scripts\/ant-styles.mjs\"/)
})
