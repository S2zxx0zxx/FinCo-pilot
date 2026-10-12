'use client'
import { Squishmoji } from '@usespaceui/squishmoji/react'

/** Procedural local illustration; not a portrait or social proof. */
export function IdentityAvatar({ seed, size = 42 }: { seed: string; size?: number }) {
  return <span className="inline-flex overflow-hidden rounded-2xl bg-secondary" aria-hidden="true"><Squishmoji seed={seed} size={size} shape="squircle" expression="happy" backgroundStyle="solid" animate={false} animOnHover={true} animOnClick={false} /></span>
}
