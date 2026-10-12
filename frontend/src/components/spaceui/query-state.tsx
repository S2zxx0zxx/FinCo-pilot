import { useTranslation } from 'react-i18next'
import { AlertCircle } from 'lucide-react'
import { Empty, EmptyHeader, EmptyMedia, EmptyTitle, EmptyDescription, EmptyContent } from '@/components/ui/empty'
import { Button } from '@/components/ui/button'

export function QueryError({ retry }: { retry: () => unknown }) {
  const { t } = useTranslation()
  return <Empty role="alert" className="finco-surface my-4 py-10">
    <EmptyHeader><EmptyMedia variant="icon"><AlertCircle aria-hidden="true" /></EmptyMedia>
      <EmptyTitle>{t('common.error')}</EmptyTitle>
      <EmptyDescription>{t('frontend.loadError')}</EmptyDescription>
    </EmptyHeader>
    <EmptyContent><Button type="button" variant="secondary" onClick={() => void retry()}>{t('frontend.retry')}</Button></EmptyContent>
  </Empty>
}
