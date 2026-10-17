import { readFile, writeFile } from 'node:fs/promises'
import { RESTRICTED_CRAWLERS } from '../../landing/lib/marketing.ts'
import { marketingPublicationEnv, CANONICAL_MARKETING_ORIGIN } from './marketing-publication-policy.mjs'

/** Build authoritative discovery assets from the same export as the public HTML.
 * No finance routes, requests, credentials or fabricated modification dates.
 */
export async function writeRootDiscovery(frontend, env = process.env) {
  const indexable = marketingPublicationEnv(env).NEXT_PUBLIC_MARKETING_INDEXABLE === 'true'
  const sitemap = await readFile(`${frontend}/public/welcome/sitemap.xml`, 'utf8')
  const urls = [...sitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map(match => match[1])
  const expected = ['','features/','how-it-works/','guides/import-transactions/']
    .map(path => `${CANONICAL_MARKETING_ORIGIN}/welcome/${path}`)
  if (JSON.stringify(urls) !== JSON.stringify(indexable ? expected : [])) {
    throw new Error('Exported sitemap does not match the approved public allowlist')
  }
  const privateRules = ['/api/', '/mcp', '/reset-password', '/verify-email', '/sso-callback', '/auth/', '/oauth/', '/i/']
  const rules = indexable
    ? ['User-agent: *', 'Allow: /welcome/', ...privateRules.map(path => `Disallow: ${path}`)]
    : ['User-agent: *', 'Disallow: /', ...privateRules.map(path => `Disallow: ${path}`)]
  // A more specific user-agent group takes precedence over wildcard rules.
  // Preserve the full existing training/user-agent restriction list.
  rules.push('', ...RESTRICTED_CRAWLERS.map(agent => `User-agent: ${agent}`), 'Disallow: /')
  if (indexable) rules.push('', `Sitemap: ${CANONICAL_MARKETING_ORIGIN}/sitemap.xml`)
  await writeFile(`${frontend}/public/robots.txt`, rules.join('\n') + '\n')
  await writeFile(`${frontend}/public/sitemap.xml`, sitemap)
  return { indexable, sitemapUrls: urls.length }
}
