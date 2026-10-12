import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { chromium, firefox, webkit } from 'playwright'
import axe from 'axe-core'

const origin = process.env.LANDING_TEST_URL || 'http://127.0.0.1:3100'
const directory = new URL('../test-artifacts/', import.meta.url)
await mkdir(directory, { recursive: true })
const browserType = { chromium, firefox, webkit }[process.env.LANDING_BROWSER || 'chromium']
assert.ok(browserType, 'Unknown browser')
const browser = await browserType.launch({ headless: true, args: browserType === chromium ? ['--no-sandbox'] : [] })
const widths = [320,375,390,620,768,920,921,1024,1440]
const report = { browser: browserType.name(), widths: [], accessibility: [], checks: [] }

async function accessibility(page, state) {
  await page.evaluate(() => window.scrollTo({top:0,behavior:'instant'}))
  await page.addScriptTag({ content: axe.source })
  const violations = await page.evaluate(async () => (await window.axe.run(document, {
    runOnly: {type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']},
  })).violations.map(v => ({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,html:n.html,summary:n.failureSummary}))})))
  assert.deepEqual(violations, [], state + ': accessibility failures')
  report.accessibility.push({ state, violations })
}
try {
  for (const width of widths) {
    const reducedMotion = width === 375 ? 'reduce' : 'no-preference'
    const context = await browser.newContext({viewport:{width,height:width<500?812:900},hasTouch:width<500,reducedMotion})
    const page = await context.newPage(); const errors=[]; const external=[]
    page.on('pageerror',e=>errors.push(e.message))
    page.on('request',r=>{if(new URL(r.url()).origin!==new URL(origin).origin)external.push(r.url())})
    const response=await page.goto(origin,{waitUntil:'networkidle'})
    assert.equal(response.status(),200)
    assert.equal(await page.locator('h1').count(),1)
    assert.match(await page.locator('h1').innerText(),/Money.*makes.*more.*sense.*together/s)
    await page.evaluate(()=>document.fonts.ready)
    const dimensions=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}))
    assert.ok(dimensions.document<=dimensions.viewport+2,width+': horizontal overflow')
    for(const path of ['/login','/register','/pricing','/privacy','/terms','/support']) {
      const appOrigin=process.env.LANDING_APP_ORIGIN || 'https://fincopilot.app'
      assert.ok(await page.locator('a[href="'+appOrigin+path+'"]').count(), 'missing product destination '+path)
    }
    assert.ok(await page.getByText('Illustrative interface').count())
    assert.ok(await page.getByText('Actual application screens · Synthetic sample data · Screenshots, not live accounts').count())
    const sampleTabs=page.getByRole('tablist',{name:'Explore sample views'})
    for(const [name,text] of [['Budgets','₹24,800'],['Activity','18 items'],['Overview','₹1,84,250']]) {
      await sampleTabs.getByRole('tab',{name,exact:true}).click()
      assert.ok((await page.locator('.preview-body:not([inert]):visible').innerText()).includes(text))
      if(width===390||width===1440)await accessibility(page,width+':'+name)
    }
    await sampleTabs.getByRole('tab',{name:'Overview',exact:true}).focus()
    await page.keyboard.press('ArrowRight')
    assert.equal(await page.evaluate(()=>document.activeElement.textContent.trim()),'Budgets')
    assert.equal(await sampleTabs.getByRole('tab',{name:'Budgets',exact:true}).getAttribute('aria-selected'),'true')
    await page.keyboard.press('End')
    assert.equal(await page.evaluate(()=>document.activeElement.textContent.trim()),'Activity')
    await page.keyboard.press('Home')
    assert.equal(await page.evaluate(()=>document.activeElement.textContent.trim()),'Overview')
    assert.equal(await sampleTabs.locator('[tabindex="0"]').count(),1)
    const benefits=page.getByRole('tablist',{name:'Choose benefit'})
    await benefits.getByRole('tab',{name:'Understand what changed'}).focus();await page.keyboard.press('ArrowDown')
    assert.equal(await benefits.getByRole('tab',{name:'Stay in the driver’s seat'}).getAttribute('aria-selected'),'true')
    assert.ok(await page.getByRole('tabpanel').filter({hasText:'Keep your own financial workflow'}).isVisible())
    const screens=page.getByRole('tablist',{name:'Explore FinCo-Pilot screens'})
    await screens.getByRole('tab',{name:'Accounts',exact:true}).click()
    const img=page.locator('.product-capture img:visible')
    await img.scrollIntoViewIfNeeded();await page.waitForFunction(()=>[...document.querySelectorAll('.product-capture img')].filter(e=>e.offsetWidth).every(e=>e.complete&&e.naturalWidth>0))
    assert.match(await img.getAttribute('alt'),/Original FinCo-Pilot Accounts/)
    const imgSrc=await img.evaluate(e=>e.currentSrc)
    assert.ok(imgSrc.includes(width<=620?'accounts-mobile.webp':'accounts-desktop.webp'))
    await screens.getByRole('tab',{name:'Dashboard',exact:true}).click()
    await page.getByRole('button',{name:'Do I have to connect a bank account?',exact:true}).click()
    assert.ok(await page.getByText('FinCo-Pilot supports managing financial accounts and transactions manually.',{exact:false}).isVisible())
    if(width<=920) {
      const menu=page.getByRole('button',{name:'Open navigation',exact:true});await menu.click();await page.keyboard.press('Escape')
      assert.equal(await menu.getAttribute('aria-expanded'),'false')
      assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('aria-label')),'Open navigation')
      await menu.click();await page.getByRole('navigation',{name:'Mobile navigation'}).getByRole('link',{name:'Why FinCo'}).click()
      assert.equal(await menu.getAttribute('aria-expanded'),'false')
    }
    const sound=page.getByRole('button',{name:'Sound off',exact:true})
    assert.equal(await sound.getAttribute('aria-pressed'),'false')
    if(reducedMotion==='reduce') {
      assert.ok(await sound.isDisabled())
      const styles=await page.locator('h1').evaluate(e=>({opacity:getComputedStyle(e).opacity,filter:getComputedStyle(e).filter,scroll:getComputedStyle(document.documentElement).scrollBehavior}))
      assert.deepEqual(styles,{opacity:'1',filter:'none',scroll:'auto'})
      assert.equal(await page.locator('h1').getAttribute('data-reveal-static'),'true')
      assert.ok(await page.locator('h1 span').evaluateAll(els=>els.every(e=>getComputedStyle(e).opacity==='1'&&getComputedStyle(e).filter==='none')))
    }
    if (width===1440) {
      await sound.click()
      await page.waitForFunction(()=>document.querySelector('.sound-toggle')?.getAttribute('aria-pressed')==='true')
      await page.getByRole('button',{name:'Sound on',exact:true}).click()
      assert.equal(await sound.getAttribute('aria-pressed'),'false')
      await page.emulateMedia({ reducedMotion:'reduce' })
      await page.waitForFunction(()=>document.querySelector('h1')?.getAttribute('data-reveal-static')==='true')
      assert.ok(await sound.isDisabled())
      await page.emulateMedia({ reducedMotion:'no-preference' })
    }
    if(width===390||width===1440) {
      await accessibility(page,width+':full-page-final')
      await page.evaluate(()=>{history.replaceState(null,'',location.pathname);window.scrollTo({top:0,behavior:'instant'})})
      await page.screenshot({path:new URL(width+'-full.png',directory).pathname,fullPage:true,animations:'disabled'})
    }
    assert.deepEqual(errors,[],width+': page errors');assert.deepEqual(external,[],width+': third-party requests')
    report.widths.push({width,...dimensions,status:'passed'});await context.close()
  }
  const keyboard=await browser.newContext();const page=await keyboard.newPage();await page.goto(origin,{waitUntil:'networkidle'})
  await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.textContent.trim()),'Skip to content')
  await page.keyboard.press('Enter');assert.equal(new URL(page.url()).hash,'#main-content');await keyboard.close()
  const nojs=await browser.newContext({javaScriptEnabled:false});const n=await nojs.newPage();await n.goto(origin)
  assert.equal(await n.locator('h1').evaluate(e=>getComputedStyle(e).opacity),'1');assert.ok(await n.locator('h1').isVisible());await nojs.close()
  const touch=await browser.newContext({viewport:{width:390,height:812},hasTouch:true});const t=await touch.newPage();await t.goto(origin,{waitUntil:'networkidle'})
  const targets=await t.locator('.preview-tab').evaluateAll(els=>els.map(e=>{const r=e.getBoundingClientRect();return {w:r.width,h:r.height}}))
  assert.ok(targets.every(r=>r.w>=44&&r.h>=44));await touch.close()
  report.checks=['ArrowRight/Home/End tabs','ArrowDown benefit tabs','Escape menu focus','real product responsive pictures','no external assets','no-JS visible H1','reduced-motion static H1','44px preview targets','WCAG scans for every sample state','FAQ','CTA hrefs','skip link']
  console.log(JSON.stringify(report,null,2))
} finally {
  await writeFile(new URL(browserType.name()+'-acceptance.json',directory),JSON.stringify(report,null,2)+'\n')
  await browser.close()
}
