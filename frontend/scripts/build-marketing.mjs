/** Compile the existing Next.js landing into same-origin static assets.
 * No extra web service, external preview origin, credentials or finance data.
 */
import { spawnSync } from 'node:child_process'
import { cp, rm, access } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const landing = path.resolve(frontend, '../landing')
await access(path.join(landing, 'package-lock.json'))
function run(args, env = {}) {
  const result = spawnSync('npm', args, { cwd: landing, stdio: 'inherit', env: { ...process.env, ...env } })
  if (result.status !== 0) throw new Error(`Landing build failed: npm ${args.join(' ')}`)
}
run(['ci', '--no-audit', '--no-fund'])
run(['run', 'build'], {
  FINCO_EXPORT_MARKETING: 'true', NEXT_PUBLIC_FINCO_LANDING_BASE_PATH: '/welcome',
  NEXT_PUBLIC_FINCO_SAME_ORIGIN: 'true', NEXT_PUBLIC_MARKETING_INDEXABLE: 'false',
  NEXT_TELEMETRY_DISABLED: '1',
})
const target = path.join(frontend, 'public/welcome')
await access(path.join(landing, '.next-export/index.html'))
await rm(target, { recursive: true, force: true })
await cp(path.join(landing, '.next-export'), target, { recursive: true })
console.log('Next.js landing exported to /welcome/ with same-origin app links.')
