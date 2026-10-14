// Adapted from Space UI BlurRevealText (MIT); reduced motion and bounded cascade.
import { LazyMotion, domAnimation, useReducedMotion } from 'motion/react'
import * as m from 'motion/react-m'

export function BlurRevealText({ text, className }: { text: string; className?: string }) {
  const reducedMotion = useReducedMotion()
  const words = text.split(' ')
  if (reducedMotion) return <span className={className}>{text}</span>
  return <LazyMotion features={domAnimation} strict><span className={className}>
    <span className="sr-only">{text}</span>
    {words.map((word, index) => <m.span key={`${word}-${index}`} aria-hidden="true" className="inline-block"
      initial={{ opacity: 0, y: 8, filter: 'blur(4px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      transition={{ duration: 0.35, delay: Math.min(index * 0.04, 0.24), ease: [0.22, 1, 0.36, 1] }}>
      {word}{index < words.length - 1 ? '\u00a0' : ''}
    </m.span>)}
  </span></LazyMotion>
}
