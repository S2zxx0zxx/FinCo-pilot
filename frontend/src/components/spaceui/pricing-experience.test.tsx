import { expect, it, vi } from 'vitest'
import { screen, within } from '@testing-library/react'
import { useState } from 'react'
import { renderWithProviders } from '@/test/utils'
import { FALLBACK_PRICING } from '@/billing/catalog'
import type { PlanId, PricingCatalog } from '@/billing/types'
import { PricingExperience } from './pricing-experience'
function setup({signedIn=false,currentPlan='free' as PlanId,catalog=FALLBACK_PRICING}={}) {
  const next=vi.fn()
  function Harness() {
    const [plan,setPlan]=useState<PlanId>('pro'),[interval,setInterval]=useState<'monthly'|'annual'>('monthly')
    return <PricingExperience catalog={catalog} selectedPlan={plan} interval={interval} currentPlan={currentPlan} signedIn={signedIn} billingLoading={false} onPlanChange={setPlan} onIntervalChange={setInterval} onContinue={next} founderOffer={null} management={<p>Management fixture</p>}/>
  }
  return {...renderWithProviders(<Harness/>),next}
}
it('annual updates Pro but Max stays monthly, and selecting never charges',async()=>{
  const {user,next}=setup()
  await user.click(screen.getByRole('radio',{name:'Annual'}))
  expect(within(screen.getByRole('region',{name:'Selected plan'})).getByText('₹999')).toBeInTheDocument()
  await user.click(screen.getAllByRole('button',{name:'Select Max'})[0])
  const summary=within(screen.getByRole('region',{name:'Selected plan'}))
  expect(summary.getByText('₹349')).toBeInTheDocument();expect(summary.getByText('/ month')).toBeInTheDocument()
  expect(next).not.toHaveBeenCalled()
  await user.click(summary.getByRole('button',{name:'Sign in for Max'}));expect(next).toHaveBeenCalledOnce()
})
it.each([{prices:[]},{prices:[{plan:'pro',interval:'monthly',amount_minor:-1,currency:'INR'}]},{prices:[{plan:'pro',interval:'monthly',amount_minor:9900,currency:'USD'}]}])('blocks unavailable or malformed prices instead of displaying zero',({prices})=>{
  setup({catalog:{...FALLBACK_PRICING,prices} as PricingCatalog})
  const summary=within(screen.getByRole('region',{name:'Selected plan'}))
  expect(summary.getByText('Unavailable')).toBeInTheDocument();expect(summary.getByRole('button',{name:'Sign in for Pro'})).toBeDisabled()
})
it('routes existing paid customers selecting Free to real subscription management',async()=>{
  const {user,next}=setup({signedIn:true,currentPlan:'max'})
  await user.click(screen.getAllByRole('button',{name:'Select Free'})[0])
  expect(screen.getByRole('link',{name:'Manage subscription'})).toHaveAttribute('href','#billing-management')
  expect(screen.getByRole('heading',{name:'Your subscription, in your control.'})).toBeInTheDocument()
  expect(next).not.toHaveBeenCalled()
})
it('discloses the payment boundary and conditional AI availability',async()=>{
  const {user}=setup()
  await user.click(screen.getByRole('button',{name:'Does selecting a plan charge me?'}))
  expect(screen.getByText(/No\. Selecting a plan only updates/)).toBeVisible()
  await user.click(screen.getByRole('button',{name:'Does Max include AI automation?'}))
  expect(screen.getByText(/allowance of 300 AI actions/)).toBeVisible()
})
