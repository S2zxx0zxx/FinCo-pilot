const MONOCHROME_THEME = {
  light: {
    primary: '#0A0A0A',
    ring: '#0A0A0A',
    sidebarPrimary: '#0A0A0A',
    accent: '#F1F1F2',
    accentForeground: '#09090B',
    muted: '#F4F4F5',
    sidebarAccent: '#F1F1F2',
    sidebarAccentForeground: '#09090B',
  },
  dark: {
    primary: '#FFFFFF',
    ring: '#FFFFFF',
    sidebarPrimary: '#FFFFFF',
    accent: '#171717',
    accentForeground: '#FAFAFA',
    muted: '#151515',
    sidebarAccent: '#151515',
    sidebarAccentForeground: '#FAFAFA',
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
