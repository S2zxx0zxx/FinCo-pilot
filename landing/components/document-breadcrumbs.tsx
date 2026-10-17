'use client'

import { Breadcrumbs } from '@heroui/react'

/** Supporting pages have a real hierarchy; homepage sections do not. */
export function DocumentBreadcrumbs({ title }: { title: string }) {
  return (
    <Breadcrumbs className="document-breadcrumb" aria-label="Breadcrumb">
      <Breadcrumbs.Item href="/">Home</Breadcrumbs.Item>
      <Breadcrumbs.Item>{title}</Breadcrumbs.Item>
    </Breadcrumbs>
  )
}
