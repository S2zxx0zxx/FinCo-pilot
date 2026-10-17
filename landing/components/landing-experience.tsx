'use client'

import {
  Accordion,
  Disclosure,
  Meter,
  Button,
  Card,
  Chip,
  Drawer,
  Link,
  Separator,
  useOverlayState,
} from '@heroui/react'
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  CalendarDays,
  ChartPie,
  Check,
  Download,
  FileText,
  Landmark,
  LockKeyhole,
  Menu,
  ShieldCheck,
  SlidersHorizontal,
  Wallet,
} from 'lucide-react'
import { InstalledAppHandoff } from '@/components/installed-app-handoff'
import { SpendingPlayground } from '@/components/spending-playground'
import { PlanPreview } from '@/components/plan-preview'
import { MobileActions } from '@/components/mobile-actions'
import { ImportWalkthrough } from '@/components/import-walkthrough'
import { ProductScreens } from '@/components/product-screens'
import { APP_LINKS } from '@/lib/links'
import { landingAsset } from '@/lib/asset'

const nav = [
  { title: 'Why FinCo', href: '#why-finco' },
  { title: 'The product', href: '#experience' },
  { title: 'How it works', href: '#how-it-works' },
  { title: 'Questions', href: '#questions' },
]
const features = [
  {
    icon: <Landmark aria-hidden="true" />,
    title: 'Accounts, together.',
    body: 'Organise cash, bank and card accounts by type and currency. Start manually; a bank connection is optional.',
    detail: 'A home for each balance',
  },
  {
    icon: <FileText aria-hidden="true" />,
    title: 'Every transaction, in context.',
    body: 'Review income and expenses with categories, payees and account context. Find the details behind a monthly total.',
    detail: 'From records to a useful picture',
  },
  {
    icon: <ChartPie aria-hidden="true" />,
    title: 'A plan for the month.',
    body: 'Use budgets to organise spending and goals to track what you are saving towards. Review progress as your records change.',
    detail: 'Budgets + goals',
  },
  {
    icon: <CalendarDays aria-hidden="true" />,
    title: 'Remember what repeats.',
    body: 'Manage recurring transactions and loan or EMI plans. Include upcoming outflows when reviewing a spending estimate.',
    detail: 'Today, with tomorrow in view',
  },
  {
    icon: <Download aria-hidden="true" />,
    title: 'Bring your records with you.',
    body: 'Preview transaction files, choose the destination and check mappings before confirming. CSV, QIF, OFX/QFX and CAMT are supported formats.',
    detail: 'Review before you import',
  },
  {
    icon: <SlidersHorizontal aria-hidden="true" />,
    title: 'Go deeper when you need to.',
    body: 'Explore reports, assets and invoices alongside your everyday finances. Optional AI and bank providers depend on your setup and plan.',
    detail: 'Your workflow, at your pace',
  },
]
const faqs = [
  [
    'What is FinCo-Pilot?',
    'FinCo-Pilot is a personal finance workspace for accounts, transactions, budgets, goals and reports. It also includes recurring transactions, loan plans and spending estimates. Available modules depend on your settings and plan.',
  ],
  [
    'Do I have to connect a bank account?',
    'No. FinCo-Pilot supports managing financial accounts and transactions manually. File imports and provider connections are separate capabilities. Bank availability depends on the active provider and deployment.',
  ],
  [
    'How does safe-to-spend work?',
    'The spending plan uses confirmed balances, card debt, upcoming outflows, loan installments and the reserves you enter. You review your obligations before calculating. Missing inputs can block an estimate; incomplete records can make a result unreliable.',
  ],
  [
    'Can I bring in my existing transactions?',
    'The importer supports CSV, QIF, OFX/QFX and CAMT. Check the destination account, dates, amount signs, currency and duplicate handling in the preview. Format support does not guarantee every bank export maps correctly. The import guide explains current limitations.',
  ],
  [
    'Will QIF preserve every UPI reference?',
    'Do not assume so. The reviewed QIF parser uses date, amount and payee or memo; extra reference tags are not mapped to an external transaction ID. Read the import guide and check the preview against your source file.',
  ],
  [
    'Can I use FinCo-Pilot on my phone?',
    'The web application includes responsive screens and progressive web app support for supported browsers. You can use it from your phone or desktop; available features may vary.',
  ],
  [
    'Are AI features required?',
    'No. Accounts, transactions and the core financial workspace are independent of optional AI capabilities. Provider configuration, permissions and plan availability determine which optional tools are offered.',
  ],
  [
    'Is the financial preview on this page real?',
    'All numbers in the interactive example are synthetic. The product screenshots were captured from the application with synthetic sample records. Nothing on this page reads a live account or personal financial data.',
  ],
  [
    'Where can I check pricing?',
    'Use the Pricing link to review the plans currently shown in the application. Feature availability, plan limits and sign-up access should be checked there before choosing a plan.',
  ],
  [
    'Is a spending estimate financial advice?',
    'No. It is a planning aid based on your inputs and records, not a guarantee that a purchase is affordable. Check missing accounts, bills, debts and reserves before making a decision.',
  ],
]
function Mark() {
  return (
    <span className="wordmark">
      FinCo-Pilot
      <span className="brand-dot" aria-hidden="true">
        .
      </span>
    </span>
  )
}
function ArrowLink({
  href,
  children,
  light = false,
}: {
  href: string
  children: React.ReactNode
  light?: boolean
}) {
  return (
    <Link
      href={href}
      className={
        'button button--lg button--primary action-link' +
        (light ? ' cta-light' : '')
      }
    >
      {children}
      <ArrowRight size={18} aria-hidden="true" />
    </Link>
  )
}
function Navigation() {
  const menu = useOverlayState()
  return (
    <header className="site-header" id="top">
      <div className="shell nav-inner">
        <Link href="#top" aria-label="FinCo-Pilot, back to top">
          <Mark />
        </Link>
        <nav className="nav-desktop" aria-label="Primary navigation">
          {nav.map((item) => (
            <Link key={item.href} href={item.href}>
              {item.title}
            </Link>
          ))}
        </nav>
        <div className="nav-actions">
          <Link href={APP_LINKS.login}>Log in</Link>
          <ArrowLink href={APP_LINKS.register}>Get started</ArrowLink>
        </div>
        <Drawer state={menu}>
          <Button
            className="nav-toggle"
            variant="tertiary"
            isIconOnly
            aria-label="Open navigation"
            aria-expanded={menu.isOpen}
            aria-controls="mobile-menu"
          >
            <Menu aria-hidden="true" />
          </Button>
          <Drawer.Backdrop>
            <Drawer.Content placement="right">
              <Drawer.Dialog className="navigation-drawer">
                <Drawer.CloseTrigger aria-label="Close navigation" />
                <Drawer.Header>
                  <Drawer.Heading>FinCo-Pilot</Drawer.Heading>
                  <p>A little clarity starts here.</p>
                </Drawer.Header>
                <Drawer.Body>
                  <nav
                    id="mobile-menu"
                    className="mobile-nav"
                    aria-label="Mobile navigation"
                  >
                    {nav.map((item, index) => (
                      <Link
                        key={item.href}
                        href={item.href}
                        onPress={() => menu.close()}
                      >
                        <span className="menu-number">0{index + 1}</span>
                        {item.title}
                        <ArrowRight size={18} aria-hidden="true" />
                      </Link>
                    ))}
                    <Separator />
                    <Link href={APP_LINKS.login}>Log in</Link>
                    <ArrowLink href={APP_LINKS.register}>Get started</ArrowLink>
                  </nav>
                </Drawer.Body>
              </Drawer.Dialog>
            </Drawer.Content>
          </Drawer.Backdrop>
        </Drawer>
      </div>
    </header>
  )
}
function ProductPreview() {
  return (
    <div className="preview-stack">
      <div className="preview-topline">
        <span>
          <span className="status-dot" /> YOUR MONTH, IN PERSPECTIVE
        </span>
        <Chip size="sm" variant="soft">
          Synthetic example
        </Chip>
      </div>
      <Card
        className="balance-card"
        aria-label="Illustrative monthly money example"
      >
        <Card.Header>
          <span className="small-label">
            <Wallet size={16} aria-hidden="true" /> THE BALANCE IS THE STARTING
            POINT
          </span>
        </Card.Header>
        <Card.Content>
          <div className="hero-cash">
            <span>Money in the bank</span>
            <strong>₹62,000</strong>
          </div>
          <div className="money-sequence" aria-label="Example reserves">
            <div className="sequence-step step-one">
              <span className="sequence-number">01</span>
              <div>
                <strong>Keep your commitments</strong>
                <span>Bills & EMI</span>
              </div>
              <b>₹22,000</b>
            </div>
            <div className="sequence-step step-two">
              <span className="sequence-number">02</span>
              <div>
                <strong>Make room for tomorrow</strong>
                <span>Buffer + goal reserve</span>
              </div>
              <b>₹15,000</b>
            </div>
          </div>
          <div className="balance-result step-three">
            <div>
              <span>Room to choose in this example</span>
              <strong>₹25,000</strong>
            </div>
            <ArrowDown aria-hidden="true" />
            <Meter
              value={25000}
              maxValue={62000}
              aria-label="Sample remainder as a share of sample cash"
            >
              <Meter.Track>
                <Meter.Fill />
              </Meter.Track>
            </Meter>
          </div>
        </Card.Content>
        <Card.Footer>
          <p className="capture-note">
            Illustrative interface · No real account data.
            <br />
            Simplified arithmetic, not a spending recommendation.
          </p>
        </Card.Footer>
      </Card>
      <Link className="preview-footnote" href="#perspective">
        Change the assumptions. See the difference.
        <ArrowRight size={15} aria-hidden="true" />
      </Link>
    </div>
  )
}
function Hero() {
  return (
    <section className="hero-section">
      <div className="shell hero-grid">
        <div className="hero-copy">
          <Chip variant="soft" className="hero-chip">
            <span className="status-dot" /> A calmer way to manage money
          </Chip>
          <h1>
            Bank balance.
            <br />
            <span>Meet real life.</span>
          </h1>
          <p className="hero-description">
            See what your money already needs to do. Bring accounts, bills and
            goals together before your next spending decision.
          </p>
          <div className="hero-actions">
            <ArrowLink href={APP_LINKS.register}>
              Start your workspace
            </ArrowLink>
            <Link
              href="#perspective"
              className="button button--lg button--secondary"
            >
              Try the example
              <ArrowDown size={18} aria-hidden="true" />
            </Link>
          </div>
          <p className="hero-note">
            <Check size={16} aria-hidden="true" /> Start with manual accounts{' '}
            <span aria-hidden="true">·</span> Bank connection optional
          </p>
          <div className="hero-principle">
            <span aria-hidden="true">YOUR MONEY, WITH CONTEXT</span>
            <p>
              Keep today organised.
              <br />
              <strong>Give tomorrow some room.</strong>
            </p>
          </div>
        </div>
        <div className="hero-visual">
          <ProductPreview />
        </div>
      </div>
      <div className="shell capability-strip">
        <span>ONE PLACE. A CLEARER PICTURE.</span>
        <div>
          {[
            { icon: Landmark, text: 'Accounts' },
            { icon: FileText, text: 'Transactions' },
            { icon: ChartPie, text: 'Budgets & goals' },
            { icon: CalendarDays, text: 'What’s coming' },
          ].map(({ icon: Icon, text }) => (
            <span key={text}>
              <Icon size={18} aria-hidden="true" />
              {text}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
function FeatureSpecimen({ index }: { index: number }) {
  if (index === 0)
    return (
      <div
        className="feature-specimen account-specimen"
        aria-label="Synthetic account illustration"
      >
        <div>
          <Landmark size={16} aria-hidden="true" />
          <span>Everyday</span>
          <strong>₹42,000</strong>
        </div>
        <div>
          <Landmark size={16} aria-hidden="true" />
          <span>Savings</span>
          <strong>₹20,000</strong>
        </div>
      </div>
    )
  if (index === 1)
    return (
      <div
        className="feature-specimen transaction-specimen"
        aria-label="Synthetic transaction illustration"
      >
        <div>
          <span className="mini-category">G</span>
          <span>
            Groceries<small>Everyday account</small>
          </span>
          <strong>−₹250</strong>
        </div>
        <div>
          <span className="mini-category income">I</span>
          <span>
            Income<small>Everyday account</small>
          </span>
          <strong>+₹1,000</strong>
        </div>
      </div>
    )
  if (index === 2)
    return (
      <div className="feature-specimen goal-specimen">
        <Meter value={60} aria-label="Synthetic goal, 60 percent saved">
          <div className="mini-meter-label">
            <span>Emergency reserve</span>
            <Meter.Output />
          </div>
          <Meter.Track>
            <Meter.Fill />
          </Meter.Track>
        </Meter>
        <span>₹60,000 of ₹1,00,000 · Synthetic</span>
      </div>
    )
  if (index === 3)
    return (
      <div className="feature-specimen recurring-specimen">
        <span className="mini-date">
          25<small>OCT</small>
        </span>
        <span>
          Household supplies<small>Monthly · Synthetic</small>
        </span>
        <strong>₹4,000</strong>
      </div>
    )
  if (index === 4)
    return (
      <div className="feature-specimen import-specimen">
        <Chip size="sm" variant="soft">
          CSV
        </Chip>
        <ArrowRight size={16} aria-hidden="true" />
        <span>Preview & map</span>
        <ArrowRight size={16} aria-hidden="true" />
        <Check size={17} aria-hidden="true" />
      </div>
    )
  return (
    <div className="feature-specimen module-specimen">
      {['Reports', 'Assets', 'Invoices'].map((text) => (
        <Chip key={text} variant="soft">
          {text}
        </Chip>
      ))}
    </div>
  )
}
function WhyFinCo() {
  return (
    <section className="section shell" id="why-finco">
      <div className="section-head">
        <div>
          <p className="section-kicker">A HOME FOR YOUR FINANCIAL LIFE</p>
          <h2>
            Less scattered.
            <br />
            <span>More understood.</span>
          </h2>
        </div>
        <p>
          From the everyday details to the bigger picture. Keep the pieces
          together, so your next decision has somewhere to start.
        </p>
      </div>
      <div className="feature-grid">
        {features.map((feature, index) => (
          <Card key={feature.title} className="feature-card" variant="default">
            <Card.Header>
              <div className="feature-top">
                <span className="feature-icon">{feature.icon}</span>
                <Chip size="sm" variant="soft">
                  0{index + 1}
                </Chip>
              </div>
              <Card.Title>{feature.title}</Card.Title>
            </Card.Header>
            <Card.Content>
              <p>{feature.body}</p>
              <FeatureSpecimen index={index} />
            </Card.Content>
            <Card.Footer>
              <span className="feature-detail">
                {feature.detail}
                <ArrowRight size={15} aria-hidden="true" />
              </span>
            </Card.Footer>
          </Card>
        ))}
      </div>
      <Link className="section-link" href={landingAsset('/features/')}>
        Explore features and availability
        <Link.Icon />
      </Link>
    </section>
  )
}
function Experience() {
  return (
    <section
      className="section planning-section"
      id="perspective"
      aria-labelledby="planning-title"
    >
      <div className="shell planning-grid">
        <div className="planning-copy">
          <p className="section-kicker">TRY A DIFFERENT PERSPECTIVE</p>
          <h2 id="planning-title">
            Some money
            <br />
            already has
            <br />
            <span>somewhere to be.</span>
          </h2>
          <p className="section-intro">
            A bigger buffer. A busier month. A goal worth protecting. Change the
            assumptions and see what happens to a sample balance.
          </p>
          <ul className="plain-checks">
            <li>
              <Check aria-hidden="true" />
              Pick a sample month or make your own
            </li>
            <li>
              <Check aria-hidden="true" />
              Adjust bills, buffer and goal reserves
            </li>
            <li>
              <Check aria-hidden="true" />
              See a remainder, zero or a shortfall
            </li>
          </ul>
          <div className="demo-boundary">
            <ShieldCheck aria-hidden="true" />
            <p>
              Your financial records stay yours.
              <span>This example runs locally and reads no account data.</span>
            </p>
          </div>
          <p className="capture-note">
            The actual spending plan also checks confirmed balances, card debt
            and reviewed obligations. Missing inputs can block an estimate.
          </p>
        </div>
        <SpendingPlayground />
      </div>
    </section>
  )
}
const setupSteps = [
  [
    'Set up your workspace',
    'Choose an account type and currency. Start manually, with a reliable current balance.',
    Landmark,
  ],
  [
    'Bring in the details',
    'Add transactions or preview a small file. Check dates, signs and duplicates before confirming.',
    Download,
  ],
  [
    'Review your next move',
    'Explore one budget, goal or report. Check upcoming commitments before making a spending plan.',
    ChartPie,
  ],
] as const
function HowItWorks() {
  return (
    <section className="section shell" id="how-it-works">
      <div className="section-head">
        <div>
          <p className="section-kicker">MAKE A START. KEEP IT SIMPLE.</p>
          <h2>
            One useful task.
            <br />
            <span>Then the next.</span>
          </h2>
        </div>
        <p>
          No need to organise your entire financial life in one sitting. Start
          with the records you can verify.
        </p>
      </div>
      <ol className="getting-started">
        {setupSteps.map(([title, text, Icon], i) => (
          <li key={title}>
            <Card variant="transparent">
              <Card.Header>
                <div className="step-top">
                  <Chip variant="soft">STEP 0{i + 1}</Chip>
                  <Icon aria-hidden="true" />
                </div>
                <Card.Title>{title}</Card.Title>
              </Card.Header>
              <Card.Content>
                <p>{text}</p>
              </Card.Content>
            </Card>
          </li>
        ))}
      </ol>
      <Link className="section-link" href={landingAsset('/how-it-works/')}>
        Read the first-session checklist
        <Link.Icon />
      </Link>
      <ImportWalkthrough />
    </section>
  )
}
function Privacy() {
  return (
    <section className="section trust-section">
      <div className="shell">
        <div className="section-head">
          <div>
            <p className="section-kicker">
              PERSONAL FINANCE. PERSONAL CHOICES.
            </p>
            <h2>
              Your context.
              <br />
              <span>Your control.</span>
            </h2>
          </div>
          <p>
            Know what you are using, what you are connecting and what the
            numbers can tell you.
          </p>
        </div>
        <div className="trust-grid">
          {[
            {
              icon: LockKeyhole,
              title: 'Workspace permissions',
              body: 'Access depends on authentication and workspace roles. Review who can see or change records in a shared workspace.',
            },
            {
              icon: Landmark,
              title: 'Connections are a choice',
              body: 'Start with manual records. Optional bank and AI providers depend on configuration, permissions and availability.',
            },
            {
              icon: ShieldCheck,
              title: 'Inputs before estimates',
              body: 'A dashboard reflects the records included. Check missing balances, bills and debts before relying on an estimate.',
            },
          ].map(({ icon: Icon, title, body }) => (
            <Card key={title} variant="transparent" className="trust-item">
              <Card.Header>
                <span className="feature-icon">
                  <Icon aria-hidden="true" />
                </span>
                <Card.Title>{title}</Card.Title>
              </Card.Header>
              <Card.Content>
                <p>{body}</p>
              </Card.Content>
            </Card>
          ))}
        </div>
        <Card className="product-principles">
          <Card.Header>
            <Chip size="sm" variant="soft">
              WHY FINCO-PILOT
            </Chip>
            <Card.Title>Built around everyday decisions.</Card.Title>
          </Card.Header>
          <Card.Content>
            <p>
              A useful financial workspace gives your balances, records and
              plans a shared context. Start with the information you can verify,
              then build a picture you understand.
            </p>
            <ul>
              <li>
                <Check size={16} aria-hidden="true" />
                Manual records are a valid starting point
              </li>
              <li>
                <Check size={16} aria-hidden="true" />
                Estimates need reviewed inputs
              </li>
              <li>
                <Check size={16} aria-hidden="true" />
                Optional connections have explicit boundaries
              </li>
            </ul>
          </Card.Content>
          <Card.Footer>
            <Link href={landingAsset('/how-it-works/')}>
              See the first-session checklist
              <Link.Icon />
            </Link>
          </Card.Footer>
        </Card>
        <div className="policy-actions">
          <Link href={APP_LINKS.privacy} className="button button--secondary">
            Read the privacy policy
          </Link>
          <Link href={APP_LINKS.terms}>
            Read the terms
            <Link.Icon />
          </Link>
        </div>
      </div>
    </section>
  )
}
function FAQList({
  indexes,
  initial = false,
}: {
  indexes: number[]
  initial?: boolean
}) {
  return (
    <Accordion
      className="faq-list"
      variant="surface"
      defaultExpandedKeys={initial ? ['faq-1'] : []}
      allowsMultipleExpanded
    >
      {indexes.map((index) => (
        <Accordion.Item id={'faq-' + (index + 1)} key={faqs[index][0]}>
          <Accordion.Heading>
            <Accordion.Trigger>
              {faqs[index][0]}
              <Accordion.Indicator />
            </Accordion.Trigger>
          </Accordion.Heading>
          <Accordion.Panel>
            <Accordion.Body>
              <p>{faqs[index][1]}</p>
            </Accordion.Body>
          </Accordion.Panel>
        </Accordion.Item>
      ))}
    </Accordion>
  )
}
function Questions() {
  return (
    <section className="section shell faq-section" id="questions">
      <div>
        <p className="section-kicker">A LITTLE CONTEXT GOES A LONG WAY</p>
        <h2>
          Good questions.
          <br />
          <span>Straight answers.</span>
        </h2>
        <p className="section-intro">Get to know your next workspace.</p>
        <Link href={APP_LINKS.support}>
          Support options
          <Link.Icon />
        </Link>
      </div>
      <div className="faq-groups">
        <FAQList indexes={[0, 1, 2, 3, 5]} initial />
        <Disclosure className="more-questions">
          <Disclosure.Heading>
            <Disclosure.Trigger>
              Five more questions
              <Disclosure.Indicator />
            </Disclosure.Trigger>
          </Disclosure.Heading>
          <Disclosure.Content>
            <FAQList indexes={[4, 6, 7, 8, 9]} />
          </Disclosure.Content>
        </Disclosure>
      </div>
    </section>
  )
}
function FinalCTA() {
  return (
    <section className="final-section shell">
      <Card className="final-card">
        <Card.Content>
          <div>
            <Chip variant="soft">A CLEARER PLACE TO START</Chip>
            <h2>
              Make room for
              <br />
              your next chapter.
            </h2>
            <p>Start with one account. Build from there.</p>
          </div>
          <div className="final-actions">
            <ArrowLink href={APP_LINKS.register} light>
              Open your workspace
            </ArrowLink>
            <Link href={APP_LINKS.pricing}>
              View current plans
              <Link.Icon />
            </Link>
            <span>Check live sign-up and plan availability.</span>
          </div>
        </Card.Content>
      </Card>
    </section>
  )
}
function Footer() {
  return (
    <footer className="footer">
      <div className="shell">
        <div className="footer-top">
          <div>
            <Link href="#top" aria-label="FinCo-Pilot, back to top">
              <Mark />
            </Link>
            <p>Your money, with context.</p>
          </div>
          <nav className="footer-links" aria-label="Footer navigation">
            <Link href={landingAsset('/features/')}>Features</Link>
            <Link href={landingAsset('/how-it-works/')}>How it works</Link>
            <Link href={landingAsset('/guides/import-transactions/')}>
              Import guide
            </Link>
            <Link href={APP_LINKS.pricing}>Pricing</Link>
            <Link href={APP_LINKS.support}>Support</Link>
            <Link href={APP_LINKS.login}>Log in</Link>
          </nav>
        </div>
        <Separator />
        <div className="footer-bottom">
          <span>© 2026 FinCo-Pilot</span>
          <nav aria-label="Policies">
            <Link href={APP_LINKS.privacy}>Privacy</Link>
            <Link href={APP_LINKS.terms}>Terms</Link>
            <Link href="#top">
              Back to top
              <ArrowUp size={16} aria-hidden="true" />
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  )
}
export function LandingExperience() {
  return (
    <>
      <InstalledAppHandoff />
      <div className="marketing-page">
        <Link className="skip-link" href="#main-content">
          Skip to content
        </Link>
        <Navigation />
        <main id="main-content">
          <Hero />
          <ProductScreens />
          <Experience />
          <WhyFinCo />
          <HowItWorks />
          <Privacy />
          <PlanPreview />
          <Questions />
          <FinalCTA />
        </main>
        <Footer />
        <MobileActions />
      </div>
    </>
  )
}
