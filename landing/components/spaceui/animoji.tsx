'use client'

import * as React from 'react'
import { useMediaQuery } from '@/hooks/use-media-query'
import Image from 'next/image'
import { landingAsset } from '@/lib/asset'
import emojiRegex from 'emoji-regex'
import type { EmojiSource } from '@usespaceui/emoji'
import { useInView } from 'motion/react'
import { cn } from '@/lib/utils'

export type Segment = { kind: 'text'; value: string } | { kind: 'emoji'; value: string }

// A bare hex codepoint word, e.g. "1f496" or the two-part "1f1e8-1f1ee" for a flag.
const CODEPOINT_TOKEN = /^[0-9a-fA-F]{4,6}(?:[-_][0-9a-fA-F]{4,6})*$/

// Codepoint words only count on their own, between whitespace — never mid-word,
// so plain hex-looking text like "decade" or "cafe" is never mistaken for one.
function splitCodepoints(text: string): Segment[] {
  return text.split(/(\s+)/).map((part) => {
    if (CODEPOINT_TOKEN.test(part)) {
      try {
        return { kind: 'emoji', value: String.fromCodePoint(...part.split(/[-_]/).map(value => Number.parseInt(value, 16))) }
      } catch {
        return { kind: 'text', value: part }
      }
    }
    return { kind: 'text', value: part }
  })
}

// Same regex @usespaceui/emoji resolves codepoints with, so flags/ZWJ combos stay one match.
export function splitEmoji(text: string): Segment[] {
  const segments: Segment[] = []
  let lastIndex = 0
  for (const match of text.matchAll(emojiRegex())) {
    const index = match.index ?? 0
    if (index > lastIndex) segments.push(...splitCodepoints(text.slice(lastIndex, index)))
    segments.push({ kind: 'emoji', value: match[0] })
    lastIndex = index + match[0].length
  }
  if (lastIndex < text.length) segments.push(...splitCodepoints(text.slice(lastIndex)))
  return segments
}

function EmojiGlyph({ emoji, source, className, localAssets }: { emoji: string; source: EmojiSource; className?: string; localAssets?: boolean }) {
  const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)', true)
  const ref = React.useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true, amount: 0.4 })
  const [resolved, setResolved] = React.useState('')
  React.useEffect(() => {
    if (localAssets || !inView) return
    let active = true
    void import('@usespaceui/emoji').then(({ resolveEmojiUrl, EmojiType }) => {
      if (active) setResolved(resolveEmojiUrl(emoji, { source, type: reducedMotion ? EmojiType.ThreeD : EmojiType.Anim, fallback: true } as never))
    }).catch(() => { if (active) setResolved('') })
    return () => { active = false }
  }, [emoji, source, reducedMotion, localAssets, inView])
  const src = localAssets && emoji === '🧭'
    ? landingAsset(!reducedMotion && inView ? '/emoji/compass.webp' : '/emoji/compass-still.webp')
    : resolved
  const [failed, setFailed] = React.useState(false)
  React.useEffect(() => setFailed(false), [src])

  // Raw glyph fallback rather than break the sentence.
  if (!src || failed) return <span ref={ref}>{emoji}</span>

  return (
    <span ref={ref}><Image
      src={src}
      alt={emoji}
      width={48}
      height={48}
      unoptimized
      draggable={false}
      onError={() => setFailed(true)}
      className={cn('pointer-events-none inline-block h-[1em] w-[1em] object-contain align-[-0.1em]', className)}
    /></span>
  )
}

/** Providers with an animated style — Apple, Twemoji and Blobmoji have none. */
export type AnimojiSource = typeof EmojiSource.Fluent | typeof EmojiSource.Telegram | typeof EmojiSource.Noto

export type AnimojiProps = {
  children: string
  /** @default 'fluent' */
  source?: AnimojiSource
  className?: string
  emojiClassName?: string
  /** Self-hosted Fluent compass assets avoid third-party requests. */
  localAssets?: boolean
}

/** Renders every Unicode emoji in `children` as an animated image sized to the surrounding text. */
export function Animoji({ children, source = 'fluent', className, emojiClassName, localAssets }: AnimojiProps) {
  return (
    <span className={cn('inline', className)}>
      {splitEmoji(children).map((segment, index) =>
        segment.kind === 'text' ? (
          <React.Fragment key={index}>{segment.value}</React.Fragment>
        ) : (
          <EmojiGlyph key={index} emoji={segment.value} source={source} className={emojiClassName} localAssets={localAssets} />
        ),
      )}
    </span>
  )
}
