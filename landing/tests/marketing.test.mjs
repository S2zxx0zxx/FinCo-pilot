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
    /10,000 users trust|as seen on|SOC 2 certified|RBI approved/,
  )
  assert.match(read('app/layout.tsx'), /export const metadata/)
})
test('all CTA links stay on established product routes', () => {
  const p = read('components/landing-experience.tsx')
  for (const name of ['register', 'login', 'privacy', 'terms'])
    assert.ok(p.includes('APP_LINKS.' + name))
})
test('HeroUI v3 owns the full landing interface with no Ant runtime', () => {
  const home =
    read('components/landing-experience.tsx') +
    read('components/spending-playground.tsx')
  const product = read('components/product-screens.tsx')
  const deps = JSON.parse(read('package.json'))
  assert.match(home, /from '@heroui\/react'/)
  assert.match(product, /from '@heroui\/react'/)
  for (const component of [
    'Drawer.Dialog',
    'Disclosure.Trigger',
    'DisclosureGroup',
    'NumberField.Input',
    'Card.Header',
    'Meter.Track',
    'Alert.Content',
    'Chip',
    'Separator',
  ])
    assert.ok(home.includes(component))
  assert.match(product, /Tabs.List/)
  assert.match(product, /Tabs.Panel/)
  assert.equal(deps.dependencies['@heroui/react'], '3.2.6')
  assert.equal(deps.dependencies['@heroui/styles'], '3.2.6')
  for (const name of Object.keys({
    ...deps.dependencies,
    ...deps.devDependencies,
  }))
    assert.doesNotMatch(name, /antd|@ant-design/)
  assert.doesNotMatch(
    home + product + read('app/layout.tsx'),
    /antd|AntdRegistry|components\/spaceui|motion\/react|landing-sound|hero-backdrop/,
  )
  assert.match(read('app/globals.css'), /prefers-reduced-motion/)
  assert.match(home, /aria-expanded/)
  assert.match(home, /Skip to content/)
  assert.ok(
    existsSync(new URL('../SPACEUI-LICENSE.txt', import.meta.url)),
    'Retain historical component licenses',
  )
})

// Production Vite's /welcome export must keep Next.js metadata routes static.
// The route content remains build-time derived from the existing marketing policy.
test('robots and sitemap support Next.js 16 static marketing export', () => {
  for (const page of ['robots', 'sitemap']) {
    assert.match(
      read(`app/${page}.ts`),
      /export const dynamic = 'force-static'/,
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
      '/welcome/guides/import-transactions/',
    )
    delete process.env.NEXT_PUBLIC_FINCO_LANDING_BASE_PATH
    assert.equal(landingAsset('/features/'), '/features/')
  } finally {
    if (original === undefined)
      delete process.env.NEXT_PUBLIC_FINCO_LANDING_BASE_PATH
    else process.env.NEXT_PUBLIC_FINCO_LANDING_BASE_PATH = original
  }
  const home =
    read('components/landing-experience.tsx') +
    read('components/import-walkthrough.tsx')
  for (const destination of [
    'features/',
    'how-it-works/',
    'guides/import-transactions/',
  ]) {
    assert.ok(
      home.includes(`landingAsset('/${destination}')`),
      `Missing crawlable homepage link to ${destination}`,
    )
  }
})

test('the SSR hero heading has text nodes before hydration, not hidden-only tokens', () => {
  const reveal = read('components/spaceui/blur-reveal-text.tsx')
  assert.match(reveal, /staticReveal\s*\? <span key=\{/)
  assert.doesNotMatch(reveal, /staticReveal\s*\? <span[^>]+aria-hidden/)
  assert.match(
    read('components/landing-experience.tsx'),
    /<h1>\s*Bank balance\.\s*<br \/>\s*<span>Meet real life\.<\/span>\s*<\/h1>/,
  )
})

test('HeroUI styles are compiled with Tailwind in the documented order', () => {
  const css = read('app/globals.css')
  assert.ok(
    css.indexOf("@import 'tailwindcss'") <
      css.indexOf("@import '@heroui/styles'"),
  )
  assert.match(css, /@import '@heroui\/styles'/)
  assert.match(read('app/layout.tsx'), /import '.\/globals.css'/)
  assert.equal(
    JSON.parse(read('package.json')).scripts.build,
    'node scripts/marketing-content.mjs && next build',
  )
  for (const path of [
    'lib/ant-theme.ts',
    'scripts/ant-styles.mjs',
    'components/landing-theme.tsx',
  ])
    assert.ok(
      !existsSync(new URL('../' + path, import.meta.url)),
      'Remove superseded integration: ' + path,
    )
})
