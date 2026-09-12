# FinCo-Pilot PowerPWA Architecture

## Goal

FinCo-Pilot's PWA layer is designed to make the existing React/Vite product installable and app-like without turning a finance application into an unsafe offline cache. The browser version and installed version share one frontend and one backend.

## Experience layers

### Cold launch

`frontend/index.html` owns a zero-JavaScript launch surface. It reads the persisted theme before first paint and renders the FinCo F mark on the correct black/white surface while the JavaScript bundle, i18n, providers and initial route bootstrap. React retires the launch surface only after the lazy-route fallback threshold is covered, preventing a blank or white flash.

### Section navigation

Every pathname change gets a short non-blocking FinCo transition. The router and network continue immediately underneath the overlay; the animation does not introduce an artificial data delay. The visual uses CSS perspective, transform and opacity rather than WebGL/Three.js so it remains lightweight on mobile GPUs. `prefers-reduced-motion` disables continuous motion.

### Genuine lazy-route waits

React `Suspense` uses the same visual language, but its fallback is delayed by 130 ms so a fast lazy import does not flash a second loader. Route chunks are warmed on pointer hover, pointer down and keyboard focus.

### Local data waits

Page-level requests continue to use local skeleton/shimmer states. A full-screen transition is not used for every background refresh.

## Installability

- Web app manifest with standalone display mode.
- 192px, 512px and maskable 512px production PNG launcher icons.
- Apple touch icon and SVG brand fallbacks.
- Shortcuts for Dashboard, Transactions, Accounts and Reports.
- Native `beforeinstallprompt` handling where supported.
- iOS guidance for Safari's Share -> Add to Home Screen flow.
- Standalone-mode and safe-area CSS.

## Service worker security model

The service worker is deliberately conservative:

- `/api/*` is never written to Cache Storage.
- POST/PUT/PATCH/DELETE requests are never intercepted or replayed.
- User-uploaded/same-origin images are not generically cached.
- There is no background sync for financial writes.
- Only the public app shell, launcher assets and content-hashed Vite `/static/` files are cached.
- The built index is inspected at install time to warm its hashed JS/CSS entry assets so the shell can start offline after installation.
- Previously visited lazy chunks are cached naturally when requested through `/static/`.
- Navigation is network-first with the cached SPA document as the offline shell fallback.

This means an offline user can launch the application shell and receive a clear connection state, while authenticated finance data remains governed by the application's normal API/authentication layer.

## Updates

A newly installed worker waits instead of silently taking over an active finance session. The UI exposes an update-ready action. Only after the user accepts does the app send `SKIP_WAITING`; reload occurs on `controllerchange`. Nginx serves `sw.js` and `index.html` with revalidation/no-store policies while content-hashed `/static/` assets receive long immutable caching.

## Network behavior

The runtime tracks online/offline events and displays a compact offline indicator. Reconnection remains compatible with React Query's normal refetch behavior. No transaction is silently queued for a later replay, avoiding accidental duplicate writes.

## Production files

- `frontend/public/manifest.webmanifest`
- `frontend/public/sw.js`
- `frontend/src/pwa/pwa-provider.tsx`
- `frontend/src/pwa/pwa-chrome.tsx`
- `frontend/src/pwa/pwa.css`
- `frontend/src/transitions/finco-route-loader.tsx`
- `frontend/src/transitions/finco-navigation-transition.tsx`
- `frontend/src/transitions/route-preloader.ts`
- `frontend/default.conf.template`

The existing Vite `assetsDir: 'static'` setting must remain unchanged because `/assets` is an application route in FinCo-Pilot.

## Release gate

Before merge, validate all of the following on the final branch:

1. `npm run lint -- --max-warnings=0`
2. `npm run build`
3. `npm test`
4. Manifest is detected in Chrome/Edge Application tools.
5. Service worker reaches Activated and Running state on production/preview HTTPS or localhost.
6. Install prompt produces the FinCo F launcher icon, not a legacy asset.
7. Standalone launch has no white flash in light or dark mode.
8. Route transition appears on section changes and honours reduced motion.
9. Direct deep links such as `/transactions` and `/reports` survive refresh.
10. With DevTools Offline enabled after one controlled load, the SPA shell launches and clearly reports offline state.
11. Cache Storage contains no `/api/` responses.
12. A waiting worker does not refresh the app until the user chooses Update.
13. Android Chrome, desktop Chrome/Edge and iOS Safari Add to Home Screen are smoke-tested.

## Future layers

Push notifications, share-target/import integration and encrypted/controlled IndexedDB read caching should be added as separate features. They should not be coupled to the base installability release, and financial writes should only gain background replay after backend idempotency guarantees are explicit and tested.
