/** Bounded mobile/desktop lab sample, never field CWV or authenticated QA.
 * Fixed marketing paths; no forms, retries, tokens, finance APIs or collectors.
 * Local mode expects an already running isolated production static server.
 */
import { chromium } from 'playwright'
import lighthouse from 'lighthouse'
import desktopConfig from 'lighthouse/core/config/desktop-config.js'
import { writeFile } from 'node:fs/promises'

const live = process.argv.includes('--live')
const origin = live ? 'https://fincopilot.app' : 'http://127.0.0.1:3132'
const paths = ['/welcome/', '/welcome/features/', '/welcome/guides/import-transactions/']
const report = { observedAtUtc: new Date().toISOString(), scope: live ? 'Live public production lab' : 'Isolated production export lab',
  caveat: 'Simulated lab; no field p75 INP, actual phone or conversion claim. Two runs per page/device, no before/after causal claim.', results: [] }
const proxyRaw = live && (process.env.HTTPS_PROXY || process.env.https_proxy)
const proxy = proxyRaw ? new URL(proxyRaw) : null
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox','--remote-debugging-port=9223'],
  ...(proxy ? {proxy:{server:proxy.origin,...(proxy.username ? {username:decodeURIComponent(proxy.username),password:decodeURIComponent(proxy.password)} : {})}} : {}) })
try {
  report.stage = 'verify-public-origin'
  const page = await browser.newPage()
  const response = await page.goto(origin + paths[0], { waitUntil: 'networkidle', timeout: 30000 })
  report.preflight = { status: response?.status(), expectedBrandTitle: (await page.title()).includes('FinCo-Pilot') }
  if (response?.status() !== 200 || !report.preflight.expectedBrandTitle) throw new Error('Public marketing origin not verified; lab stopped')
  await page.close()
  report.stage = 'lighthouse-runs'
  for (const path of paths) for (const formFactor of ['mobile','desktop']) for (let run = 1; run <= 2; run++) {
    const { lhr } = await lighthouse(origin + path, { port:9223, output:'json', logLevel:'error',
      onlyCategories:['performance','accessibility','best-practices','seo'] }, formFactor === 'desktop' ? desktopConfig : undefined)
    const result = { path, formFactor, run, fetchTime:lhr.fetchTime, lighthouseVersion:lhr.lighthouseVersion,
      finalUrl:lhr.finalDisplayedUrl, runtimeError:lhr.runtimeError?.code ?? null,
      scores:Object.fromEntries(Object.entries(lhr.categories).map(([key,value]) => [key,value.score === null ? null : Math.round(value.score*100)])),
      metrics:Object.fromEntries(['first-contentful-paint','largest-contentful-paint','total-blocking-time','cumulative-layout-shift','speed-index','total-byte-weight']
        .map(key => [key,lhr.audits[key]?.numericValue ?? null])) }
    report.results.push(result)
    console.log(JSON.stringify(result))
    if (result.runtimeError) throw new Error('Lab runtime failure; stopped without retry')
  }
} catch (error) {
  report.failureKind = error instanceof Error && /timeout/i.test(error.message) ? 'timeout' : 'network_or_lighthouse_error'
  report.blocked = 'Browser/network/lab run failed; completed rows retained, missing runs are unverified'
  process.exitCode = 1
} finally {
  await browser.close()
  if (process.env.FINCO_LAB_REPORT) await writeFile(process.env.FINCO_LAB_REPORT, JSON.stringify(report,null,2)+'\n')
}
