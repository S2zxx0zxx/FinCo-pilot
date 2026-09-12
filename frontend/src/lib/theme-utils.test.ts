import { afterEach, describe, expect, it } from 'vitest'

import { setThemeBasedOnSystem } from '@/lib/theme-utils'

const VARS = [
  '--primary',
  '--ring',
  '--sidebar-primary',
  '--accent',
  '--accent-foreground',
  '--muted',
  '--sidebar-accent',
  '--sidebar-accent-foreground',
]

function readVar(name: string): string {
  return document.documentElement.style.getPropertyValue(name)
}

afterEach(() => {
  for (const name of VARS) {
    document.documentElement.style.removeProperty(name)
  }
})

describe('setThemeBasedOnSystem', () => {
  it('uses the canonical black primary on a light theme', () => {
    setThemeBasedOnSystem('#ff7a59', '#818cf8', 'light')

    expect(readVar('--primary')).toBe('#0A0A0A')
    expect(readVar('--ring')).toBe('#0A0A0A')
    expect(readVar('--sidebar-primary')).toBe('#0A0A0A')
  })

  it('uses the canonical white primary on a dark theme', () => {
    setThemeBasedOnSystem('#ff7a59', '#818cf8', 'dark')

    expect(readVar('--primary')).toBe('#FFFFFF')
    expect(readVar('--ring')).toBe('#FFFFFF')
    expect(readVar('--sidebar-primary')).toBe('#FFFFFF')
  })

  it('treats an unknown theme as light', () => {
    setThemeBasedOnSystem('#ff7a59', '#818cf8', undefined)

    expect(readVar('--primary')).toBe('#0A0A0A')
  })

  it('keeps saved legacy colors from recoloring the product', () => {
    setThemeBasedOnSystem('#ff7a59', '#ff7a59', 'light')
    expect(readVar('--primary')).not.toBe('#ff7a59')

    setThemeBasedOnSystem('#ff7a59', '#ff7a59', 'dark')
    expect(readVar('--primary')).not.toBe('#ff7a59')
  })

  it('uses neutral surface accents in both modes', () => {
    setThemeBasedOnSystem(null, null, 'light')
    expect(readVar('--accent')).toBe('#F1F1F2')
    expect(readVar('--accent-foreground')).toBe('#09090B')
    expect(readVar('--muted')).toBe('#F4F4F5')

    setThemeBasedOnSystem(null, null, 'dark')
    expect(readVar('--accent')).toBe('#171717')
    expect(readVar('--accent-foreground')).toBe('#FAFAFA')
    expect(readVar('--muted')).toBe('#151515')
  })

  it('sets every shared theme variable even when old settings are absent', () => {
    setThemeBasedOnSystem(null, null, 'light')

    for (const name of VARS) {
      expect(readVar(name), name).not.toBe('')
    }
  })
})
