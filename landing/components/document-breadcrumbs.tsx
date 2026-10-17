'use client'

import { Breadcrumbs } from '@heroui/react'
import { landingAsset } from '@/lib/asset'

/** Supporting pages have a real hierarchy; homepage sections do not. */
export function DocumentBreadcrumbs({ title }: { title: string }) {
  return (
    <nav aria-label="Breadcrumb">
      <Breadcrumbs className="document-breadcrumb">
        <Breadcrumbs.Item href={landingAsset('/')}>Home</Breadcrumbs.Item>
        <Breadcrumbs.Item>{title}</Breadcrumbs.Item>
      </Breadcrumbs>
    </nav>
  )
}
