import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { chromium, firefox, webkit } from 'playwright'
import axe from 'axe-core'
const origin = process.env.LANDING_TEST_URL || 'http://127.0.0.1:3100'
const directory = new URL('../test-artifacts/', import.meta.url)
await mkdir(directory, { recursive: true })
const browserType = { chromium, firefox, webkit }[
  process.env.LANDING_BROWSER || 'chromium'
]
assert.ok(browserType, 'Unknown browser')
const browser = await browserType.launch({
  headless: true,
  args: browserType === chromium ? ['--no-sandbox'] : [],
})
const report = {
  browser: browserType.name(),
  widths: [],
  accessibility: [],
  checks: [],
}
async function accessibility(page, state) {
  await page.waitForFunction(
    () =>
      [...document.querySelectorAll('.modal__backdrop,.popover')].every(
        (overlay) =>
          overlay.getAttribute('data-entering') !== 'true' &&
          !overlay.querySelector('[data-entering="true"]') &&
          overlay
            .getAnimations({ subtree: true })
            .every(
              (animation) =>
                animation.playState !== 'running' && !animation.pending,
            ),
      ),
    null,
    { timeout: 5000 },
  )
  await page.addScriptTag({ content: axe.source })
  const violations = await page.evaluate(async () =>
    (
      await window.axe.run(document, {
        runOnly: {
          type: 'tag',
          values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'],
        },
      })
    ).violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        html: n.html,
        summary: n.failureSummary,
      })),
    })),
  )
  assert.deepEqual(violations, [], state + ': accessibility failures')
  report.accessibility.push({ state, violations })
  console.log('PASS: accessibility ' + state)
}
try {
  for (const width of [320, 375, 390, 620, 768, 920, 921, 1024, 1440]) {
    const reducedMotion = width === 375 ? 'reduce' : 'no-preference'
    const context = await browser.newContext({
      viewport: { width, height: width < 500 ? 812 : 900 },
      hasTouch: width < 500,
      reducedMotion,
    })
    const page = await context.newPage()
    // Match the declared touch context with real touchscreen input.
    const activate = (locator) =>
      width < 500 ? locator.tap() : locator.click()
    const errors = []
    const external = []
    page.on('pageerror', (e) => errors.push(e.message))
    page.on('request', (r) => {
      if (new URL(r.url()).origin !== new URL(origin).origin)
        external.push(r.url())
    })
    const response = await page.goto(origin, { waitUntil: 'networkidle' })
    assert.equal(response.status(), 200)
    assert.equal(await page.locator('h1').count(), 1)
    assert.match(
      await page.locator('h1').innerText(),
      /Bank balance.*Meet real life/s,
    )
    await page.evaluate(() => document.fonts.ready)
    const dimensions = await page.evaluate(() => ({
      viewport: innerWidth,
      document: document.documentElement.scrollWidth,
    }))
    assert.ok(
      dimensions.document <= dimensions.viewport + 2,
      width + ': horizontal overflow',
    )
    const appOrigin = process.env.LANDING_APP_ORIGIN ?? 'https://fincopilot.app'
    for (const path of [
      '/login',
      '/register',
      '/pricing',
      '/privacy',
      '/terms',
      '/support',
    ]) {
      assert.ok(
        await page.locator('a[href="' + appOrigin + path + '"]').count(),
        'missing product destination ' + path,
      )
    }
    assert.ok(
      await page.getByText('Illustrative interface', { exact: false }).count(),
    )
    assert.equal(await page.locator('.feature-card').count(), 6)
    const buffer = page.getByRole('textbox', {
      name: 'Emergency buffer to protect',
      exact: true,
    })
    for (const [value, title, result] of [
      ['20000', 'Illustrative remainder', '₹15,000'],
      ['35000', 'Illustrative remainder', '₹0'],
      ['40000', 'Illustrative shortfall', '₹5,000'],
    ]) {
      await buffer.fill(value)
      await buffer.blur()
      assert.ok(
        (await page.locator('.example-result').innerText()).includes(title),
      )
      assert.ok(
        (await page.locator('.example-result').innerText()).includes(result),
      )
    }
    await buffer.fill('')
    await buffer.blur()
    assert.ok(
      await page
        .getByText('Enter a buffer to see the example.', { exact: true })
        .isVisible(),
    )
    await buffer.fill('10000')
    await buffer.blur()
    // Native HeroUI NumberField must keep both steppers in the same row.
    const fieldLayout = await page
      .locator('.number-field__group')
      .evaluateAll((groups) =>
        groups.flatMap((group) => {
          const box = group.getBoundingClientRect()
          return [...group.querySelectorAll('input,button')].map((child) => {
            const rect = child.getBoundingClientRect()
            return {
              inside:
                rect.left >= box.left &&
                rect.right <= box.right + 1 &&
                rect.top >= box.top &&
                rect.bottom <= box.bottom + 1,
            }
          })
        }),
      )
    assert.ok(
      fieldLayout.every((item) => item.inside),
      width + ': numeric controls must fit their group',
    )
    await buffer.focus()
    await page.keyboard.press('ArrowUp')
    await buffer.blur()
    assert.match(await page.locator('.example-result').innerText(), /₹24,000/)
    await buffer.focus()
    await page.keyboard.press('ArrowDown')
    await buffer.blur()
    assert.match(await page.locator('.example-result').innerText(), /₹25,000/)
    if (width === 390 || width === 1440)
      await accessibility(page, width + ':demo')
    const screens = page.locator('.product-tabs').getByRole('tablist')
    await activate(screens.getByRole('tab', { name: /Accounts$/ }))
    const accountsPanel = page.getByRole('tabpanel', {
      name: 'Accounts',
      exact: true,
    })
    await accountsPanel.waitFor({ state: 'visible' })
    const img = accountsPanel.locator('.product-capture img')
    await img.scrollIntoViewIfNeeded()
    await page.waitForFunction(() =>
      [...document.querySelectorAll('.product-capture img')]
        .filter((e) => e.offsetWidth)
        .every((e) => e.complete && e.naturalWidth > 0),
    )
    assert.match(await img.getAttribute('alt'), /Original FinCo-Pilot Accounts/)
    assert.ok(
      (await img.evaluate((e) => e.currentSrc)).includes(
        width <= 620 ? 'accounts-mobile.webp' : 'accounts-desktop.webp',
      ),
    )
    await screens.getByRole('tab', { name: /Dashboard$/ }).focus()
    await page.keyboard.press('ArrowRight')
    await page.keyboard.press('Enter')
    await screens
      .getByRole('tab', { name: /Accounts$/, selected: true })
      .waitFor()
    assert.equal(
      await screens
        .getByRole('tab', { name: /Accounts$/ })
        .getAttribute('aria-selected'),
      'true',
    )
    await activate(screens.getByRole('tab', { name: /Dashboard$/ }))
    if (width === 390 || width === 1440) {
      // Every new surface is exercised with real touch or mouse input.
      await activate(
        page.getByRole('radio', { name: 'Bills-heavy month', exact: true }),
      )
      assert.match(await page.locator('.example-result').innerText(), /₹9,000/)
      await activate(
        page.getByRole('radio', { name: 'Bigger savings goal', exact: true }),
      )
      assert.match(await page.locator('.example-result').innerText(), /₹10,000/)
      await activate(
        page.getByRole('button', {
          name: 'Reset spending example',
          exact: true,
        }),
      )
      assert.match(await page.locator('.example-result').innerText(), /₹25,000/)
      await page
        .getByRole('slider', {
          name: 'Savings goal reserve slider',
          exact: true,
        })
        .focus()
      await page.keyboard.press('ArrowRight')
      assert.match(await page.locator('.example-result').innerText(), /₹24,000/)
      await activate(
        page.getByRole('button', {
          name: 'Reset spending example',
          exact: true,
        }),
      )
      await activate(
        page.getByRole('button', {
          name: 'What is included in this example?',
          exact: true,
        }),
      )
      await page
        .getByRole('dialog', {
          name: 'Three reserves. One sample balance.',
          exact: true,
        })
        .waitFor()
      await accessibility(page, width + ':calculation-explained')
      await page.keyboard.press('Escape')
      await page
        .getByRole('dialog', {
          name: 'Three reserves. One sample balance.',
          exact: true,
        })
        .waitFor({ state: 'hidden' })
      for (const title of ['Budgets', 'Goals', 'Recurring', 'Reports']) {
        await activate(
          screens.getByRole('tab', { name: new RegExp(title + '$') }),
        )
        const panel = page.getByRole('tabpanel', { name: title, exact: true })
        await panel.waitFor({ state: 'visible' })
        await panel.locator('.product-capture img').evaluate(async (img) => {
          if (!img.complete)
            await new Promise((resolve) =>
              img.addEventListener('load', resolve, { once: true }),
            )
          if (!img.naturalWidth) throw new Error('Missing product image')
        })
      }
      await activate(
        page.getByRole('button', {
          name: 'Expand Reports screen',
          exact: true,
        }),
      )
      await page
        .getByRole('dialog', {
          name: 'Reports — actual application',
          exact: true,
        })
        .waitFor()
      await page.waitForFunction(() =>
        document.activeElement?.closest('.screen-lightbox'),
      )
      await accessibility(page, width + ':expanded-product')
      await page.keyboard.press('Escape')
      await page
        .getByRole('dialog', {
          name: 'Reports — actual application',
          exact: true,
        })
        .waitFor({ state: 'hidden' })
      await page.waitForFunction(() =>
        document.activeElement?.textContent?.includes('Expand Reports screen'),
      )
      await activate(
        page.getByRole('button', {
          name: 'Expand Reports screen',
          exact: true,
        }),
      )
      await page
        .getByRole('dialog', {
          name: 'Reports — actual application',
          exact: true,
        })
        .waitFor()
      await activate(
        page.getByRole('button', {
          name: 'Close expanded screen',
          exact: true,
        }),
      )
      await page
        .getByRole('dialog', {
          name: 'Reports — actual application',
          exact: true,
        })
        .waitFor({ state: 'hidden' })
      await activate(
        page.getByRole('button', { name: 'Take the 3-step tour', exact: true }),
      )
      const tour = page.getByRole('dialog', {
        name: '01 / Start with one account',
        exact: true,
      })
      await tour.waitFor()
      await activate(
        page.getByRole('button', { name: 'Next tour step', exact: true }),
      )
      await page
        .getByRole('dialog', {
          name: '02 / Review the records behind it',
          exact: true,
        })
        .waitFor()
      await activate(
        page.getByRole('button', { name: 'Next tour step', exact: true }),
      )
      await page
        .getByRole('dialog', {
          name: '03 / Give the next step a purpose',
          exact: true,
        })
        .waitFor()
      await accessibility(page, width + ':tour')
      await activate(
        page.getByRole('button', { name: 'Previous tour step', exact: true }),
      )
      await page
        .getByRole('dialog', {
          name: '02 / Review the records behind it',
          exact: true,
        })
        .waitFor()
      await page.keyboard.press('Escape')
      await page.getByRole('dialog').waitFor({ state: 'hidden' })
      await activate(
        page.getByRole('button', { name: 'Inspect the mapping', exact: true }),
      )
      await page
        .getByRole('tabpanel', { name: '2. Check the mapping', exact: true })
        .waitFor()
      await activate(
        page.getByRole('button', { name: 'Review sample rows', exact: true }),
      )
      await page
        .getByRole('tabpanel', { name: '3. Review the proposal', exact: true })
        .waitFor()
      assert.match(await page.locator('.import-net').innerText(), /₹750/)
      await accessibility(page, width + ':import-preview')
      await activate(
        page.getByRole('button', {
          name: 'Back to the sample file',
          exact: true,
        }),
      )
      await page
        .getByRole('tabpanel', { name: '1. Choose a file', exact: true })
        .waitFor()
      const billing = page.getByRole('radiogroup', {
        name: 'Plan billing interval',
        exact: true,
      })
      await activate(
        billing.getByRole('radio', { name: 'Annual', exact: true }),
      )
      assert.match(
        await page.locator('.plan-pro .plan-price').innerText(),
        /₹999/,
      )
      assert.match(
        await page.locator('.plan-max .plan-price').innerText(),
        /No standard annual option/,
      )
      await activate(
        billing.getByRole('radio', { name: 'Monthly', exact: true }),
      )
      assert.match(
        await page.locator('.plan-pro .plan-price').innerText(),
        /₹99/,
      )
      await activate(
        page.getByRole('button', { name: 'Five more questions', exact: true }),
      )
      const aiQuestion = page.getByRole('button', {
        name: 'Are AI features required?',
        exact: true,
      })
      await activate(aiQuestion)
      await page
        .getByText(
          'Accounts, transactions and the core financial workspace are independent of optional AI capabilities.',
          { exact: false },
        )
        .waitFor()
      await accessibility(page, width + ':more-FAQ')
      await activate(
        page.getByRole('button', { name: 'Five more questions', exact: true }),
      )
      await aiQuestion.waitFor({ state: 'hidden' })
      if (width === 390) {
        await page.locator('#perspective').scrollIntoViewIfNeeded()
        await page
          .getByRole('navigation', { name: 'Quick actions', exact: true })
          .waitFor()
        await buffer.focus()
        await page
          .getByRole('navigation', { name: 'Quick actions', exact: true })
          .waitFor({ state: 'hidden' })
        await buffer.blur()
        await page
          .getByRole('navigation', { name: 'Quick actions', exact: true })
          .waitFor()
        await page.locator('.final-section').scrollIntoViewIfNeeded()
        await page
          .getByRole('navigation', { name: 'Quick actions', exact: true })
          .waitFor({ state: 'hidden' })
      }
      await activate(screens.getByRole('tab', { name: /Dashboard$/ }))
    }
    const faq = page.getByRole('button', {
      name: 'Do I have to connect a bank account?',
      exact: true,
    })
    await activate(faq)
    await page
      .getByRole('button', {
        name: 'Do I have to connect a bank account?',
        exact: true,
        expanded: true,
      })
      .waitFor()
    assert.equal(await faq.getAttribute('aria-expanded'), 'true')
    assert.ok(
      await page
        .getByText(
          'FinCo-Pilot supports managing financial accounts and transactions manually.',
          { exact: false },
        )
        .isVisible(),
    )
    if (width === 390 || width === 1440)
      await accessibility(page, width + ':FAQ-open')
    await activate(faq)
    await page
      .getByRole('button', {
        name: 'Do I have to connect a bank account?',
        exact: true,
        expanded: false,
      })
      .waitFor()
    assert.equal(await faq.getAttribute('aria-expanded'), 'false')
    await page
      .getByText(
        'FinCo-Pilot supports managing financial accounts and transactions manually.',
        { exact: false },
      )
      .waitFor({ state: 'hidden' })
    if (width <= 920) {
      const menu = page.getByRole('button', {
        name: 'Open navigation',
        exact: true,
      })
      await activate(menu)
      await page
        .getByRole('navigation', { name: 'Mobile navigation' })
        .waitFor()
      assert.equal(await menu.getAttribute('aria-expanded'), 'true')
      // Inspect the settled drawer, after HeroUI's native entering state and fades.
      await page.waitForFunction(
        () => {
          const backdrop = document.querySelector('.drawer__backdrop')
          return (
            backdrop &&
            !backdrop.querySelector('[data-entering="true"]') &&
            backdrop.getAttribute('data-entering') !== 'true' &&
            backdrop
              .getAnimations({ subtree: true })
              .every(
                (animation) =>
                  animation.playState !== 'running' && !animation.pending,
              )
          )
        },
        null,
        { timeout: 5000 },
      )
      if (width === 390) await accessibility(page, '390:drawer-open')
      await page.keyboard.press('Escape')
      await page
        .getByRole('navigation', { name: 'Mobile navigation' })
        .waitFor({ state: 'hidden' })
      await page.waitForFunction(
        () =>
          document.activeElement?.getAttribute('aria-label') ===
          'Open navigation',
      )
      assert.equal(await menu.getAttribute('aria-expanded'), 'false')
      await activate(menu)
      await activate(
        page
          .getByRole('navigation', { name: 'Mobile navigation' })
          .getByRole('link', { name: /Why FinCo/ }),
      )
      await page
        .getByRole('navigation', { name: 'Mobile navigation' })
        .waitFor({ state: 'hidden' })
      assert.equal(await menu.getAttribute('aria-expanded'), 'false')
    }
    if (reducedMotion === 'reduce') {
      assert.equal(
        await page.evaluate(
          () => getComputedStyle(document.documentElement).scrollBehavior,
        ),
        'auto',
      )
      assert.equal(
        await page
          .locator('.hero-copy')
          .evaluate((e) => getComputedStyle(e).animationName),
        'none',
      )
    }
    const sample = page.getByRole('link', {
      name: 'Download the sample CSV',
      exact: true,
    })
    const csv = await context.request.get(
      new URL(await sample.getAttribute('href'), origin).href,
    )
    assert.equal(csv.status(), 200)
    assert.match(await csv.text(), /Synthetic grocery,-250\.00,INR/)
    if (width === 390 || width === 1440) {
      await accessibility(page, width + ':final')
      await page.evaluate(() => {
        history.replaceState(null, '', location.pathname)
        window.scrollTo({ top: 0, behavior: 'instant' })
      })
      await page.screenshot({
        path: new URL(width + '-full.png', directory).pathname,
        fullPage: true,
        animations: 'disabled',
      })
    }
    assert.deepEqual(errors, [], width + ': page errors')
    assert.deepEqual(external, [], width + ': third-party requests')
    report.widths.push({ width, ...dimensions, status: 'passed' })
    await context.close()
    console.log(`PASS: ${browserType.name()} landing at ${width}px`)
  }
  const keyboard = await browser.newContext()
  const page = await keyboard.newPage()
  await page.goto(origin, { waitUntil: 'networkidle' })
  await page.keyboard.press('Tab')
  assert.equal(
    await page.evaluate(() => document.activeElement.textContent.trim()),
    'Skip to content',
  )
  await page.keyboard.press('Enter')
  assert.equal(new URL(page.url()).hash, '#main-content')
  await keyboard.close()
  const nojs = await browser.newContext({ javaScriptEnabled: false })
  const n = await nojs.newPage()
  await n.goto(origin)
  assert.ok(await n.locator('h1').isVisible())
  assert.equal(
    await n.locator('.hero-copy').evaluate((e) => getComputedStyle(e).opacity),
    '1',
  )
  assert.equal(
    await n
      .locator('.balance-card')
      .evaluate((e) => getComputedStyle(e).borderTopStyle),
    'solid',
    'HeroUI card styles must work before hydration',
  )
  await nojs.close()
  report.checks = [
    'sample input positive/zero/shortfall/empty states',
    'presets, reset, sliders and explanation popover',
    'six app views, screenshot zoom and three-step guided tour',
    'sample import mapping and review with accessible Table',
    'standard monthly/annual plan preview',
    'additional FAQ disclosure',
    'mobile CTA visibility while editing and at final CTA',
    'keyboard product tabs',
    'Escape drawer focus and anchor close',
    'real responsive product pictures',
    'no external requests',
    'no-JS visible H1 and styled HeroUI card',
    'reduced motion',
    'WCAG22 scans in demo, FAQ and drawer states',
    'FAQ open/close',
    'CTA hrefs',
    'sample CSV download',
    'skip link',
  ]
  console.log(JSON.stringify(report, null, 2))
} finally {
  await writeFile(
    new URL(browserType.name() + '-acceptance.json', directory),
    JSON.stringify(report, null, 2) + '\n',
  )
  await browser.close()
}
