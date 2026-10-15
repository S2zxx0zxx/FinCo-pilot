import type { ReactNode } from 'react'
import Link from 'next/link'
import { APP_LINKS } from '@/lib/links'
import { marketingUrl, PUBLIC_PAGES, serializeJsonLd } from '@/lib/marketing'

/** Server-only documentation shell: no tracking, accounts, API calls or session state. */
export function MarketingDocument({ path, title, intro, children }: {
  path: string; title: string; intro: string; children: ReactNode
}) {
  const breadcrumbs = { '@context': 'https://schema.org', '@type': 'BreadcrumbList', itemListElement: [
    { '@type': 'ListItem', position: 1, name: 'Home', item: marketingUrl('/') },
    { '@type': 'ListItem', position: 2, name: title, item: marketingUrl(path) },
  ] }
  return <div className="document-page">
    <a className="skip-link" href="#document-content">Skip to content</a>
    <header className="document-header shell">
      <Link className="document-brand" href="/">FinCo-Pilot</Link>
      <nav aria-label="Product documentation">{PUBLIC_PAGES.filter(page => page.path !== '/').map(page =>
        <Link key={page.path} href={page.path} aria-current={page.path === path ? 'page' : undefined}>{page.label}</Link>)}</nav>
    </header>
    <main id="document-content" className="document-content shell">
      <nav aria-label="Breadcrumb"><ol className="document-breadcrumb"><li><Link href="/">Home</Link></li><li aria-current="page">{title}</li></ol></nav>
      <h1>{title}</h1><p className="document-intro">{intro}</p>
      {children}
      <section className="document-action" aria-labelledby="document-next"><h2 id="document-next">Explore the application</h2>
        <p>Available features and connected services depend on your account settings, permissions and plan.</p>
        <a className="document-cta" href={APP_LINKS.register}>Go to sign up</a><a href={APP_LINKS.login}>Log in</a>
      </section>
    </main>
    <footer className="document-footer shell"><span>FinCo-Pilot product documentation</span><nav aria-label="Policies and support"><a href={APP_LINKS.privacy}>Privacy</a><a href={APP_LINKS.terms}>Terms</a><a href={APP_LINKS.support}>Support</a></nav></footer>
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: serializeJsonLd(breadcrumbs) }} />
  </div>
}
