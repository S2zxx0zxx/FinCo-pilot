import { UsageCard } from '@/components/spaceui/usage-card'
import { useQueryClient } from '@tanstack/react-query'
import { CheckoutStatusCard } from '@/billing/checkout-status-card'
import { RenewalEnrollmentCard } from "@/billing/renewal-enrollment-card"
import { RefundOperatorCard } from "@/billing/refund-operator-card"
import { RefundsCard } from "@/billing/refunds-card"
import { CancellationCard } from "@/billing/cancellation-card"
import { ensureRazorpaySdk } from '@/lib/razorpay-sdk'
import { validCheckoutOrder } from '@/billing/checkout-order'
import { useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuth } from '@/contexts/auth-context'
import { useBilling } from '@/contexts/billing-context'
import { buildSupportUrl, rememberRequestId } from '@/lib/support'
import { FounderOfferCard } from '@/billing/founder-offer-card'
import type { CheckoutOrder, PlanId } from '@/billing/types'
import type {
  RazorpayCheckoutOptions,
  RazorpaySuccessResponse,
} from '@/types/razorpay'

import { PricingExperience } from '@/components/spaceui/pricing-experience'
export default function PricingPage() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const { user, token } = useAuth()
  const queryClient = useQueryClient()
  const refreshCheckoutStatus = () => queryClient.invalidateQueries({ queryKey: ['billing', 'checkout-status', user?.id] })
  const {
    catalog,
    founderCampaign,
    refreshFounderCampaign,
    plan: currentPlan,
    isLoading: billingLoading,
  } = useBilling()
  const requestedPlan = params.get('plan')
  const explicitPlan = requestedPlan === 'free' || requestedPlan === 'pro' || requestedPlan === 'max'
    ? requestedPlan as PlanId
    : null
  const selectedPlan: PlanId = explicitPlan ?? (user && !billingLoading ? currentPlan : 'pro')
  const interval = params.get('interval') === 'annual' ? 'annual' : 'monthly'
  const setInterval = (next: 'monthly' | 'annual') => {
    const nextParams = new URLSearchParams(params)
    nextParams.set('interval', next)
    setParams(nextParams, { replace: true })
  }

  const selectPlan = (next: PlanId) => {
    const nextParams = new URLSearchParams(params)
    nextParams.set('plan', next)
    setParams(nextParams, { replace: true })
  }

  const checkoutStarting = useRef(false)
  const checkoutOpen = useRef(false)
  const continueWithPlan = async (plan: PlanId) => {
    if (checkoutStarting.current || checkoutOpen.current) return
    checkoutStarting.current = true
    try { await startCheckout(plan) } finally { checkoutStarting.current = false }
  }

  const startCheckout = async (plan: PlanId) => {
    if (user && currentPlan === plan) return
    selectPlan(plan)

    if (!user || !token) {
      navigate(plan === 'free' ? '/register' : '/login?next=' + encodeURIComponent('/pricing?plan=' + plan + '&interval=' + (plan === 'pro' ? interval : 'monthly')))
      return
    }

    if (plan === 'free') return

    try {
      await ensureRazorpaySdk()
    } catch {
      toast.error('Payment SDK failed to load. Please try again.')
      return
    }
    if (!window.Razorpay) {
      toast.error('Payment SDK failed to load. Please refresh the page and try again.')
      return
    }

    const effectiveInterval = plan === 'max' ? 'monthly' : interval
    const authHeaders = {
      'Content-Type': 'application/json',
      Authorization: 'Bearer ' + token,
    }

    try {
      const orderRes = await fetch('/api/checkout/create-order', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ plan, interval: effectiveInterval }),
      })

      if (!orderRes.ok) {
        const errData = await orderRes.json().catch(() => ({}))
        const detail = (errData as { detail?: string }).detail ?? 'Could not start checkout.'
        toast.error(detail)
        return
      }

      const orderData = await orderRes.json() as CheckoutOrder
      if (!validCheckoutOrder(orderData, plan, effectiveInterval)) {
        toast.error('The payment order could not be validated. No payment was opened.')
        return
      }

      let paymentReceived = false
      let verificationStarted = false
      const cancelQuote = async () => {
        if (paymentReceived) return
        try {
          const result = await fetch('/api/checkout/cancel-reservation', {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify({ reservation_id: orderData.reservation_id }),
          })
          if (result.ok) {
            await refreshFounderCampaign()
            toast.info('Checkout closed. Your temporary quote was released.')
          } else {
            toast.info('Checkout closed. The provider order remains pending reconciliation; no new payment was started.')
          }
        } catch {
          toast.info('Checkout closed. Quote release could not be confirmed.')
          // Provider outcomes stay durable; a dismissed modal cannot prove non-payment.
        }
      }

      const offerDescription = orderData.founder_wave != null
        ? 'Founder Wave ' + orderData.founder_wave + ' · ' + orderData.service_period_days + ' days Pro'
        : plan.toUpperCase() + ' · ' + orderData.service_period_days + '-day first period'

      const options: RazorpayCheckoutOptions = {
        key: orderData.key_id,
        amount: orderData.amount,
        currency: orderData.currency,
        name: 'FinCo-Pilot',
        description: offerDescription,
        order_id: orderData.order_id,
        handler: async (response: RazorpaySuccessResponse) => {
          paymentReceived = true
          if (verificationStarted) return
          verificationStarted = true
          checkoutOpen.current = true
          try {
            const verifyRes = await fetch('/api/checkout/verify-payment', {
              method: 'POST',
              headers: authHeaders,
              body: JSON.stringify({
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_signature: response.razorpay_signature,
              }),
            })
            const requestReference = rememberRequestId(verifyRes.headers)
            if (verifyRes.ok) {
              await refreshFounderCampaign()
              toast.success('Payment captured and verified. Activation is pending the secure subscription lifecycle.')
            } else {
              const body = await verifyRes.json().catch(() => ({}))
              const detail = (body as { detail?: string }).detail
              toast.error(detail ?? 'Payment verification failed. Please contact support.', {
                action: {
                  label: 'Contact support',
                  onClick: () => navigate(buildSupportUrl({
                    from: '/pricing',
                    category: 'billing_payment',
                    reference: requestReference,
                  })),
                },
              })
            }
          } catch {
            toast.error('Payment confirmation is unresolved. Do not pay again; check payment status or contact support.', {
              action: {
                label: 'Contact support',
                onClick: () => navigate(buildSupportUrl({
                  from: '/pricing',
                  category: 'billing_payment',
                })),
              },
            })
          } finally {
            checkoutOpen.current = false
            void refreshCheckoutStatus()
          }
        },
        modal: {
          ondismiss: () => {
            if (paymentReceived) return
            checkoutOpen.current = false
            void cancelQuote()
            void refreshCheckoutStatus()
          },
        },
        // Orders bind payment attempts to the server-owned purchase.
        // Keep in-modal retries disabled. Failed or ambiguous attempts
        // retain their original Order; fresh status checks do not collect money.
        retry: { enabled: false },
        theme: { color: '#000000' },
      }

      const rzp = new window.Razorpay(options)
      rzp.on('payment.failed', () => {
        if (paymentReceived) return
        void refreshCheckoutStatus()
        toast.error('Payment was not confirmed. If debited, do not pay again. Check payment status or contact support.', {
          action: {
            label: 'Contact support',
            onClick: () => navigate(buildSupportUrl({
              from: '/pricing',
              category: 'billing_payment',
            })),
          },
        })
      })
      checkoutOpen.current = true
      rzp.open()
    } catch {
      checkoutOpen.current = false
      void refreshCheckoutStatus()
      toast.error('Checkout could not be confirmed. Check payment status before paying again.')
    }
  }

  return <PricingExperience catalog={catalog} selectedPlan={selectedPlan} interval={interval}
    currentPlan={currentPlan} signedIn={Boolean(user)} billingLoading={billingLoading}
    onPlanChange={selectPlan} onIntervalChange={setInterval} onContinue={() => void continueWithPlan(selectedPlan)}
    founderOffer={selectedPlan === 'pro' && interval === 'monthly' ? <FounderOfferCard campaign={founderCampaign} /> : null}
    management={user ? <><UsageCard /><RenewalEnrollmentCard /><CancellationCard /><RefundsCard /><CheckoutStatusCard /><RefundOperatorCard /></> : null} />
}
