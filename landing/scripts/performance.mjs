import { chromium } from 'playwright'
import lighthouse from 'lighthouse'
import { mkdir, writeFile } from 'node:fs/promises'
const origin=process.env.LANDING_TEST_URL||'http://127.0.0.1:3100'
await mkdir(new URL('../test-artifacts/',import.meta.url),{recursive:true})
const browser=await chromium.launch({args:['--no-sandbox','--remote-debugging-port=9222']})
try {
 const page=await browser.newPage({viewport:{width:390,height:844}})
 await page.addInitScript(()=>{
  window.__vitals={lcp:0,cls:0,longTasks:0}
  new PerformanceObserver(list=>{for(const e of list.getEntries())window.__vitals.lcp=e.startTime}).observe({type:'largest-contentful-paint',buffered:true})
  new PerformanceObserver(list=>{for(const e of list.getEntries())if(!e.hadRecentInput)window.__vitals.cls+=e.value}).observe({type:'layout-shift',buffered:true})
  new PerformanceObserver(list=>{window.__vitals.longTasks+=list.getEntries().length}).observe({type:'longtask',buffered:true})
 })
 await page.goto(origin,{waitUntil:'networkidle'})
 const resources=await page.evaluate(()=>({vitals:window.__vitals,resources:performance.getEntriesByType('resource').map(r=>({name:r.name,transferSize:r.transferSize,duration:r.duration}))}))
 await writeFile(new URL('../test-artifacts/resource-profile.json',import.meta.url),JSON.stringify(resources,null,2))
 const result=await lighthouse(origin,{port:9222,output:['json','html'],onlyCategories:['performance','accessibility','best-practices','seo'],logLevel:'error'})
 await writeFile(new URL('../test-artifacts/lighthouse.json',import.meta.url),result.report[0])
 await writeFile(new URL('../test-artifacts/lighthouse.html',import.meta.url),result.report[1])
 const summary={mode:'Lighthouse simulated mobile, loopback production build; not field INP or physical phone',categories:Object.fromEntries(Object.entries(result.lhr.categories).map(([k,v])=>[k,Math.round(v.score*100)])),metrics:Object.fromEntries(['first-contentful-paint','largest-contentful-paint','total-blocking-time','cumulative-layout-shift','speed-index'].map(k=>[k,{value:result.lhr.audits[k].numericValue,display:result.lhr.audits[k].displayValue}])),resourceTransferBytes:resources.resources.reduce((n,r)=>n+r.transferSize,0)}
 await writeFile(new URL('../docs/PERFORMANCE_BASELINE.json',import.meta.url),JSON.stringify(summary,null,2)+'\n')
 console.log(JSON.stringify(summary,null,2))
} finally {await browser.close()}
