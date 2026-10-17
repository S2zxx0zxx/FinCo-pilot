import copy
import json
from pathlib import Path
import unittest
from growth_release_check import Metadata, ORIGIN, PAGES, failures

class ReleaseContracts(unittest.TestCase):
    def fixture(self):
        rows = [{'url':ORIGIN+p, 'status':200, 'headers':{'Content-Type':'text/html'},
                 'html':{'canonical':[ORIGIN+p], 'h1':['A useful heading'], 'title':'Title '+p,
                         'description':'Description '+p, 'robots':'index, follow', 'internal_links':[]}}
                for p in PAGES]
        rows += [{'url':ORIGIN+'/sitemap.xml','status':200, 'headers':{'Content-Type':'application/xml'},
                  'sitemap_namespace_valid':True,'sitemap_urls':[ORIGIN+p for p in PAGES]},
                 {'url':ORIGIN+'/robots.txt','status':200,'headers':{'Content-Type':'text/plain'},
                  'robots_text':'User-agent: *\nAllow: /welcome/\nSitemap: '+ORIGIN+'/sitemap.xml'},
                 {'url':ORIGIN+'/api/health/ready','readiness':'ready'},
                 {'url':ORIGIN+'/welcome/__seo_missing_page__/','status':404}]
        rows += [{'url':ORIGIN+p,'status':200,'html':{'robots':'noindex'}} for p in ['/login','/register','/pricing','/privacy','/terms','/support']]
        rows += [{'url':'https://www.fincopilot.app'+p,'status':308,'redirect':ORIGIN+p} for p in PAGES]
        return rows
    def test_good_fixture_passes_and_each_release_regression_fails(self):
        good=self.fixture(); self.assertEqual(failures(good), [])
        for field,value in [('status',302),('truncated',True),('html',{})]:
            rows=copy.deepcopy(good); rows[0][field]=value; self.assertTrue(failures(rows))
        for field,value in [('robots','noindex, follow'),('canonical',[ORIGIN+'/login']),('h1',[]),
                            ('title',''),('description',''),('internal_links',['/features'])]:
            rows=copy.deepcopy(good); rows[0]['html'][field]=value; self.assertTrue(failures(rows))
        rows=copy.deepcopy(good); rows[0]['headers']['X-Robots-Tag']='NOINDEX'; self.assertTrue(failures(rows))
        rows=copy.deepcopy(good); rows[4]['sitemap_urls'].append(ORIGIN+'/accounts'); self.assertTrue(failures(rows))
        rows=copy.deepcopy(good); rows[6]['readiness']='not_ready'; self.assertTrue(failures(rows))
        rows=copy.deepcopy(good); rows[5]['robots_text']='User-agent: *\nDisallow: /\nSitemap: '+ORIGIN+'/sitemap.xml'; self.assertTrue(failures(rows))
        rows=copy.deepcopy(good); rows[-5]['html']['robots']='index'; self.assertTrue(failures(rows))
    def test_live_www_regressions_are_rejected_for_every_public_page(self):
        for path in PAGES:
            for status,destination in [(200,None),(307,ORIGIN+path),(308,ORIGIN+'/login')]:
                rows=self.fixture()
                row=next(r for r in rows if r['url']=='https://www.fincopilot.app'+path)
                row.update(status=status,redirect=destination)
                self.assertTrue(any('www must permanently redirect' in e for e in failures(rows)))
    def test_slash_redirects_are_explicit_and_public_host_scoped(self):
        config=json.loads((Path(__file__).resolve().parents[1]/'frontend/vercel.json').read_text())
        for path in PAGES:
            matches=[r for r in config['redirects'] if r['source']==path]
            self.assertEqual(matches,[{'source':path,'has':[{'type':'host','value':'www.fincopilot.app'}],
                                      'destination':ORIGIN+path,'permanent':True}])
    def test_parser_reads_split_heading_and_omits_token_links(self):
        p=Metadata(); p.feed('<title>Useful title</title><h1><span>Hello</span> world</h1><a href="/login?token=secret">a</a><a href="/welcome/features/">b</a>')
        self.assertEqual(p.headings,['Hello world']); self.assertEqual(p.links,['/welcome/features/'])

if __name__ == '__main__': unittest.main()
