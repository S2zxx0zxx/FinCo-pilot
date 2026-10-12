'use client'
import { Squishmoji } from '@usespaceui/squishmoji/react'
import { useReducedMotion } from 'motion/react'

/** Procedural local illustration; not a portrait or social proof. */
export function IdentityAvatar({ seed, size = 42 }: { seed: string; size?: number }) {
  const reduceMotion = useReducedMotion()
  return <span className="inline-flex overflow-hidden rounded-2xl bg-secondary" aria-hidden="true"><Squishmoji seed={seed} size={size} shape="squircle" expression="happy" backgroundStyle="solid" animate={false} animOnHover={!reduceMotion} animOnClick={false} /></span>
}
