'use client'
import { useState } from 'react'
import { Button, Chip, Link, Modal, Tabs, useOverlayState } from '@heroui/react'
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  ChartPie,
  Expand,
  Landmark,
  LayoutDashboard,
  Play,
  Target,
} from 'lucide-react'
import { landingAsset } from '@/lib/asset'
import { APP_LINKS } from '@/lib/links'
export const productScreens = [
  {
    id: 'dashboard',
    title: 'Dashboard',
    icon: LayoutDashboard,
    description:
      'Balances, income, expenses and category activity. Review the month with your accounts in context.',
    alt: 'Original FinCo-Pilot dashboard with two synthetic accounts and sample monthly activity.',
  },
  {
    id: 'accounts',
    title: 'Accounts',
    icon: Landmark,
    description:
      'Everyday and savings accounts, organised by type and currency. These examples are manually managed.',
    alt: 'Original FinCo-Pilot Accounts screen showing synthetic everyday and savings accounts.',
  },
  {
    id: 'budgets',
    title: 'Budgets',
    icon: ChartPie,
    description:
      'Give a category a monthly budget. This specimen sets aside ₹8,000 for groceries.',
    alt: 'Original FinCo-Pilot Budgets screen with a synthetic monthly grocery budget.',
  },
  {
    id: 'goals',
    title: 'Goals',
    icon: Target,
    description:
      'A longer-term purpose for your money. This manual sample goal has ₹60,000 towards a ₹1,00,000 reserve.',
    alt: 'Original FinCo-Pilot Goals screen with a synthetic emergency reserve goal.',
  },
  {
    id: 'recurring',
    title: 'Recurring',
    icon: CalendarDays,
    description:
      'Keep repeating commitments in view. The sample household-supplies entry is manually configured.',
    alt: 'Original FinCo-Pilot Recurring screen with a synthetic monthly household expense.',
  },
  {
    id: 'reports',
    title: 'Reports',
    icon: ChartPie,
    description:
      'Explore a financial picture over time. This net-worth specimen contains synthetic balances and a made-up historical series.',
    alt: 'Original FinCo-Pilot Reports screen with synthetic balances and historical data.',
  },
] as const
function ScreenPicture({
  screen,
  expanded = false,
}: {
  screen: (typeof productScreens)[number]
  expanded?: boolean
}) {
  return (
    <picture>
      <source
        media="(max-width:620px)"
        srcSet={landingAsset('/product/' + screen.id + '-mobile.webp')}
      />
      <img
        src={landingAsset('/product/' + screen.id + '-desktop.webp')}
        width={1440}
        height={920}
        loading={expanded ? 'eager' : 'lazy'}
        decoding="async"
        alt={screen.alt}
      />
    </picture>
  )
}
const tourSteps = [
  {
    screen: 1,
    title: '01 / Start with one account',
    body: 'Choose the account type and currency, then enter a balance you can verify. A provider connection is optional.',
  },
  {
    screen: 0,
    title: '02 / Review the records behind it',
    body: 'Add transactions or inspect an import preview. Check dates, categories, signs and duplicates before confirming.',
  },
  {
    screen: 3,
    title: '03 / Give the next step a purpose',
    body: 'Track a goal or review a budget. Confirm debts, upcoming obligations and reserves before using the spending-plan tool.',
  },
]
export function ProductScreens() {
  const [selected, setSelected] = useState('dashboard')
  const tour = useOverlayState()
  const zoom = useOverlayState()
  const [step, setStep] = useState(0)
  const current =
    productScreens.find((screen) => screen.id === selected) ?? productScreens[0]
  return (
    <section
      className="section shell"
      id="experience"
      aria-labelledby="product-title"
    >
      <div className="section-head">
        <div>
          <p className="section-kicker">THE ACTUAL WORKSPACE</p>
          <h2 id="product-title">
            Less imagining.
            <br />
            <span>More seeing for yourself.</span>
          </h2>
        </div>
        <div>
          <p className="product-intro">
            Six views from the application. Real screens, filled with synthetic
            sample records.
          </p>
          <Modal state={tour}>
            <Button
              variant="secondary"
              className="tour-trigger"
              onPress={() => setStep(0)}
            >
              <Play size={15} aria-hidden="true" />
              Take the 3-step tour
            </Button>
            <Modal.Backdrop>
              <Modal.Container size="lg">
                <Modal.Dialog className="guided-tour">
                  <Modal.CloseTrigger aria-label="Close product tour" />
                  <Modal.Header>
                    <Chip size="sm" variant="soft">
                      A FIRST LOOK
                    </Chip>
                    <Modal.Heading>{tourSteps[step].title}</Modal.Heading>
                  </Modal.Header>
                  <Modal.Body
                    tabIndex={0}
                    role="region"
                    aria-label="Tour step details"
                  >
                    <p>{tourSteps[step].body}</p>
                    <div className="tour-picture">
                      <ScreenPicture
                        screen={productScreens[tourSteps[step].screen]}
                        expanded
                      />
                    </div>
                    <p className="capture-note">
                      Actual application · Synthetic records · No live account
                    </p>
                  </Modal.Body>
                  <Modal.Footer>
                    <span aria-live="polite">{step + 1} of 3</span>
                    <Button
                      variant="secondary"
                      isDisabled={step === 0}
                      onPress={() => setStep((value) => value - 1)}
                      aria-label="Previous tour step"
                    >
                      <ArrowLeft size={16} aria-hidden="true" />
                      Back
                    </Button>
                    {step < 2 ? (
                      <Button
                        onPress={() => setStep((value) => value + 1)}
                        aria-label="Next tour step"
                      >
                        Next
                        <ArrowRight size={16} aria-hidden="true" />
                      </Button>
                    ) : (
                      <Link
                        href={APP_LINKS.register}
                        className="button button--primary"
                      >
                        Start your workspace
                        <ArrowRight size={16} aria-hidden="true" />
                      </Link>
                    )}
                  </Modal.Footer>
                </Modal.Dialog>
              </Modal.Container>
            </Modal.Backdrop>
          </Modal>
        </div>
      </div>
      <div className="product-tabs">
        <Tabs
          selectedKey={selected}
          onSelectionChange={(key) => setSelected(String(key))}
          className="screen-tabs"
        >
          <div className="product-toolbar">
            <Tabs.ListContainer>
              <Tabs.List aria-label="Explore FinCo-Pilot screens">
                {productScreens.map(({ icon: Icon, ...screen }) => (
                  <Tabs.Tab id={screen.id} key={screen.id}>
                    <Icon aria-hidden="true" />
                    {screen.title}
                    <Tabs.Indicator />
                  </Tabs.Tab>
                ))}
              </Tabs.List>
            </Tabs.ListContainer>
          </div>
          {productScreens.map((screen) => (
            <Tabs.Panel id={screen.id} key={screen.id}>
              <div className="product-window">
                <div className="window-chrome">
                  <span className="window-dots" aria-hidden="true">
                    <i />
                    <i />
                    <i />
                  </span>
                  <span>FinCo-Pilot / {screen.title}</span>
                  <Chip size="sm" variant="soft">
                    Sample data
                  </Chip>
                </div>
                <div className="product-capture">
                  <ScreenPicture screen={screen} />
                </div>
              </div>
              <div className="product-caption">
                <p>{screen.description}</p>
                <p className="capture-note">
                  Actual application screens · Synthetic sample data ·
                  Screenshots, not live accounts
                </p>
              </div>
            </Tabs.Panel>
          ))}
        </Tabs>
        <Modal state={zoom}>
          <Button variant="tertiary" size="sm" className="expand-screen">
            <Expand size={15} aria-hidden="true" />
            Expand {current.title} screen
          </Button>
          <Modal.Backdrop>
            <Modal.Container size="full" scroll="outside">
              <Modal.Dialog className="screen-lightbox">
                <Modal.CloseTrigger aria-label="Close expanded screen" />
                <Modal.Header>
                  <Modal.Heading>
                    {current.title} — actual application
                  </Modal.Heading>
                  <p>
                    Synthetic sample records. Screenshot, not a live account.
                  </p>
                </Modal.Header>
                <Modal.Body>
                  <ScreenPicture screen={current} expanded />
                </Modal.Body>
              </Modal.Dialog>
            </Modal.Container>
          </Modal.Backdrop>
        </Modal>
      </div>
    </section>
  )
}
