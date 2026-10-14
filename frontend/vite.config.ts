import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { createHash } from 'node:crypto'
import { readFile, readdir, writeFile } from 'node:fs/promises'
import { defineConfig, loadEnv, type IndexHtmlTransformContext } from 'vite'
import { resolveAppVersion } from './build/version.ts'
import { localQaSessionPlugin } from './build/local-qa-session.ts'
import { finalizeSecurityPolicy } from './build/security-policy.ts'

function getFrontendHost(frontendUrl?: string, allowPublicDevelopment = false) {
  const hosts = ['localhost', '127.0.0.1']
  if (!frontendUrl) return hosts
  const withoutProto = frontendUrl.replace(/^https?:\/\//, '')
  const host = withoutProto.split(/[:/]/)[0]
  if (host && !hosts.includes(host) && allowPublicDevelopment) hosts.push(host)
  return hosts
}

export default defineConfig(async ({ mode }) => {
  const env = loadEnv(mode, import.meta.dirname, '')
  const frontendUrl = env.FRONTEND_URL || process.env.FRONTEND_URL
  const backendUrl = env.BACKEND_URL || process.env.BACKEND_URL
  const allowPublicDevelopment = (env.FINCO_ALLOW_PUBLIC_DEV_SERVER || process.env.FINCO_ALLOW_PUBLIC_DEV_SERVER) === 'true'
  const appVersionRoot = env.APP_VERSION_ROOT || process.env.APP_VERSION_ROOT
  const sentryUploadEnabled = Boolean(env.SENTRY_AUTH_TOKEN && env.SENTRY_ORG && env.SENTRY_PROJECT)
  const appVersion = await resolveAppVersion(
    appVersionRoot || import.meta.dirname,
    env.VITE_APP_VERSION || process.env.VITE_APP_VERSION,
  )

  return {
    envPrefix: ['VITE_', 'NEXT_PUBLIC_'],
    define: {
      __APP_VERSION__: JSON.stringify(appVersion),
    },
    build: {
      // Never publish public sourcemaps; upload private artifacts only with CI token.
      sourcemap: sentryUploadEnabled ? ('hidden' as const) : false,
      // Keep the existing per-chunk budget; optional locales load on demand.
      chunkSizeWarningLimit: 1000,
      // Emit hashed JS/CSS into `static/` instead of Vite's default `assets/`.
      // The default collides with our `/assets` SPA route: nginx's
      // `try_files $uri $uri/ /index.html` matches the real `dist/assets/`
      // directory before falling back to index.html, so a direct load or
      // refresh of `/assets` 301s into the build dir and renders a blank
      // page instead of booting the app (issue #295).
      assetsDir: 'static',
      manifest: true,
    },
    plugins: [react(), tailwindcss(), localQaSessionPlugin({
      mode,
      enabled: (env.FINCO_LOCAL_QA_ENABLED || process.env.FINCO_LOCAL_QA_ENABLED) === 'true',
      frontendUrl,
      backendUrl,
      email: env.FINCO_QA_EMAIL || process.env.FINCO_QA_EMAIL,
      password: env.FINCO_QA_PASSWORD || process.env.FINCO_QA_PASSWORD,
    }), {
      name: 'finco-public-route-hints',
      apply: 'build',
      transformIndexHtml: {
        order: 'post',
        handler(_html: string, context: IndexHtmlTransformContext) {
          if (!context.bundle) return
          const login = Object.values(context.bundle).find(output => output.type === 'chunk' && output.facadeModuleId?.endsWith('/src/pages/login.tsx'))
          const headingFont = Object.values(context.bundle).find(output => output.type === 'asset' && /open-runde-semibold-latin-.+\.woff2$/.test(output.fileName))
          const bodyFont = Object.values(context.bundle).find(output => output.type === 'asset' && /inter-latin-wght-normal-.+\.woff2$/.test(output.fileName))
          if (!login || login.type !== 'chunk') return
          // Only public sign-in code is hinted. Modulepreload fetches/parses;
          // it does not admit a session, render private UI or fetch finance APIs.
          const hints = JSON.stringify({ login: `/${login.fileName}`, font: headingFont ? `/${headingFont.fileName}` : null, bodyFont: bodyFont ? `/${bodyFont.fileName}` : null })
          return [{ tag: 'script', injectTo: 'head', children: `(()=>{const h=${hints};const p=location.pathname;if(!['/','/login','/sign-in'].includes(p))return;try{if(p==='/'&&localStorage.getItem('token'))return}catch{}const add=(rel,href,as,integrity)=>{const l=document.createElement('link');l.rel=rel;l.href=href;if(integrity)l.integrity=integrity;if(as){l.as=as;l.type='font/woff2';l.crossOrigin='anonymous'}document.head.append(l)};add('modulepreload',h.login,undefined,h.loginIntegrity);let lang='en';try{lang=new URLSearchParams(location.search).get('lng')||localStorage.getItem('i18nextLng')||'en'}catch{}if(/^(en|pt|es|fr|de|it|pl|nl|sk)(-|$)/i.test(lang)){if(h.bodyFont)add('preload',h.bodyFont,'font');if(h.font)add('preload',h.font,'font')}})()` }]
        },
      },
    }, {
      name: 'finco-pwa-release-version',
      apply: 'build',
      async closeBundle() {
        await finalizeSecurityPolicy(import.meta.dirname)
        // A changed shell must produce a changed worker and isolated caches.
        // Otherwise browsers never discover frontend-only releases, and a
        // waiting worker can overwrite the active release's offline shell.
        const dist = path.resolve(import.meta.dirname, 'dist')
        const workerPath = path.join(dist, 'sw.js')
        const worker = await readFile(workerPath, 'utf8')
        if (!worker.includes("const VERSION = 'finco-pwa-v5'")) throw new Error('PWA version template is missing')
        const digest = createHash('sha256').update(worker)
        // Include public icons/manifest too: their URLs are stable but their
        // bytes can change between releases without changing index.html.
        async function hashDirectory(directory: string) {
          const entries = await readdir(directory, { withFileTypes: true })
          for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
            const file = path.join(directory, entry.name)
            if (entry.isDirectory()) await hashDirectory(file)
            else if (file !== workerPath) {
              digest.update(path.relative(dist, file)).update('\0').update(await readFile(file)).update('\0')
            }
          }
        }
        await hashDirectory(dist)
        const release = digest.digest('hex').slice(0, 20)
        await writeFile(workerPath, worker.replace("const VERSION = 'finco-pwa-v5'", `const VERSION = 'finco-pwa-v5-${release}'`))
      },
    }, ...(sentryUploadEnabled ? [
      (await (async () => {
        const pkg = '@sentry/vite-plugin'
        const mod = await import(/* @vite-ignore */ pkg)
        return mod.sentryVitePlugin({
          org: env.SENTRY_ORG,
          project: env.SENTRY_PROJECT,
          authToken: env.SENTRY_AUTH_TOKEN,
          telemetry: false,
          release: { name: appVersion },
          sourcemaps: { filesToDeleteAfterUpload: ['dist/**/*.map'] },
          errorHandler: (error: unknown) => { throw error },
        })
      })())
    ] : [])],
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, './src'),
      },
    },
    server: {
      port: 5173,
      host: '0.0.0.0',
      // Public domains must serve the production build. A deliberate public
      // development session requires explicit operator opt-in; no wildcard.
      allowedHosts: getFrontendHost(frontendUrl, allowPublicDevelopment),
      proxy: {
        '/api': {
          target: backendUrl ?? 'http://localhost:8000',
          changeOrigin: true,
        },
      },
      watch: {
        usePolling: true,
      },
    },
  }
})
