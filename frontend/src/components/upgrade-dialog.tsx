import { LockKeyhole, ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { PlanBadge } from '@/components/plan-badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { UpgradeIntent } from '@/billing/types'

export function UpgradeDialog({
  intent,
  onOpenChange,
}: {
  intent: UpgradeIntent | null
  onOpenChange: (open: boolean) => void
}) {
  const navigate = useNavigate()
  const plan = intent?.plan ?? 'pro'
  return (
    <Dialog open={Boolean(intent)} onOpenChange={onOpenChange}>
      <DialogContent className="overflow-hidden border-border/70 bg-background/95 p-0 shadow-2xl backdrop-blur-xl sm:max-w-md">
        <div className="relative px-6 pb-6 pt-7">
          <div className="pointer-events-none absolute inset-x-8 top-0 h-24 rounded-full bg-foreground/[0.05] blur-3xl" />
          <DialogHeader className="relative text-left">
            <div className="mb-3 flex items-center gap-2">
              <span className="grid size-9 place-items-center rounded-2xl border bg-muted/60 shadow-inner">
                <LockKeyhole className="size-4" />
              </span>
              <PlanBadge plan={plan} />
            </div>
            <DialogTitle className="text-xl tracking-tight">
              {plan === 'max' ? 'Unlock FinCo Max' : 'Unlock FinCo Pro'}
            </DialogTitle>
            <DialogDescription className="leading-relaxed">
              {intent?.reason ?? 'This feature is part of a paid FinCo plan.'}
            </DialogDescription>
          </DialogHeader>

          <div className="relative mt-5 flex items-start gap-3 rounded-2xl border bg-muted/35 p-3.5 text-sm text-muted-foreground">
            <ShieldCheck className="mt-0.5 size-4 shrink-0 text-foreground" />
            <p>Plan access is verified by the server. Changing browser state, URLs or local storage cannot unlock paid actions.</p>
          </div>
        </div>
        <DialogFooter className="border-t bg-muted/20 p-4 sm:justify-stretch">
          <Button
            className="h-11 w-full rounded-xl"
            onClick={() => {
              onOpenChange(false)
              navigate(`/pricing?plan=${plan}`)
            }}
          >
            View {plan === 'max' ? 'Max' : 'Pro'} plan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
