import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { writeRootDiscovery } from '../../frontend/scripts/marketing-root-discovery.mjs'
import { getMarketingConfig, RESTRICTED_CRAWLERS } from '../lib/marketing.ts'

const release = { VERCEL_ENV: 'production', FINCO_MARKETING_PUBLICATION_APPROVED: 'true', NEXT_PUBLIC_MARKETING_URL: 'https://fincopilot.app' }
const urls = ['','features/','how-it-works/','guides/import-transactions/'].map(p => `https://fincopilot.app/welcome/${p}`)
const xml = values => `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${values.map(url => `<url><loc>${url}</loc></url>`).join('')}</urlset>`

test('root discovery retains crawler/private restrictions and matches exported canonical inventory', async () => {
  const dir = await mkdtemp(`${tmpdir()}/finco-discovery-`)
  try {
    await mkdir(`${dir}/public/welcome`, { recursive: true })
    await writeFile(`${dir}/public/welcome/sitemap.xml`, xml(urls))
    assert.deepEqual(await writeRootDiscovery(dir, release), { indexable: true, sitemapUrls: 4 })
    const robots = await readFile(`${dir}/public/robots.txt`, 'utf8')
    for (const agent of RESTRICTED_CRAWLERS) assert.ok(robots.includes(`User-agent: ${agent}\n`))
    assert.match(robots, /Disallow: \/api\//)
    assert.match(robots, /Allow: \/welcome\//)
    assert.equal(robots.match(/Sitemap:/g).length, 1)
    assert.match(robots, /Sitemap: https:\/\/fincopilot.app\/sitemap.xml/)
    assert.equal(await readFile(`${dir}/public/sitemap.xml`, 'utf8'), xml(urls))
    await assert.rejects(writeRootDiscovery(dir, {}), /allowlist/)
    await writeFile(`${dir}/public/welcome/sitemap.xml`, xml([]))
    assert.deepEqual(await writeRootDiscovery(dir, {}), { indexable: false, sitemapUrls: 0 })
    const preview = await readFile(`${dir}/public/robots.txt`, 'utf8')
    assert.match(preview, /^User-agent: \*\nDisallow: \/\n/)
    assert.ok(!preview.includes('Sitemap:'))
    await writeFile(`${dir}/public/welcome/sitemap.xml`, xml([...urls, 'https://fincopilot.app/accounts']))
    await assert.rejects(writeRootDiscovery(dir, release), /allowlist/)
  } finally { await rm(dir, { recursive: true, force: true }) }
})

test('direct same-origin builds cannot bypass the publication gate', () => {
  const exported = { ...release, FINCO_EXPORT_MARKETING: 'true', NEXT_PUBLIC_MARKETING_INDEXABLE: 'true' }
  assert.equal(getMarketingConfig(exported).indexable, true)
  assert.throws(() => getMarketingConfig({ ...exported, FINCO_MARKETING_PUBLICATION_APPROVED: undefined }))
  assert.throws(() => getMarketingConfig({ ...exported, NEXT_PUBLIC_MARKETING_URL: 'https://www.fincopilot.app' }))
  assert.equal(getMarketingConfig({ ...exported, VERCEL_ENV: 'preview' }).indexable, false)
})
