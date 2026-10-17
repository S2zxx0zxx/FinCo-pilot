'use client'
import { useState } from 'react'
import {
  Card,
  Chip,
  Link,
  ToggleButton,
  ToggleButtonGroup,
} from '@heroui/react'
import { ArrowRight, Check } from 'lucide-react'
import catalog from '@/lib/standard-plans.json'
import { APP_LINKS } from '@/lib/links'
import { formatMoney } from '@/lib/spending-example'
const plans = [
  {
    id: 'free',
    title: 'Free',
    intro: 'Find your starting point.',
    items: [
      'Core personal finance workspace',
      'Explore accounts and your records',
      'Usage limits apply',
    ],
  },
  {
    id: 'pro',
    title: 'Pro',
    intro: 'Build a more detailed picture.',
    items: [
      'Advanced reports',
      'Rules and smart reconciliation',
      'Higher usage allowances',
    ],
  },
  {
    id: 'max',
    title: 'Max',
    intro: 'Room for more complex workflows.',
    items: [
      'Business workspace capabilities',
      'Invoices',
      'Agent and automation capabilities, when configured',
    ],
  },
] as const
export function PlanPreview() {
  const [interval, setInterval] = useState('monthly')
  return (
    <section
      className="section shell plans-section"
      id="plans"
      aria-labelledby="plans-title"
    >
      <div className="section-head">
        <div>
          <p className="section-kicker">ROOM TO START. ROOM TO GROW.</p>
          <h2 id="plans-title">
            Choose your
            <br />
            <span>next step.</span>
          </h2>
        </div>
        <div>
          <p className="plans-description">
            A preview of the standard catalog. Review live availability, limits,
            tax treatment and checkout terms on the pricing page.
          </p>
          <ToggleButtonGroup
            aria-label="Plan billing interval"
            selectionMode="single"
            selectedKeys={[interval]}
            disallowEmptySelection
            onSelectionChange={(keys) => {
              const value = keys.values().next().value
              if (typeof value === 'string') setInterval(value)
            }}
            className="plan-interval"
          >
            <ToggleButton id="monthly">Monthly</ToggleButton>
            <ToggleButton id="annual">Annual</ToggleButton>
          </ToggleButtonGroup>
        </div>
      </div>
      <div className="plan-grid">
        {plans.map((plan) => {
          const option = catalog.prices.find(
            (price) =>
              price.plan === plan.id &&
              price.interval === (plan.id === 'free' ? 'none' : interval),
          )
          return (
            <Card key={plan.id} className={'plan-card plan-' + plan.id}>
              <Card.Header>
                <div className="plan-title">
                  <Card.Title>{plan.title}</Card.Title>
                  {plan.id === 'pro' && (
                    <Chip size="sm" variant="soft">
                      Reports + rules
                    </Chip>
                  )}
                </div>
                <Card.Description>{plan.intro}</Card.Description>
              </Card.Header>
              <Card.Content>
                <div className="plan-price">
                  {option ? (
                    <>
                      <strong>{formatMoney(option.amount_minor / 100)}</strong>
                      <span>
                        {plan.id === 'free'
                          ? 'standard free plan'
                          : interval === 'annual'
                            ? '/ year'
                            : '/ month'}
                      </span>
                    </>
                  ) : (
                    <>
                      <strong className="plan-no-annual">
                        Monthly billing
                      </strong>
                      <span>No standard annual option</span>
                    </>
                  )}
                </div>
                <ul>
                  {plan.items.map((item) => (
                    <li key={item}>
                      <Check size={16} aria-hidden="true" />
                      {item}
                    </li>
                  ))}
                </ul>
              </Card.Content>
              <Card.Footer>
                <Link
                  className={
                    'button ' +
                    (plan.id === 'pro'
                      ? 'button--primary'
                      : 'button--secondary')
                  }
                  href={APP_LINKS.pricing}
                >
                  Review {plan.title} details
                  <ArrowRight size={16} aria-hidden="true" />
                </Link>
              </Card.Footer>
            </Card>
          )
        })}
      </div>
      <p className="pricing-footnote">
        Standard catalog preview · Plan features depend on permissions and
        configuration · Promotional offers and checkout availability are shown
        in the application.
      </p>
    </section>
  )
}
