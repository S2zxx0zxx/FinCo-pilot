import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
const read = (path) => readFileSync(new URL('../' + path, import.meta.url), 'utf8')

test('product sign-in and registration stay in the original Vite application', () => {
  const links = read('lib/links.ts')
  assert.match(links, /new URL\('\/login', APP_URL\)/)
  assert.match(links, /new URL\('\/register', APP_URL\)/)
  assert.match(links, /https:\/\/fincopilot\.app/)
  assert.doesNotMatch(links, /CLERK_SECRET_KEY|DATABASE_URL/)
})
test('real sections, metadata, and no fabricated social proof', () => {
  const p = read('components/landing-experience.tsx')
  for (const section of ['why-finco','experience','how-it-works','questions']) assert.ok(p.includes(section))
  for (const section of ['Hero','ProductPreview','WhyFinCo','Experience','HowItWorks','Privacy','Questions','FinalCTA']) assert.ok(p.includes('function '+section))
  assert.match(p, /Illustrative interface/)
  assert.doesNotMatch(p, /10,000 users trust|as seen on|SOC 2 certified|RBI approved/)
  assert.match(read('app/layout.tsx'), /export const metadata/)
})
test('all CTA links stay on established product routes', () => {
  const p = read('components/landing-experience.tsx')
  for (const name of ['register','login','privacy','terms']) assert.ok(p.includes('APP_LINKS.'+name))
})
test('source attribution and accessibility guards', () => {
  assert.ok(existsSync(new URL('../SPACEUI-LICENSE.txt', import.meta.url)))
  assert.match(read('components/spaceui/button.tsx'), /useRender/)
  assert.match(read('components/spaceui/accordion.tsx'), /AccordionPrimitive/)
  assert.match(read('components/spaceui/blur-reveal-text.tsx'), /useInView/)
  assert.match(read('app/globals.css'), /prefers-reduced-motion/)
  assert.match(read('components/landing-experience.tsx'), /aria-expanded/)
  assert.match(read('components/landing-experience.tsx'), /aria-selected/)
  assert.match(read('components/landing-experience.tsx'), /Skip to content/)
})
