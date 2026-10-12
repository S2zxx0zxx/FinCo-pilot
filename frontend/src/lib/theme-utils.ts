const MONOCHROME_THEME = {
  light: {
    primary: '#0A0A0A',
    ring: '#0A0A0A',
    sidebarPrimary: '#0A0A0A',
    accent: '#e9e9ed',
    accentForeground: '#18181b',
    muted: '#efeff1',
    sidebarAccent: '#e9e9ed',
    sidebarAccentForeground: '#18181b',
  },
  dark: {
    primary: '#FFFFFF',
    ring: '#FFFFFF',
    sidebarPrimary: '#FFFFFF',
    accent: '#303036',
    accentForeground: '#fafafa',
    muted: '#252529',
    sidebarAccent: '#252529',
    sidebarAccentForeground: '#fafafa',
  },
} as const

/**
 * Keep the historical function signature because auth/layout callers and the
 * backend still expose saved theme-color settings from older installations.
 * FinCo-Pilot's current identity is deliberately monochrome, so those legacy
 * values no longer override the visual system. This also prevents an existing
 * orange/coral setting in the database from reappearing after a page load.
 */
export function setThemeBasedOnSystem(
  _lightColor: string | null,
  _darkColor: string | null,
  resolvedTheme?: string,
) {
  const root = document.documentElement
  const palette = resolvedTheme === 'dark' ? MONOCHROME_THEME.dark : MONOCHROME_THEME.light

  root.style.setProperty('--primary', palette.primary)
  root.style.setProperty('--ring', palette.ring)
  root.style.setProperty('--sidebar-primary', palette.sidebarPrimary)
  root.style.setProperty('--accent', palette.accent)
  root.style.setProperty('--accent-foreground', palette.accentForeground)
  root.style.setProperty('--muted', palette.muted)
  root.style.setProperty('--sidebar-accent', palette.sidebarAccent)
  root.style.setProperty('--sidebar-accent-foreground', palette.sidebarAccentForeground)
}
