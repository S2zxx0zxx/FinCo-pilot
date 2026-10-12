// Space UI theme-toggle circle reveal adapted to FinCo's next-themes provider.
import { flushSync } from 'react-dom'
import { useTheme } from 'next-themes'
import { Sun, Moon } from 'lucide-react'
import { useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { useMediaQuery } from '@/hooks/spaceui/use-media-query'

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const { t } = useTranslation()
  const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
  const busy = useRef(false)
  const dark = resolvedTheme === 'dark'
  const label = dark ? t('settings.themeLight') : t('settings.themeDark')
  async function toggle(event: React.MouseEvent<HTMLButtonElement>) {
    if (busy.current) return
    const next = dark ? 'light' : 'dark'
    if (reducedMotion || !document.startViewTransition) { setTheme(next); return }
    const { x, y, width, height } = event.currentTarget.getBoundingClientRect()
    const cx = x + width / 2, cy = y + height / 2
    const radius = Math.hypot(Math.max(cx, innerWidth - cx), Math.max(cy, innerHeight - cy))
    busy.current = true
    try {
      const transition = document.startViewTransition(() => flushSync(() => setTheme(next)))
      await transition.ready
      document.documentElement.animate({ clipPath: [`circle(0px at ${cx}px ${cy}px)`, `circle(${radius}px at ${cx}px ${cy}px)`] },
        { duration: 350, easing: 'cubic-bezier(0.22,1,0.36,1)', pseudoElement: '::view-transition-new(root)' })
      await transition.finished
    } catch { setTheme(next) } finally { busy.current = false }
  }
  return <Button type="button" variant="ghost" size="icon-sm" onClick={toggle} title={label} aria-label={label}>
    {dark ? <Sun size={17} /> : <Moon size={17} />}
  </Button>
}
