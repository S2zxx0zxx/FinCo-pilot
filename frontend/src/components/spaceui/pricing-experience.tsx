import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowUpRight, Check, Lock } from 'lucide-react'
import { FinCoLogo } from '@/components/finco-logo'
import { Button } from '@/components/ui/button'
import { IdentityAvatar } from './identity-avatar'
import { Card } from './pricing-card'
import { Badge } from './pricing-badge'
import { Radio, RadioGroup } from './pricing-radio-group'
import { Tabs, TabsList, TabsTab, TabsPanel } from './pricing-tabs'
import { Accordion, AccordionItem, AccordionTrigger, AccordionPanel } from './pricing-accordion'
import { Separator } from './pricing-separator'
import { FEATURES, PLAN_COPY, PLAN_LIMITS, planAllows } from '@/billing/pricing-presentation'
import { formatInrMinor, priceFor } from '@/billing/catalog'
import type { PlanId, PricingCatalog } from '@/billing/types'
import './pricing-experience.css'

type Interval = 'monthly' | 'annual'
type Props = {
  catalog: PricingCatalog; selectedPlan: PlanId; interval: Interval; currentPlan: PlanId
  signedIn: boolean; billingLoading: boolean; onPlanChange: (plan: PlanId) => void
  onIntervalChange: (interval: Interval) => void; onContinue: () => void
  founderOffer: ReactNode; management: ReactNode
}
const plans = ['free', 'pro', 'max'] as const
const questions = [
  ['What happens if I return to Free?', 'Your existing financial history stays readable. Free limits apply to new work. Use subscription management below to review renewal and cancellation options.'],
  ['How does annual billing work?', 'Pro annual is charged once per year, upfront. Max is available monthly only. Your chosen Pro billing period is preserved when you sign in.'],
  ['How do founder offers work?', 'When a campaign is live, its current availability appears separately below. Eligibility, capacity and your exact quote are confirmed before payment. Standard plan prices above are not a promise of founder eligibility.'],
  ['Does selecting a plan charge me?', 'No. Selecting a plan only updates your choice. Continue to review the payment checkout. The server confirms the exact eligible offer and applicable tax treatment before any payment.'],
  ['Are cancellation and refunds the same?', 'No. Stopping renewal and requesting a refund are separate actions. Signed-in customers can review their subscription, cancellation and refund status below.'],
  ['Does Max include AI automation?', 'Max has an allowance of 300 AI actions per month. Agents and MCP automation also require the deployment capability to be enabled. A plan alone does not enable an unavailable service.'],
] as const
function option(catalog: PricingCatalog, plan: PlanId, interval: Interval) {
  const value = priceFor(catalog, plan, plan === 'free' ? 'none' : plan === 'max' ? 'monthly' : interval)
  return value && Number.isSafeInteger(value.amount_minor) && value.amount_minor >= 0 && value.currency === 'INR' ? value : undefined
}
function Price({ catalog, plan, interval }: Pick<Props, 'catalog' | 'interval'> & { plan: PlanId }) {
  const value = option(catalog, plan, interval)
  return <div className="pricing-price"><strong>{value ? formatInrMinor(value.amount_minor) : 'Unavailable'}</strong><span>{plan === 'free' ? 'forever' : plan === 'pro' && interval === 'annual' ? '/ year · billed annually' : '/ month'}</span></div>
}
function PlanCard({ plan, scope, ...props }: Props & { plan: PlanId; scope: string }) {
  const selected = props.selectedPlan === plan
  return <Card render={<article />} aria-labelledby={`${scope}-${plan}`} className={`pricing-plan ${plan === 'pro' ? 'pricing-pro' : ''}`} data-selected={selected}>
    <div className="pricing-plan-heading"><span className="pricing-eyebrow">{PLAN_COPY[plan].eyebrow}</span>{props.signedIn && props.currentPlan === plan ? <Badge variant="outline">Current plan</Badge> : null}</div>
    <h2 id={`${scope}-${plan}`}>{PLAN_COPY[plan].title}</h2>
    <Price catalog={props.catalog} plan={plan} interval={props.interval} />
    <p className="pricing-plan-description">{PLAN_COPY[plan].description}</p>
    <Button variant="outline" className="pricing-select" aria-pressed={selected} onClick={() => props.onPlanChange(plan)}>{selected ? `Selected: ${PLAN_COPY[plan].title}` : `Select ${PLAN_COPY[plan].title}`}<ArrowUpRight aria-hidden="true" size={16} /></Button>
    <Separator />
    <ul className="pricing-features">{FEATURES.map(feature => {
      const allowed = planAllows(plan, feature.minPlan)
      return <li key={feature.label}>{allowed ? <Check size={17} aria-hidden="true" /> : <Lock size={16} aria-hidden="true" />}<span>{feature.label}{!allowed ? <small>Available on {feature.minPlan === 'pro' ? 'Pro and Max' : 'Max'}</small> : null}</span></li>
    })}</ul>
    <p className="pricing-fine">{plan === 'max' ? 'Max is monthly only. AI automation requires an enabled deployment.' : plan === 'pro' && props.interval === 'annual' ? 'One upfront payment. No monthly instalments.' : plan === 'free' ? 'No card required. No ads.' : 'Standard monthly price. Eligible offers are shown separately.'}</p>
  </Card>
}
export function PricingExperience(props: Props) {
  const { catalog, selectedPlan, interval, currentPlan, signedIn, billingLoading } = props
  const current = signedIn && currentPlan === selectedPlan
  const manage = signedIn && currentPlan !== 'free' && selectedPlan === 'free'
  const selectedPrice = option(catalog, selectedPlan, interval)
  const monthly = option(catalog, 'pro', 'monthly'), annual = option(catalog, 'pro', 'annual')
  const savings = monthly && annual ? monthly.amount_minor * 12 - annual.amount_minor : 0
  const tax = catalog.tax_display_mode === 'inclusive' ? 'Prices include applicable taxes.' : catalog.tax_display_mode === 'exclusive' ? 'Applicable taxes may be added at checkout.' : 'Tax details are currently unavailable. Paid checkout requires billing setup.'
  const cta = current ? 'Current plan' : !signedIn ? selectedPlan === 'free' ? 'Start free' : `Sign in for ${PLAN_COPY[selectedPlan].title}` : `Continue with ${PLAN_COPY[selectedPlan].title}`
  return <main className="finco-pricing"><div className="pricing-container">
    <header className="pricing-header"><Button variant="outline" size="icon" asChild><Link to="/" aria-label="Home"><ArrowLeft size={18} /></Link></Button><Link to="/" className="pricing-brand"><FinCoLogo size={24} />FinCo-Pilot</Link><Link to="/support">Get help <ArrowUpRight size={15} aria-hidden="true" /></Link></header>
    <section className="pricing-hero"><Badge variant="outline">YOUR MONEY. YOUR PACE.</Badge><h1>A plan for where you are.<br /><span>And what’s next.</span></h1><p>Build your money habit for free. Add deeper analysis or a business workspace when you need it.</p><div className="pricing-billing"><span id="pricing-period">Pro billing period</span><RadioGroup aria-labelledby="pricing-period" value={interval} onValueChange={value => props.onIntervalChange(value as Interval)} className="pricing-radio-group">{(['monthly','annual'] as const).map(value => <label key={value}><Radio value={value} />{value === 'monthly' ? 'Monthly' : 'Annual'}</label>)}</RadioGroup>{savings > 0 ? <span className="pricing-savings">Pro saves {formatInrMinor(savings)} / year</span> : null}</div><p className="pricing-fine">Annual billing applies to Pro. Max stays monthly.</p></section>
    <section aria-label="Choose a plan" className="pricing-desktop-plans">{plans.map(plan => <PlanCard key={plan} plan={plan} scope="desktop-plan" {...props} />)}</section>
    <Tabs className="pricing-mobile-plans" value={selectedPlan} onValueChange={value => props.onPlanChange(value as PlanId)}><TabsList aria-label="Plans" activateOnFocus>{plans.map(plan => <TabsTab key={plan} value={plan}>{PLAN_COPY[plan].title}</TabsTab>)}</TabsList>{plans.map(plan => <TabsPanel key={plan} value={plan}><PlanCard plan={plan} scope="mobile-plan" {...props} /></TabsPanel>)}</Tabs>
    <Card render={<section />} aria-label="Selected plan" className="pricing-summary"><div><p className="pricing-eyebrow">Your choice · {PLAN_COPY[selectedPlan].title}</p><Price catalog={catalog} plan={selectedPlan} interval={interval} /><p className="pricing-fine">{tax} Selecting a plan does not charge you.</p></div><div className="pricing-summary-action">{manage ? <Button asChild><a href="#billing-management">Manage subscription</a></Button> : <Button disabled={current || billingLoading || !selectedPrice} onClick={props.onContinue}>{billingLoading ? 'Loading your plan…' : cta}<ArrowUpRight size={17} aria-hidden="true" /></Button>}<span className="pricing-fine">{current ? 'You are already on this plan.' : manage ? 'Review renewal and cancellation below.' : 'Your exact eligible quote is confirmed before payment.'}</span></div></Card>
    {props.founderOffer}
    <section className="pricing-comparison" aria-labelledby="pricing-compare"><div className="pricing-section-title"><span className="pricing-eyebrow">THE DETAILS, WITHOUT THE GUESSWORK</span><h2 id="pricing-compare">Make room for your next move.</h2><p>Compare the actual plan allowances. Monthly quotas reset on the first day of each calendar month (UTC).</p></div><table className="pricing-desktop-comparison"><caption className="sr-only">Plan limits and capabilities</caption><thead><tr><th scope="col">What’s included</th>{plans.map(plan => <th key={plan} scope="col">{PLAN_COPY[plan].title}</th>)}</tr></thead><tbody>{PLAN_LIMITS.map(([label,...values]) => <tr key={label}><th scope="row">{label}</th>{values.map((value,i) => <td key={i}>{value}</td>)}</tr>)}</tbody></table><div className="pricing-mobile-comparison"><h3>{PLAN_COPY[selectedPlan].title} allowances</h3><dl>{PLAN_LIMITS.map(([label,...values]) => <div key={label}><dt>{label}</dt><dd>{values[plans.indexOf(selectedPlan)]}</dd></div>)}</dl><p className="pricing-fine">Switch the plan tabs above to compare another plan.</p></div><p className="pricing-fine">Personal and business workspaces share the total workspace allowance. *AI actions and Agents / MCP require the deployment capability to be enabled. Storage uses binary units.</p></section>
    <Separator />
    <section className="pricing-faq" aria-labelledby="pricing-faq-title"><div><IdentityAvatar seed="finco-pricing-guide" size={56} /><span className="pricing-eyebrow">A LITTLE CLARITY</span><h2 id="pricing-faq-title">Good questions.<br />Straight answers.</h2><p>Need a hand choosing?<br /><Link to="/support">Talk to support <ArrowUpRight size={15} aria-hidden="true" /></Link></p></div><Accordion>{questions.map(([question,answer],index) => <AccordionItem key={question} value={index}><AccordionTrigger>{question}</AccordionTrigger><AccordionPanel>{answer}</AccordionPanel></AccordionItem>)}</Accordion></section>
    {signedIn ? <section id="billing-management" className="pricing-management" aria-labelledby="pricing-manage-title"><h2 id="pricing-manage-title">Your subscription, in your control.</h2>{props.management}</section> : null}
    <footer className="pricing-footer"><span>FinCo-Pilot · Prices in INR</span><nav aria-label="Pricing legal and help"><Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link><Link to="/support">Support</Link></nav></footer>
  </div></main>
}
