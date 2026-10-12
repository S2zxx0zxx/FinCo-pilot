// frontend/src/components/page-header.tsx
interface PageHeaderProps {
  section: string
  title: string
  action?: React.ReactNode
}

export function PageHeader({ section, title, action }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between finco-page-header">
      <div>
        <p className="text-[13px] font-medium text-muted-foreground mb-2">
          {section}
        </p>
        <h1 className="finco-page-title font-semibold text-foreground tracking-tight">{title}</h1>
      </div>
      {action}
    </div>
  )
}
