'use client'

import { useRef, useState } from 'react'
import Alert from 'antd/es/alert'
import Button from 'antd/es/button'
import Card from 'antd/es/card'
import Collapse from 'antd/es/collapse'
import Divider from 'antd/es/divider'
import Drawer from 'antd/es/drawer'
import Flex from 'antd/es/flex'
import InputNumber from 'antd/es/input-number'
import Progress from 'antd/es/progress'
import Statistic from 'antd/es/statistic'
import Steps from 'antd/es/steps'
import Tag from 'antd/es/tag'
import {
  ArrowDownOutlined,
  ArrowRightOutlined,
  ArrowUpOutlined,
  BankOutlined,
  CalendarOutlined,
  CheckOutlined,
  FileTextOutlined,
  ImportOutlined,
  LockOutlined,
  MenuOutlined,
  PieChartOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  WalletOutlined,
} from '@ant-design/icons'
import { InstalledAppHandoff } from '@/components/installed-app-handoff'
import { LandingTheme } from '@/components/landing-theme'
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
    icon: <BankOutlined aria-hidden="true" />,
    title: 'Accounts, together.',
    body: 'Organise cash, bank and card accounts by type and currency. Start manually; a bank connection is optional.',
    detail: 'A home for each balance',
  },
  {
    icon: <FileTextOutlined aria-hidden="true" />,
    title: 'Every transaction, in context.',
    body: 'Review income and expenses with categories, payees and account context. Find the details behind a monthly total.',
    detail: 'From records to a useful picture',
  },
  {
    icon: <PieChartOutlined aria-hidden="true" />,
    title: 'A plan for the month.',
    body: 'Use budgets to organise spending and goals to track what you are saving towards. Review progress as your records change.',
    detail: 'Budgets + goals',
  },
  {
    icon: <CalendarOutlined aria-hidden="true" />,
    title: 'Remember what repeats.',
    body: 'Manage recurring transactions and loan or EMI plans. Include upcoming outflows when reviewing a spending estimate.',
    detail: 'Today, with tomorrow in view',
  },
  {
    icon: <ImportOutlined aria-hidden="true" />,
    title: 'Bring your records with you.',
    body: 'Preview transaction files, choose the destination and check mappings before confirming. CSV, QIF, OFX/QFX and CAMT are supported formats.',
    detail: 'Review before you import',
  },
  {
    icon: <SettingOutlined aria-hidden="true" />,
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
      FinCo-Pilot<span aria-hidden="true">↗</span>
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
    <Button
      type="primary"
      size="large"
      href={href}
      icon={<ArrowRightOutlined aria-hidden="true" />}
      iconPlacement="end"
      className={light ? 'cta-light' : undefined}
    >
      {children}
    </Button>
  )
}
function Navigation() {
  const [menuOpen, setMenuOpen] = useState(false)
  const toggle = useRef<HTMLButtonElement>(null)
  return (
    <header className="site-header" id="top">
      <div className="shell nav-inner">
        <a href="#top" aria-label="FinCo-Pilot, back to top">
          <Mark />
        </a>
        <nav className="nav-desktop" aria-label="Primary navigation">
          {nav.map((item) => (
            <a key={item.href} href={item.href}>
              {item.title}
            </a>
          ))}
        </nav>
        <Flex align="center" gap={12} className="nav-actions">
          <Button type="text" href={APP_LINKS.login}>
            Log in
          </Button>
          <ArrowLink href={APP_LINKS.register}>Get started</ArrowLink>
        </Flex>
        <Button
          ref={toggle}
          className="nav-toggle"
          type="text"
          icon={<MenuOutlined aria-hidden="true" />}
          aria-label="Open navigation"
          aria-expanded={menuOpen}
          aria-controls="mobile-menu"
          onClick={() => setMenuOpen(true)}
        />
        <Drawer
          title="FinCo-Pilot"
          open={menuOpen}
          onClose={() => setMenuOpen(false)}
          afterOpenChange={(open) => {
            if (!open) toggle.current?.focus()
          }}
          placement="right"
          size={340}
        >
          <nav
            id="mobile-menu"
            className="mobile-nav"
            aria-label="Mobile navigation"
          >
            {nav.map((item) => (
              <Button
                type="text"
                key={item.href}
                href={item.href}
                onClick={() => setMenuOpen(false)}
                icon={<ArrowRightOutlined aria-hidden="true" />}
                iconPlacement="end"
              >
                {item.title}
              </Button>
            ))}
            <Divider />
            <Button href={APP_LINKS.login}>Log in</Button>
            <ArrowLink href={APP_LINKS.register}>Get started</ArrowLink>
          </nav>
        </Drawer>
      </div>
    </header>
  )
}
function ProductPreview() {
  return (
    <Card
      className="balance-card"
      aria-label="Illustrative monthly money example"
    >
      <Flex justify="space-between" align="center" gap={8}>
        <span className="small-label">
          <WalletOutlined aria-hidden="true" /> YOUR MONTH, EXPLAINED
        </span>
        <Tag bordered={false}>Sample data</Tag>
      </Flex>
      <div className="balance-start">
        <span>Bank balance</span>
        <strong>₹62,000</strong>
      </div>
      <Divider />
      <dl className="balance-breakdown">
        <div>
          <dt>
            <span className="row-icon">
              <CalendarOutlined aria-hidden="true" />
            </span>
            Bills & EMI set aside
          </dt>
          <dd>−₹22,000</dd>
        </div>
        <div>
          <dt>
            <span className="row-icon">
              <SafetyCertificateOutlined aria-hidden="true" />
            </span>
            Emergency buffer
          </dt>
          <dd>−₹10,000</dd>
        </div>
        <div>
          <dt>
            <span className="row-icon">
              <BankOutlined aria-hidden="true" />
            </span>
            Savings goal reserve
          </dt>
          <dd>−₹5,000</dd>
        </div>
      </dl>
      <div className="balance-result">
        <span>What remains in this example</span>
        <strong>
          ₹25,000
          <ArrowDownOutlined aria-hidden="true" />
        </strong>
        <Progress
          percent={40}
          showInfo={false}
          strokeColor="#165dff"
          trailColor="#dfe8fc"
          aria-label="Illustrative remainder, approximately 40 percent of sample balance"
        />
      </div>
      <p className="capture-note">
        Illustrative interface · No real account data.
        <br />
        Simplified arithmetic, not a spending recommendation.
      </p>
    </Card>
  )
}
function Hero() {
  return (
    <section className="hero-section">
      <div className="shell hero-grid">
        <div className="hero-copy">
          <Tag color="blue" bordered={false}>
            YOUR PERSONAL FINANCE WORKSPACE
          </Tag>
          <h1>
            Bank balance.
            <br />
            <span>Meet real life.</span>
          </h1>
          <p className="hero-description">
            Your balance is only the beginning. Bring accounts, bills, budgets
            and goals into focus—before your next money decision.
          </p>
          <div className="hero-actions">
            <ArrowLink href={APP_LINKS.register}>
              Start your workspace
            </ArrowLink>
            <Button
              size="large"
              href="#experience"
              icon={<ArrowDownOutlined aria-hidden="true" />}
              iconPlacement="end"
            >
              See the product
            </Button>
          </div>
          <p className="hero-note">
            <CheckOutlined aria-hidden="true" /> Start with manual accounts{' '}
            <span aria-hidden="true">·</span> Bank connection optional
          </p>
        </div>
        <div className="hero-visual">
          <div className="visual-label">
            <span>THE NUMBER ISN’T THE WHOLE STORY.</span>
            <ArrowDownOutlined aria-hidden="true" />
          </div>
          <ProductPreview />
          <p className="visual-caption">
            Make room for the things your balance doesn’t explain.
          </p>
        </div>
      </div>
      <div className="shell capability-strip">
        <span>ONE WORKSPACE FOR</span>
        <Flex gap={28} wrap>
          <span>
            <BankOutlined aria-hidden="true" /> Accounts
          </span>
          <span>
            <FileTextOutlined aria-hidden="true" /> Transactions
          </span>
          <span>
            <PieChartOutlined aria-hidden="true" /> Budgets & goals
          </span>
          <span>
            <CalendarOutlined aria-hidden="true" /> What’s coming
          </span>
        </Flex>
      </div>
    </section>
  )
}
function WhyFinCo() {
  return (
    <section className="section shell" id="why-finco">
      <div className="section-head">
        <div>
          <p className="section-kicker">01 / SEE THE WHOLE PICTURE</p>
          <h2>
            Less scattered.
            <br />
            More understood.
          </h2>
        </div>
        <p>
          A transaction tells you what happened. A useful workspace helps you
          connect it to everything else.
        </p>
      </div>
      <div className="feature-grid">
        {features.map((feature, index) => (
          <Card key={feature.title} className="feature-card" hoverable>
            <div className="feature-top">
              <span className="feature-icon">{feature.icon}</span>
              <span className="small-label">0{index + 1}</span>
            </div>
            <h3>{feature.title}</h3>
            <p>{feature.body}</p>
            <span className="feature-detail">{feature.detail}</span>
          </Card>
        ))}
      </div>
      <Button
        type="link"
        href={landingAsset('/features/')}
        icon={<ArrowRightOutlined aria-hidden="true" />}
        iconPlacement="end"
      >
        Explore features and availability
      </Button>
    </section>
  )
}
function Experience() {
  const [buffer, setBuffer] = useState<number | null>(10000)
  const remainder = buffer === null ? null : 62000 - 22000 - buffer - 5000
  return (
    <section className="section planning-section" id="perspective">
      <div className="shell planning-grid">
        <div>
          <p className="section-kicker">03 / A NUMBER WITH CONTEXT</p>
          <h2>
            ₹62,000 in the bank.
            <br />
            How much is yours
            <br />
            to spend?
          </h2>
          <p className="section-intro">
            Rent, repayments and savings still need a place. The spending-plan
            tool brings confirmed balances and reviewed obligations into the
            same calculation.
          </p>
          <ul className="plain-checks">
            <li>
              <CheckOutlined aria-hidden="true" /> Confirm current cash and card
              debt
            </li>
            <li>
              <CheckOutlined aria-hidden="true" /> Review upcoming bills and
              loan installments
            </li>
            <li>
              <CheckOutlined aria-hidden="true" /> Protect the reserves you
              choose
            </li>
          </ul>
          <p className="capture-note">
            The app can withhold an estimate when required inputs are missing.
            Review the inputs before relying on a result.
          </p>
        </div>
        <Card className="planning-demo">
          <Flex justify="space-between" align="center" wrap gap={8}>
            <h3>Try a simple example.</h3>
            <Tag color="blue">Interactive illustration</Tag>
          </Flex>
          <p>Change the buffer. See why the balance alone isn’t enough.</p>
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
          <label htmlFor="example-buffer">Emergency buffer to protect</label>
          <InputNumber
            id="example-buffer"
            aria-label="Emergency buffer to protect"
            prefix="₹"
            min={0}
            max={62000}
            step={1000}
            precision={0}
            value={buffer}
            onChange={(value) => setBuffer(value)}
            size="large"
            className="buffer-input"
          />
          <div className="example-result" aria-live="polite" aria-atomic="true">
            {remainder === null ? (
              <p>Enter a buffer to see the example.</p>
            ) : (
              <>
                <Statistic
                  title={
                    remainder < 0
                      ? 'Illustrative shortfall'
                      : 'Illustrative remainder'
                  }
                  value={Math.abs(remainder)}
                  formatter={() => money(Math.abs(remainder))}
                />
                <p>
                  {remainder < 0
                    ? 'These sample commitments exceed the sample balance.'
                    : 'After the sample bills, goal reserve and your chosen buffer.'}
                </p>
              </>
            )}
          </div>
          <Alert
            type="info"
            showIcon
            title="Example only"
            description="This runs locally with made-up numbers. The actual spending plan also checks account balances, debt and upcoming obligations. No account is connected."
          />
        </Card>
      </div>
    </section>
  )
}
function HowItWorks() {
  return (
    <section className="section shell" id="how-it-works">
      <div className="section-head">
        <div>
          <p className="section-kicker">04 / START SMALL</p>
          <h2>
            One useful task.
            <br />
            Then the next.
          </h2>
        </div>
        <p>
          No need to organise your entire financial life in one sitting. Start
          with the records you can verify.
        </p>
      </div>
      <Steps
        current={-1}
        className="getting-started"
        items={[
          {
            title: 'Set up your workspace',
            content:
              'Choose an account type and currency. Start manually, with a reliable current balance.',
            icon: <BankOutlined aria-hidden="true" />,
          },
          {
            title: 'Bring in the details',
            content:
              'Add transactions or preview a small file. Check dates, signs and duplicates before confirming.',
            icon: <ImportOutlined aria-hidden="true" />,
          },
          {
            title: 'Review your next move',
            content:
              'Explore one budget, goal or report. Check upcoming commitments before making a spending plan.',
            icon: <PieChartOutlined aria-hidden="true" />,
          },
        ]}
      />
      <Button
        type="link"
        href={landingAsset('/how-it-works/')}
        icon={<ArrowRightOutlined aria-hidden="true" />}
        iconPlacement="end"
      >
        Read the first-session checklist
      </Button>
      <Card className="import-callout">
        <div className="import-copy">
          <Tag bordered={false}>A PRACTICAL FIRST STEP</Tag>
          <h3>
            Your records already exist.
            <br />
            Give them a useful home.
          </h3>
          <p>
            Work from a CSV or supported statement file. Preview the mapping,
            confirm the account and inspect excluded rows before applying it.
          </p>
          <Button
            href={landingAsset('/guides/import-transactions/')}
            icon={<ArrowRightOutlined aria-hidden="true" />}
            iconPlacement="end"
          >
            Read the import guide
          </Button>
        </div>
        <div className="import-example">
          <div className="file-label">
            <FileTextOutlined aria-hidden="true" /> transactions-example.csv{' '}
            <Tag>2 rows</Tag>
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
          <Button
            type="link"
            href={landingAsset('/samples/transactions-example.csv')}
            download
            icon={<ArrowDownOutlined aria-hidden="true" />}
          >
            Download the sample CSV
          </Button>
        </div>
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
            <p className="section-kicker">05 / YOUR CONTEXT. YOUR CONTROL.</p>
            <h2>
              Personal finance.
              <br />
              With clear boundaries.
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
              icon: <LockOutlined aria-hidden="true" />,
              title: 'Workspace permissions',
              body: 'Access depends on authentication and workspace roles. Review who can see or change records in a shared workspace.',
            },
            {
              icon: <BankOutlined aria-hidden="true" />,
              title: 'Connections are a choice',
              body: 'Start with manual records. Optional bank and AI providers depend on configuration, permissions and availability.',
            },
            {
              icon: <SafetyCertificateOutlined aria-hidden="true" />,
              title: 'Inputs before estimates',
              body: 'A dashboard reflects the records included. Check missing balances, bills and debts before relying on an estimate.',
            },
          ].map((item) => (
            <div className="trust-item" key={item.title}>
              <span className="feature-icon">{item.icon}</span>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </div>
          ))}
        </div>
        <Flex wrap gap={12}>
          <Button href={APP_LINKS.privacy}>Read the privacy policy</Button>
          <Button type="text" href={APP_LINKS.terms}>
            Read the terms <ArrowRightOutlined aria-hidden="true" />
          </Button>
        </Flex>
      </div>
    </section>
  )
}
function Questions() {
  return (
    <section className="section shell faq-section" id="questions">
      <div>
        <p className="section-kicker">06 / BEFORE YOU START</p>
        <h2>
          Good questions.
          <br />
          Straight answers.
        </h2>
        <p className="section-intro">A little context goes a long way.</p>
        <Button
          type="link"
          href={APP_LINKS.support}
          icon={<ArrowRightOutlined aria-hidden="true" />}
          iconPlacement="end"
        >
          Support options
        </Button>
      </div>
      <Collapse
        className="faq-list"
        defaultActiveKey={['faq-1']}
        expandIconPlacement="end"
        items={faqs.map(([question, answer], index) => ({
          key: `faq-${index + 1}`,
          label: question,
          children: <p>{answer}</p>,
        }))}
      />
    </section>
  )
}
function FinalCTA() {
  return (
    <section className="final-section">
      <div className="shell final-inner">
        <div>
          <p className="section-kicker">A CLEARER PLACE TO START</p>
          <h2>
            Make your next decision
            <br />
            with the whole picture.
          </h2>
          <p>Start with one account. Build from there.</p>
        </div>
        <div className="final-actions">
          <ArrowLink href={APP_LINKS.register} light>
            Open your workspace
          </ArrowLink>
          <Button type="link" href={APP_LINKS.pricing}>
            View current plans <ArrowRightOutlined aria-hidden="true" />
          </Button>
          <span>Check live sign-up and plan availability.</span>
        </div>
      </div>
    </section>
  )
}
function Footer() {
  return (
    <footer className="footer">
      <div className="shell">
        <div className="footer-top">
          <div>
            <a href="#top" aria-label="FinCo-Pilot, back to top">
              <Mark />
            </a>
            <p>Your money, with context.</p>
          </div>
          <nav className="footer-links" aria-label="Footer navigation">
            <a href={landingAsset('/features/')}>Features</a>
            <a href={landingAsset('/how-it-works/')}>How it works</a>
            <a href={landingAsset('/guides/import-transactions/')}>
              Import guide
            </a>
            <a href={APP_LINKS.pricing}>Pricing</a>
            <a href={APP_LINKS.support}>Support</a>
            <a href={APP_LINKS.login}>Log in</a>
          </nav>
        </div>
        <Divider />
        <div className="footer-bottom">
          <span>© 2026 FinCo-Pilot</span>
          <nav aria-label="Policies">
            <a href={APP_LINKS.privacy}>Privacy</a>
            <a href={APP_LINKS.terms}>Terms</a>
            <a href="#top">
              Back to top <ArrowUpOutlined aria-hidden="true" />
            </a>
          </nav>
        </div>
      </div>
    </footer>
  )
}
export function LandingExperience() {
  return (
    <LandingTheme>
      <InstalledAppHandoff />
      <div className="marketing-page">
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
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
    </LandingTheme>
  )
}
