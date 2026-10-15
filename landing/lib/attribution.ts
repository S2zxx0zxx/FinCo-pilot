/** Pure opt-in event construction. No storage, cookies, network or user identifiers. */
const pages = new Set(['/', '/features', '/how-it-works', '/guides/import-transactions'])
const actions = new Set(['signup', 'login', 'import-guide'])

export function referralSource(raw: string | undefined) {
  if (!raw) return 'direct_or_unknown'
  try {
    const url = new URL(raw)
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return 'other'
    const host = url.hostname.toLowerCase()
    if (['google.com','www.google.com','google.co.in','www.google.co.in'].includes(host)) return 'google'
    if (['bing.com','www.bing.com'].includes(host)) return 'bing'
    if (['chatgpt.com','www.chatgpt.com'].includes(host)) return 'chatgpt'
    if (['perplexity.ai','www.perplexity.ai'].includes(host)) return 'perplexity'
    return 'other'
  } catch { return 'other' }
}

export function marketingEvent(input: { consented: boolean; page: string; action: string; referrer?: string }) {
  if (input.consented !== true || !pages.has(input.page) || !actions.has(input.action)) return null
  return { name: 'marketing_cta_click' as const, page_id: input.page,
    cta_id: input.action, source: referralSource(input.referrer) }
}
