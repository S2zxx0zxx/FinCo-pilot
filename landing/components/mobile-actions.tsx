'use client'
import { useEffect, useRef, useState } from 'react'
import { Link } from '@heroui/react'
import { ArrowRight } from 'lucide-react'
import { APP_LINKS } from '@/lib/links'
export function MobileActions() {
  const [visible, setVisible] = useState(false)
  const inHero = useRef(true),
    atEnd = useRef(false),
    editing = useRef(false)
  useEffect(() => {
    const hero = document.querySelector('.hero-section'),
      end = document.querySelector('.final-section')
    const update = () =>
      setVisible(!inHero.current && !atEnd.current && !editing.current)
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.target === hero) inHero.current = entry.isIntersecting
        if (entry.target === end)
          atEnd.current =
            entry.isIntersecting || entry.boundingClientRect.top < 0
      }
      update()
    })
    if (hero) observer.observe(hero)
    if (end) observer.observe(end)
    const focus = (event: FocusEvent) => {
      editing.current =
        event.type === 'focusin' && event.target instanceof HTMLInputElement
      update()
    }
    document.addEventListener('focusin', focus)
    document.addEventListener('focusout', focus)
    return () => {
      observer.disconnect()
      document.removeEventListener('focusin', focus)
      document.removeEventListener('focusout', focus)
    }
  }, [])
  return visible ? (
    <nav className="mobile-action-bar" aria-label="Quick actions">
      <Link href="#perspective" className="button button--secondary">
        Try the example
      </Link>
      <Link href={APP_LINKS.register} className="button button--primary">
        Get started
        <ArrowRight size={16} aria-hidden="true" />
      </Link>
    </nav>
  ) : null
}
