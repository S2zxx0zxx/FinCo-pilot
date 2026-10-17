'use client'

import { useMediaQuery } from '@/hooks/use-media-query'

import * as React from 'react'
import { motion, type Variants } from 'motion/react'
import { useInView } from '@/hooks/use-in-view'
import { cn } from '@/lib/utils'

export type SplitMode = 'words' | 'characters' | 'lines'

export type RevealDirection = 'up' | 'down' | 'none'

export interface BlurRevealTextProps extends React.HTMLAttributes<HTMLElement> {
  /** The text content to animate */
  text: string
  /** HTML element tag to render. @default "p" */
  as?: React.ElementType
  /** Custom class for the outer wrapper */
  className?: string
  /** Custom class for each word/character token */
  segmentClassName?: string
  /** Splitting strategy: 'words', 'characters', or 'lines'. @default "words" */
  splitBy?: SplitMode
  /** Delay between each animated segment in seconds. @default 0.05 */
  stagger?: number
  /** Initial delay before starting the animation in seconds. @default 0.1 */
  delay?: number
  /** Initial blur filter before revealing. @default "12px" */
  blurAmount?: string
  /** Duration of each segment's transition in seconds. @default 0.35 */
  duration?: number
  /** Direction from which tokens slide in. @default "up" */
  direction?: RevealDirection
  /** Distance in pixels tokens move along the Y-axis. @default 8 */
  yOffset?: number
  /** Whether animation triggers only when element enters the viewport. @default true */
  inView?: boolean
  /** Only animate once when entering view. @default true */
  once?: boolean
  /** Changing this key triggers a replay of the animation */
  replayKey?: string | number
  /** Overrides how each segment renders, e.g. to run it through Textmoji. Defaults to the raw segment text. */
  renderSegment?: (segment: string) => React.ReactNode
}

function splitText(text: string, mode: SplitMode): string[] {
  if (!text) return []
  if (mode === 'characters') {
    return Array.from(text)
  }
  if (mode === 'lines') {
    return text.split('\n')
  }
  // Default: words (splitting by spaces while preserving word tokens)
  return text.split(' ')
}

export const BlurRevealText: React.FC<BlurRevealTextProps> = ({
  text,
  as: Component = 'p',
  className,
  segmentClassName,
  splitBy = 'words',
  stagger = 0.05,
  delay = 0.1,
  blurAmount = '12px',
  duration = 0.35,
  direction = 'up',
  yOffset = 8,
  inView = true,
  once = true,
  replayKey,
  renderSegment,
  style,
  ...props
}) => {
  const reduceMotion = useMediaQuery('(prefers-reduced-motion: reduce)', true)
  const [hydrated, setHydrated] = React.useState(false)
  React.useEffect(() => setHydrated(true), [])
  const [containerRef, isElementInView] = useInView({ triggerOnce: once, fallbackInView: true })

  const shouldAnimate = inView ? isElementInView : true

  const segments = React.useMemo(() => splitText(text, splitBy), [text, splitBy])

  const initialY = direction === 'up' ? yOffset : direction === 'down' ? -yOffset : 0

  const segmentVariants: Variants = {
    hidden: {
      opacity: 1,
      filter: `blur(${blurAmount})`,
      y: initialY,
      willChange: 'filter, transform, opacity',
    },
    visible: {
      opacity: 1,
      filter: 'none',
      y: 0,
      willChange: 'auto',
    },
  }

  const staticReveal = !hydrated || reduceMotion
  // Keep the observed heading mounted across hydration and preference changes.
  // Server/no-JS text stays readable; only the word spans enhance to Motion.
  return (
    <Component
      ref={containerRef}
      className={cn('inline-flex flex-wrap items-baseline',
        className?.includes('text-center') && 'justify-center',
        className?.includes('text-right') && 'justify-end', className)}
      style={style}
      aria-label={text}
      data-reveal-static={staticReveal ? 'true' : undefined}
      {...props}
    >
      {segments.map((segment, index) => {
        const displayText = splitBy === 'words'
          ? segment + (index < segments.length - 1 ? '\u00A0' : '')
          : segment === ' ' ? '\u00A0' : segment
        const content = renderSegment ? renderSegment(displayText) : displayText
        const classes = cn('inline-block whitespace-pre', segmentClassName)
        return staticReveal
          ? <span key={`${segment}-${index}`} className={classes}>{content}</span>
          : <motion.span key={`${replayKey ?? ''}-${segment}-${index}`} aria-hidden="true" className={classes}
              initial="hidden" animate={shouldAnimate ? 'visible' : 'hidden'} variants={segmentVariants}
              transition={{ duration, delay: delay + Math.min(index * stagger, 0.3), ease: [0.22, 1, 0.36, 1] }}
            >{content}</motion.span>
      })}
    </Component>
  )
}
