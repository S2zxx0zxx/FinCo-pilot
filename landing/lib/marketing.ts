/** Explicit build-time publication contract. Never infer a public host from requests. */
export const PUBLIC_PAGES = [
  { path: '/', label: 'Home' },
  { path: '/features', label: 'Features' },
  { path: '/how-it-works', label: 'How it works' },
  { path: '/guides/import-transactions', label: 'Import guide' },
] as const

type MarketingEnvironment = Record<string, string | undefined>

export function getMarketingConfig(env: MarketingEnvironment = process.env) {
  const raw = env.NEXT_PUBLIC_MARKETING_URL?.trim()
  let origin: string | undefined
  if (raw) {
    const url = new URL(raw)
    if (url.protocol !== 'https:' || url.username || url.password || url.port ||
        url.pathname !== '/' || url.search || url.hash ||
        !(url.hostname === 'fincopilot.app' || url.hostname.endsWith('.fincopilot.app'))) {
      throw new Error('Marketing URL must be an owned HTTPS origin without path, credentials or query')
    }
    origin = url.origin
  }
  const indexable = env.VERCEL_ENV === 'production' && env.NEXT_PUBLIC_MARKETING_INDEXABLE === 'true'
  if (indexable && !origin) throw new Error('Indexable marketing requires an explicitly approved NEXT_PUBLIC_MARKETING_URL')
  // The combined frontend exports Next into /welcome with trailingSlash=true.
  // Keep page/schema/social URLs on that actual public namespace.
  const basePath = env.FINCO_EXPORT_MARKETING === 'true' ? '/welcome' : ''
  return { origin: origin ?? 'https://fincopilot.app', indexable, basePath }
}

export function marketingUrl(path: string, env: MarketingEnvironment = process.env) {
  if (!PUBLIC_PAGES.some(page => page.path === path)) throw new Error('Not an approved public marketing path')
  const { origin, basePath } = getMarketingConfig(env)
  const publicPath = basePath ? `${basePath}${path === '/' ? '/' : path + '/'}` : path
  return new URL(publicPath, origin).toString()
}

export function sitemapEntries(env: MarketingEnvironment = process.env) {
  if (!getMarketingConfig(env).indexable) return []
  // No synthetic lastmod, private app, auth, billing or token URLs.
  return PUBLIC_PAGES.map(page => ({ url: marketingUrl(page.path, env) }))
}

export function serializeJsonLd(value: unknown) {
  return JSON.stringify(value).replace(/</g, '\\u003c')
}

export function marketingSocialImage(env: MarketingEnvironment = process.env) {
  const { origin, basePath } = getMarketingConfig(env)
  return new URL(`${basePath}/social-card.png`, origin).toString()
}

export function websiteSchema(env: MarketingEnvironment = process.env) {
  const home = marketingUrl('/', env)
  return { '@context': 'https://schema.org', '@type': 'WebSite', '@id': `${home}#website`,
    url: home, name: 'FinCo-Pilot', inLanguage: 'en' }
}

/** Retain observed restrictive bot policy; changes require a separate owner policy decision. */
export const RESTRICTED_CRAWLERS = [
  "Amazonbot",
  "Applebot-Extended",
  "Bytespider",
  "CCBot",
  "ClaudeBot",
  "Diffbot",
  "Google-Extended",
  "GPTBot",
  "omgili",
  "anthropic-ai",
  "Claude-Web",
  "cohere-ai",
  "MistralAI-Training",
  "meta-externalagent",
  "GoogleOther",
  "Baiduspider",
  "PetalBot",
  "AwarioSmartBot",
  "AwarioRssBot",
  "Google-CloudVertexBot",
  "QualifiedBot",
  "Cotoyogi",
  "ICC-Crawler",
  "atlassian-bot",
  "FishBot",
  "BorderxBot",
  "NavuBot",
  "SemrushBot-SWA",
  "WARDBot",
  "magpie-crawler",
  "KimiBot",
  "CitibotSiteCrawler",
  "Perplexity-User",
  "FireCrawl",
  "FirecrawlAgent",
  "Claude-User",
  "ChatGPT-User",
  "Google-Agent",
  "Google-GeminiNotebook",
  "Google-NotebookLM",
  "MistralAI-User",
  "Kimi-User",
  "Amzn-User",
  "meta-externalfetcher",
  "Retool",
  "Instapaper",
  "ChathiveCrawler"
] as const
