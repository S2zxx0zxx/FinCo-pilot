import { createHash } from 'node:crypto'
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const otherDirectives = "style-src 'self' 'unsafe-inline' https:; img-src 'self' data: blob: https:; font-src 'self' data: https:; connect-src 'self' https: wss:; frame-src https:; worker-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
export const compatibilityCsp = `default-src 'self'; script-src 'self' 'unsafe-inline' https:; ${otherDirectives}`
export function scriptIntegrity(code: string | Buffer) {
  return `sha256-${createHash('sha256').update(code).digest('base64')}`
}

/** Hash exact delivered inline bytes and SRI-tagged executable entry modules.
 * No permissive Trusted Types default policy or unsafe-eval is introduced.
 */
export function compileStrictCsp(html: string) {
  const hashes = new Set<string>()
  for (const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)) {
    const [, attributes, code] = match
    if (/\bsrc=/.test(attributes)) {
      const integrity = attributes.match(/\bintegrity="(sha256-[^"]+)"/)?.[1]
      if (!integrity) throw new Error('Executable external entry lacks build-derived SRI')
      hashes.add(integrity)
    } else if (code.trim()) hashes.add(scriptIntegrity(code))
  }
  for (const match of html.matchAll(/<link\b(?=[^>]*(?:rel="modulepreload"|as="script"))[^>]*integrity="(sha256-[^"]+)"[^>]*>/g)) hashes.add(match[1])
  // Dynamic auth-route modulepreloads must be SRI-bound too: strict-dynamic
  // otherwise blocks executable modules even if the browser fetched them.
  const hint = html.match(/const h=(\{[^;]+\});const p=location.pathname/)
  if (hint) {
    const data = JSON.parse(hint[1]) as Record<string, unknown>
    for (const key of ['loginIntegrity', 'clerkLoginIntegrity', 'clerkAdapterIntegrity']) {
      const value = data[key]
      if (typeof value === 'string' && /^sha256-[a-zA-Z0-9+/]+=*$/.test(value)) hashes.add(value)
    }
  }
  if (!hashes.size) throw new Error('No trusted entry scripts')
  return `default-src 'self'; script-src ${[...hashes].map(hash => `'${hash}'`).join(' ')} 'strict-dynamic'; script-src-attr 'none'; ${otherDirectives}`
}

/** Finalize after Vite writes its transformed bytes, before PWA hashes shell.
 * Hashing transformIndexHtml's temporary chunk.code would produce stale SRI.
 */
export async function finalizeSecurityPolicy(root: string) {
  const htmlPath = path.join(root, 'dist/index.html')
  const initial = await readFile(htmlPath, 'utf8')
  const external = [...initial.matchAll(/<script\b[^>]*\bsrc="([^"]+)"[^>]*>/g), ...initial.matchAll(/<link\b(?=[^>]*rel="modulepreload")[^>]*href="([^"]+)"[^>]*>/g)]
  let html = initial
  for (const match of external) {
    const [tag, src] = match
    if (!/^\/static\/[\w.-]+\.js$/.test(src)) throw new Error(`Unknown entry script: ${src}`)
    const code = await readFile(path.join(root, 'dist', src.slice(1)))
    const updated = tag.replace(/\s+integrity="[^"]*"/g, '').replace(/>$/, ` integrity="${scriptIntegrity(code)}">`)
    html = html.replace(tag, updated)
  }
  const hint = html.match(/const h=(\{[^;]+\});const p=location.pathname/)
  if (hint) {
    const data = JSON.parse(hint[1]) as {
      login: string
      clerkLogin?: string | null
      clerkAdapter?: string | null
      loginIntegrity?: string
      clerkLoginIntegrity?: string
      clerkAdapterIntegrity?: string
    }
    const modules = [
      ['login', 'loginIntegrity'],
      ['clerkLogin', 'clerkLoginIntegrity'],
      ['clerkAdapter', 'clerkAdapterIntegrity'],
    ] as const
    if (Boolean(data.clerkLogin) !== Boolean(data.clerkAdapter)) {
      throw new Error('Clerk auth route hints must be paired')
    }
    for (const [moduleKey, integrityKey] of modules) {
      const url = data[moduleKey]
      if (url == null && moduleKey !== 'login') continue
      if (typeof url !== 'string' || !/^\/static\/[\w.-]+\.js$/.test(url)) {
        throw new Error(`Unknown hinted module: ${moduleKey}`)
      }
      data[integrityKey] = scriptIntegrity(await readFile(path.join(root, 'dist', url.slice(1))))
    }
    html = html.replace(hint[1], JSON.stringify(data))
  }
  await writeFile(htmlPath, html)
  // Exported Next.js owns separate HTML documents. Bind their exact scripts
  // to this same artifact instead of weakening strict CSP for the public entry.
  const marketing = path.join(root, 'dist/welcome')
  let marketingHtml = ''
  for (const file of await readdir(marketing, { recursive: true })) {
    if (!file.endsWith('.html')) continue
    const outputPath = path.join(marketing, file)
    let document = await readFile(outputPath, 'utf8')
    for (const match of [...document.matchAll(/<script\b[^>]*\bsrc="([^"]+)"[^>]*>/g), ...document.matchAll(/<link\b(?=[^>]*as="script")[^>]*href="([^"]+)"[^>]*>/g)]) {
      const [tag, src] = match
      if (!/^\/welcome\/_next\/static\/[\w./%-]+\.js$/.test(src) || src.includes('..')) throw new Error('Unknown marketing script: ' + src)
      const code = await readFile(path.join(root, 'dist', src.slice(1)))
      document = document.replace(tag, tag.replace(/\s+integrity="[^"]*"/g, '').replace(/>$/, ` integrity="${scriptIntegrity(code)}" crossorigin="anonymous">`))
    }
    await writeFile(outputPath, document)
    marketingHtml += document
  }
  if (!marketingHtml.includes('A plan') && !marketingHtml.includes('FinCo-Pilot')) throw new Error('Marketing export missing')
  const strictCsp = compileStrictCsp(html + marketingHtml)
  const output = path.join(root, 'node_modules/.cache/finco-security')
  await mkdir(output, { recursive: true })
  // The built-image map belongs to this exact artifact/environment.
  const template = `map "\${FINCO_STRICT_CSP_MODE}" $finco_csp {\n default "${compatibilityCsp}";\n enforce "${strictCsp}";\n}\nmap "\${FINCO_STRICT_CSP_MODE}" $finco_strict_report {\n default "";\n report-only "${strictCsp}";\n}\n`
  await writeFile(path.join(output, 'csp-map.conf.template'), template)
  await writeFile(path.join(output, 'policy.json'), JSON.stringify({ compatibilityCsp, strictCsp, defaultMode: 'compatibility', providerAcceptanceRequired: true }, null, 2) + '\n')
}
