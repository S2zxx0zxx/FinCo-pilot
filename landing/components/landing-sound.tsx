'use client'

import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { useMediaQuery } from '@/hooks/use-media-query'
import { IconVolume, IconVolumeOff } from '@tabler/icons-react'
import { Button } from '@/components/spaceui/button'

// Adapts Space UI's sound-provider pattern: session-only opt-in, lazy engine,
// restrained volume and no automatic delegated event binding.
type SoundEngine = typeof import('@usespaceui/sounds')
const Context = createContext({ enabled: false, toggle: () => {}, cue: () => {} })

export function LandingSoundProvider({ children }: { children: React.ReactNode }) {
  const [enabled, setEnabled] = useState(false)
  const engine = useRef<SoundEngine | null>(null)
  const lastCue = useRef(0)
  const reduced = useMediaQuery('(prefers-reduced-motion: reduce)', true)

  useEffect(() => {
    engine.current?.setEnabled(enabled && !reduced)
    return () => engine.current?.setEnabled(false)
  }, [enabled, reduced])

  const toggle = () => {
    if (enabled) { engine.current?.setEnabled(false); setEnabled(false); return }
    if (reduced) return
    void import('@usespaceui/sounds').then(sound => {
      engine.current = sound
      sound.setVoiceSeed('FinCo-Pilot')
      sound.setRespectReducedMotion(true)
      sound.setVolume(0.2)
      sound.setEnabled(true)
      sound.toggle('on')
      setEnabled(true)
      lastCue.current = performance.now()
    }).catch(() => setEnabled(false))
  }
  const cue = () => {
    if (!enabled || reduced || !engine.current || performance.now() - lastCue.current < 1500) return
    try { engine.current.tap(); lastCue.current = performance.now() } catch { /* Audio must never block a control. */ }
  }
  return <Context.Provider value={{ enabled: enabled && !reduced, toggle, cue }}>{children}</Context.Provider>
}

export function useLandingSound() { return useContext(Context) }

export function SoundToggle() {
  const { enabled, toggle } = useLandingSound()
  const reduced = useMediaQuery('(prefers-reduced-motion: reduce)', true)
  return <Button className="sound-toggle" variant="outline" aria-pressed={enabled} onClick={toggle} disabled={Boolean(reduced)} title={reduced ? 'Sound effects are disabled with reduced motion' : 'Optional Space UI sound effects'}>
    {enabled ? <IconVolume size={16} aria-hidden="true"/> : <IconVolumeOff size={16} aria-hidden="true"/>}
    Sound {enabled ? 'on' : 'off'}
  </Button>
}
