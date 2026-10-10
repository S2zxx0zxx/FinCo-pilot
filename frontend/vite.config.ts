import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { createHash } from 'node:crypto'
import { readFile, readdir, writeFile } from 'node:fs/promises'
import { defineConfig, loadEnv } from 'vite'
import { resolveAppVersion } from './build/version.ts'

function getFrontendHost(frontendUrl?: string) {
  if (!frontendUrl) return []
  const withoutProto = frontendUrl.replace(/^https?:\/\//, '')
  return [withoutProto.split(/[:/]/)[0]]
}

export default defineConfig(async ({ mode }) => {
  const env = loadEnv(mode, import.meta.dirname, '')
  const frontendUrl = env.FRONTEND_URL || process.env.FRONTEND_URL
  const backendUrl = env.BACKEND_URL || process.env.BACKEND_URL
  const mcpUrl = env.MCP_SERVER_URL || process.env.MCP_SERVER_URL || 'http://localhost:8765'
  const appVersionRoot = env.APP_VERSION_ROOT || process.env.APP_VERSION_ROOT
  const appVersion = await resolveAppVersion(
    appVersionRoot || import.meta.dirname,
    env.VITE_APP_VERSION || process.env.VITE_APP_VERSION,
  )

  return {
    define: {
      __APP_VERSION__: JSON.stringify(appVersion),
    },
    build: {
      // Keep the existing per-chunk budget; optional locales load on demand.
      chunkSizeWarningLimit: 1000,
      // Emit hashed JS/CSS into `static/` instead of Vite's default `assets/`.
      // The default collides with our `/assets` SPA route: nginx's
      // `try_files $uri $uri/ /index.html` matches the real `dist/assets/`
      // directory before falling back to index.html, so a direct load or
      // refresh of `/assets` 301s into the build dir and renders a blank
      // page instead of booting the app (issue #295).
      assetsDir: 'static',
    },
    plugins: [react(), tailwindcss(), {
      name: 'finco-pwa-release-version',
      apply: 'build',
      async closeBundle() {
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
    }],
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, './src'),
      },
    },
    server: {
      port: 5173,
      host: '0.0.0.0',
      allowedHosts: getFrontendHost(frontendUrl),
      proxy: {
        '^/mcp$': {
          target: mcpUrl,
          changeOrigin: true,
        },
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
