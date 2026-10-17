'use client'

import { useState } from 'react'
import {
  Accordion,
  Alert,
  Button,
  Card,
  Chip,
  Drawer,
  Label,
  Link,
  NumberField,
  ProgressBar,
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
const money = (value: number) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value)

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
          <span className="status-dot" /> A little more clarity
        </span>
        <Chip size="sm" variant="soft">
          Sample month
        </Chip>
      </div>
      <Card
        className="balance-card"
        aria-label="Illustrative monthly money example"
      >
        <Card.Header>
          <span className="small-label">
            <Wallet size={16} aria-hidden="true" /> YOUR MONEY, IN CONTEXT
          </span>
          <Card.Description>
            Start with the balance. Make room for real life.
          </Card.Description>
        </Card.Header>
        <Card.Content>
          <div className="balance-start">
            <span>Bank balance</span>
            <strong>
              ₹62,000<span>.00</span>
            </strong>
          </div>
          <Separator />
          <dl className="balance-breakdown">
            {[
              {
                icon: <CalendarDays aria-hidden="true" />,
                title: 'Bills & EMI set aside',
                value: '−₹22,000',
                type: 'bills',
              },
              {
                icon: <ShieldCheck aria-hidden="true" />,
                title: 'Emergency buffer',
                value: '−₹10,000',
                type: 'buffer',
              },
              {
                icon: <Landmark aria-hidden="true" />,
                title: 'Savings goal reserve',
                value: '−₹5,000',
                type: 'goal',
              },
            ].map((row) => (
              <div key={row.type}>
                <dt>
                  <span className={'row-icon ' + row.type}>{row.icon}</span>
                  {row.title}
                </dt>
                <dd>{row.value}</dd>
              </div>
            ))}
          </dl>
          <div className="balance-result">
            <div>
              <span>What remains in this example</span>
              <strong>₹25,000</strong>
            </div>
            <span className="result-arrow" aria-hidden="true">
              <ArrowUp />
            </span>
            <ProgressBar
              value={40}
              aria-label="Illustrative remainder, approximately 40 percent of sample balance"
            >
              <ProgressBar.Track>
                <ProgressBar.Fill />
              </ProgressBar.Track>
            </ProgressBar>
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
      <div className="preview-footnote">
        <span className="tiny-icon">
          <Check size={14} aria-hidden="true" />
        </span>
        Every reserve has a reason. Every number has context.
      </div>
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
            More than a number to check. A place to understand your accounts,
            make room for your bills, and move towards your goals.
          </p>
          <div className="hero-actions">
            <ArrowLink href={APP_LINKS.register}>
              Start your workspace
            </ArrowLink>
            <Link
              href="#experience"
              className="button button--lg button--secondary"
            >
              See the product
              <ArrowDown size={18} aria-hidden="true" />
            </Link>
          </div>
          <p className="hero-note">
            <Check size={16} aria-hidden="true" /> Start with manual accounts{' '}
            <span aria-hidden="true">·</span> Bank connection optional
          </p>
          <div className="hero-principle">
            <span aria-hidden="true">01 — 04</span>
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
  const [buffer, setBuffer] = useState(10000)
  const remainder = Number.isFinite(buffer)
    ? 62000 - 22000 - buffer - 5000
    : null
  return (
    <section className="section planning-section" id="perspective">
      <div className="shell planning-grid">
        <div>
          <p className="section-kicker">BALANCE IS JUST THE BEGINNING</p>
          <h2>
            Some money
            <br />
            already has <br />
            <span>somewhere to be.</span>
          </h2>
          <p className="section-intro">
            Rent. Repayments. The thing you’re saving for. Bring your
            commitments into the picture before deciding what is left.
          </p>
          <ul className="plain-checks">
            <li>
              <Check aria-hidden="true" />
              Confirm current cash and card debt
            </li>
            <li>
              <Check aria-hidden="true" />
              Review upcoming bills and loan installments
            </li>
            <li>
              <Check aria-hidden="true" />
              Protect the reserves you choose
            </li>
          </ul>
          <p className="capture-note">
            The app can withhold an estimate when required inputs are missing.
            Review the inputs before relying on a result.
          </p>
        </div>
        <Card className="planning-demo">
          <Card.Header>
            <Chip size="sm" variant="soft">
              TRY IT HERE
            </Chip>
            <Card.Title>A little buffer. A different picture.</Card.Title>
            <Card.Description>
              Change the reserve and see what remains.
            </Card.Description>
          </Card.Header>
          <Card.Content>
            <dl className="example-fixed">
              <div>
                <dt>Sample cash balance</dt>
                <dd>₹62,000</dd>
              </div>
              <div>
                <dt>Sample bills & EMI</dt>
                <dd>−₹22,000</dd>
              </div>
              <div>
                <dt>Sample goal reserve</dt>
                <dd>−₹5,000</dd>
              </div>
            </dl>
            <NumberField
              value={buffer}
              onChange={(value) => setBuffer(value ?? NaN)}
              minValue={0}
              maxValue={62000}
              step={1000}
              formatOptions={{
                style: 'currency',
                currency: 'INR',
                maximumFractionDigits: 0,
              }}
              className="buffer-input"
            >
              <Label>Emergency buffer to protect</Label>
              <NumberField.Group>
                <NumberField.DecrementButton aria-label="Decrease emergency buffer" />
                <NumberField.Input />
                <NumberField.IncrementButton aria-label="Increase emergency buffer" />
              </NumberField.Group>
            </NumberField>
            <div
              className="example-result"
              aria-live="polite"
              aria-atomic="true"
            >
              {remainder === null ? (
                <p>Enter a buffer to see the example.</p>
              ) : (
                <>
                  <span>
                    {remainder < 0
                      ? 'Illustrative shortfall'
                      : 'Illustrative remainder'}
                  </span>
                  <strong>{money(Math.abs(remainder))}</strong>
                  <p>
                    {remainder < 0
                      ? 'These sample commitments exceed the sample balance.'
                      : 'After the sample bills, goal reserve and your chosen buffer.'}
                  </p>
                </>
              )}
            </div>
          </Card.Content>
          <Card.Footer>
            <Alert status="default">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Title>Example only</Alert.Title>
                <Alert.Description>
                  This runs locally with made-up numbers. The actual spending
                  plan also checks account balances, debt and upcoming
                  obligations. No account is connected.
                </Alert.Description>
              </Alert.Content>
            </Alert>
          </Card.Footer>
        </Card>
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
      <Card className="import-callout">
        <Card.Content>
          <div className="import-copy">
            <Chip size="sm" variant="soft">
              YOUR RECORDS. A FRESH START.
            </Chip>
            <h3>
              Bring a little history.
              <br />
              Build a clearer picture.
            </h3>
            <p>
              Work from a CSV or supported statement file. Preview the mapping,
              confirm the account and inspect excluded rows before applying it.
            </p>
            <Link
              href={landingAsset('/guides/import-transactions/')}
              className="button button--secondary"
            >
              Read the import guide
              <ArrowRight size={18} aria-hidden="true" />
            </Link>
          </div>
          <div className="import-example">
            <div className="file-label">
              <span className="file-icon">
                <FileText aria-hidden="true" />
              </span>
              <div>
                <strong>transactions-example.csv</strong>
                <p>2 synthetic records · INR</p>
              </div>
            </div>
            <dl>
              <div>
                <dt>Sample income</dt>
                <dd>+₹1,000</dd>
              </div>
              <div>
                <dt>Sample grocery</dt>
                <dd>−₹250</dd>
              </div>
              <div>
                <dt>Net sample flow</dt>
                <dd>₹750</dd>
              </div>
            </dl>
            <p className="capture-note">
              Synthetic records. Net flow is not an account balance.
            </p>
            <Link
              href={landingAsset('/samples/transactions-example.csv')}
              download
            >
              <Download size={16} aria-hidden="true" />
              Download the sample CSV
            </Link>
          </div>
        </Card.Content>
      </Card>
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
      <Accordion
        className="faq-list"
        variant="surface"
        defaultExpandedKeys={['faq-1']}
        allowsMultipleExpanded
      >
        {faqs.map(([question, answer], index) => (
          <Accordion.Item id={'faq-' + (index + 1)} key={question}>
            <Accordion.Heading>
              <Accordion.Trigger>
                {question}
                <Accordion.Indicator />
              </Accordion.Trigger>
            </Accordion.Heading>
            <Accordion.Panel>
              <Accordion.Body>
                <p>{answer}</p>
              </Accordion.Body>
            </Accordion.Panel>
          </Accordion.Item>
        ))}
      </Accordion>
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
          <WhyFinCo />
          <ProductScreens />
          <Experience />
          <HowItWorks />
          <Privacy />
          <Questions />
          <FinalCTA />
        </main>
        <Footer />
      </div>
    </>
  )
}
