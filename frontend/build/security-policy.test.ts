import { describe, expect, it } from 'vitest'
import { compileStrictCsp, scriptIntegrity } from './security-policy'

describe('artifact-bound strict CSP', () => {
  it('trusts exact inline content and SRI-bound entries without unsafe script policies', () => {
    const code = 'window.example = 1;'
    const sri = scriptIntegrity('entry bytes')
    const csp = compileStrictCsp(`<script>${code}</script><script type="module" src="/static/entry.js" integrity="${sri}"></script>`)
    expect(csp).toContain(`'${scriptIntegrity(code)}'`)
    expect(csp).toContain(`'${sri}' 'strict-dynamic'`)
    expect(csp.split('script-src-attr')[0]).not.toMatch(/unsafe-inline|unsafe-eval/)
    expect(compileStrictCsp(`<script>${code} </script>`)).not.toEqual(compileStrictCsp(`<script>${code}</script>`))
  })
  it('rejects unbound external scripts rather than guessing a policy', () => {
    expect(() => compileStrictCsp('<script src="/unknown.js"></script>')).toThrow(/lacks/)
    expect(() => compileStrictCsp('<html></html>')).toThrow(/No trusted/)
  })
})
