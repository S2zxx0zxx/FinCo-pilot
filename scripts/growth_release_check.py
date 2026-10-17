#!/usr/bin/env python3
"""Bounded anonymous release observations; never accesses financial records.

No cookies, credentials, retries or discovered-link crawling. Fixed public URLs,
512 KiB response cap; records only public metadata and selected safe headers.
Exit nonzero with --require-indexable when public release gates fail.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

ORIGIN = 'https://fincopilot.app'
PAGES = ['/welcome/', '/welcome/features/', '/welcome/how-it-works/', '/welcome/guides/import-transactions/']
PATHS = ['/', *PAGES, '/robots.txt', '/sitemap.xml', '/welcome/sitemap.xml', '/login', '/register', '/pricing', '/privacy', '/terms', '/support', '/api/health/ready', '/welcome/__seo_missing_page__/']
URLS = [ORIGIN + p for p in PATHS] + ['https://www.fincopilot.app/welcome/', 'https://api.fincopilot.app/api/health/ready']

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

class Metadata(HTMLParser):
    def __init__(self):
        super().__init__(); self.tag = ''; self.title = ''; self.headings = []; self.canonicals = []; self.metas = {}; self.links = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('title', 'h1'):
            self.tag = tag
            if tag == 'h1': self.headings.append('')
        if tag == 'link' and a.get('rel') == 'canonical': self.canonicals.append(a.get('href'))
        if tag == 'meta':
            key = a.get('name') or a.get('property')
            if key: self.metas[key] = a.get('content', '')
        if tag == 'a':
            href = a.get('href', '')
            if href.startswith('/') and '?' not in href and '#' not in href: self.links.append(href)
    def handle_data(self, data):
        if self.tag == 'title': self.title += data
        if self.tag == 'h1': self.headings[-1] += data
    def handle_endtag(self, tag):
        if tag == self.tag: self.tag = ''

def observe(url):
    result = {'url': url, 'observed_at_utc': datetime.now(timezone.utc).isoformat()}
    try:
        try: response = build_opener(NoRedirect()).open(Request(url, headers={'User-Agent': 'FinCoPilot-Release-Audit/1.0'}), timeout=20)
        except HTTPError as e: response = e
        with response:
            raw = response.read(524289); body = raw[:524288].decode('utf-8', 'replace')
            result.update(status=response.code, truncated=len(raw)>524288,
                          headers={k: response.headers[k] for k in ['Content-Type','Cache-Control','X-Robots-Tag','Server'] if response.headers.get(k)})
            location = response.headers.get('Location', '')
            if location and '?' not in location and '#' not in location: result['redirect'] = location
            if 'text/html' in response.headers.get('Content-Type', ''):
                p = Metadata(); p.feed(body)
                result['html'] = {'title': p.title, 'h1': p.headings, 'canonical': p.canonicals,
                    'robots': p.metas.get('robots'), 'description': p.metas.get('description'),
                    'og_image': p.metas.get('og:image'), 'internal_links': sorted(set(p.links))}
            if url.endswith('sitemap.xml'):
                try:
                    root = ET.fromstring(body)
                    result['sitemap_urls'] = [e.text for e in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
                    result['sitemap_namespace_valid'] = root.tag == '{http://www.sitemaps.org/schemas/sitemap/0.9}urlset'
                except ET.ParseError: result['sitemap_namespace_valid'] = False
            if url.endswith('/robots.txt') and response.code == 200: result['robots_text'] = body[:16000]
            if url.endswith('/api/health/ready') and response.code == 200:
                try: result['readiness'] = json.loads(body).get('status')
                except (ValueError, AttributeError): pass
    except (URLError, OSError, TimeoutError): result['error'] = 'network_failure'
    return result

def failures(rows):
    by_url = {r['url']: r for r in rows}; errors = []; titles = set(); descriptions = set()
    for path in PAGES:
        url = ORIGIN + path; r = by_url.get(url, {}); h = r.get('html', {})
        if r.get('status') != 200 or r.get('truncated') or not h: errors.append(path + ': not complete 200 HTML')
        if h.get('canonical') != [url]: errors.append(path + ': canonical mismatch')
        if len(h.get('h1', [])) != 1 or not ''.join(h.get('h1', [])).strip(): errors.append(path + ': H1 missing')
        if not h.get('title') or h.get('title') in titles: errors.append(path + ': title missing/duplicate')
        if not h.get('description') or h.get('description') in descriptions: errors.append(path + ': description missing/duplicate')
        titles.add(h.get('title')); descriptions.add(h.get('description'))
        if not h.get('robots') or 'noindex' in h.get('robots', '').lower() or 'noindex' in r.get('headers', {}).get('X-Robots-Tag', '').lower(): errors.append(path + ': indexing blocked/unproved')
        if any(link in h.get('internal_links', []) for link in ['/features','/how-it-works','/guides/import-transactions']): errors.append(path + ': legacy broken links')
    sm = by_url.get(ORIGIN+'/sitemap.xml', {})
    if sm.get('status') != 200 or not sm.get('sitemap_namespace_valid') or sm.get('sitemap_urls') != [ORIGIN+p for p in PAGES]: errors.append('root sitemap not exact eligible inventory')
    if 'xml' not in sm.get('headers', {}).get('Content-Type', ''): errors.append('root sitemap MIME')
    robots = by_url.get(ORIGIN+'/robots.txt', {})
    if robots.get('status') != 200 or 'text/plain' not in robots.get('headers', {}).get('Content-Type', '') or 'Sitemap: '+ORIGIN+'/sitemap.xml' not in robots.get('robots_text', ''): errors.append('authoritative robots contract')
    # These are fixed ordinary groups, not certification of provider-managed policy.
    policy = RobotFileParser(); policy.parse(robots.get('robots_text', '').splitlines())
    for agent in ['Googlebot', 'Bingbot', 'OAI-SearchBot']:
        if any(not policy.can_fetch(agent, ORIGIN+p) for p in PAGES): errors.append(agent+': public crawling blocked')
    for path in ['/login','/register','/pricing','/privacy','/terms','/support']:
        row = by_url.get(ORIGIN+path, {})
        if row.get('status') != 200 or 'noindex' not in row.get('html', {}).get('robots', '').lower(): errors.append(path+': private/app noindex contract not proved')
    if by_url.get(ORIGIN+'/api/health/ready', {}).get('readiness') != 'ready': errors.append('API readiness not proved')
    if by_url.get(ORIGIN+'/welcome/__seo_missing_page__/', {}).get('status') != 404: errors.append('public missing route is not 404')
    return errors

def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--require-indexable', action='store_true'); args=p.parse_args()
    with ThreadPoolExecutor(max_workers=4) as pool: rows=list(pool.map(observe, URLS))
    errors=failures(rows)
    print(json.dumps({'scope':'Public fixed GET observations; no auth/provider/conversion acceptance', 'max_requests':len(URLS), 'observations':rows, 'release_failures':errors}, indent=2))
    return int(args.require_indexable and bool(errors))

if __name__ == '__main__': raise SystemExit(main())
