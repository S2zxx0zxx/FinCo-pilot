import { useMediaQuery } from '@/hooks/spaceui/use-media-query'

// Preserve the existing finance-grid breakpoint and sorting behaviour.
export function useIsMobile(): boolean {
  return useMediaQuery('(max-width: 767px)')
}
