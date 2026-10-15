import { useEffect } from 'react'

/** Client-side Home navigation must cross from the finance SPA to static Next.js. */
export default function PublicHome() {
  useEffect(() => { window.location.replace('/welcome/') }, [])
  return <main className="min-h-screen grid place-items-center"><a href="/welcome/">Open FinCo-Pilot</a></main>
}
