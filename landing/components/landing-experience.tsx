'use client'

import { useState } from 'react'
import { MotionConfig } from 'motion/react'
import {
  IconArrowRight, IconArrowUpRight, IconArrowDownRight, IconArrowsExchange,
  IconChartBar, IconChartDots3, IconCircleCheck, IconLock, IconMenu2,
  IconShieldLock, IconSparkles, IconTarget, IconWallet, IconX,
  IconBuildingBank, IconCalendarStats, IconReceipt, IconChevronRight
} from '@tabler/icons-react'
import { FinCoLogo } from '@/components/brand-mark'
import { Button } from '@/components/spaceui/button'
import { Badge } from '@/components/spaceui/badge'
import { Card } from '@/components/spaceui/card'
import { Link as SpaceLink } from '@/components/spaceui/link'
import { BlurRevealText } from '@/components/spaceui/blur-reveal-text'
import { ProximityGrid } from '@/components/spaceui/proximity-grid'
import { IdentityAvatar } from '@/components/spaceui/identity-avatar'
import { Accordion, AccordionItem, AccordionTrigger, AccordionPanel } from '@/components/spaceui/accordion'
import { APP_LINKS } from '@/lib/links'

type View = 'overview' | 'budgets' | 'activity'
type IconType = typeof IconWallet

const nav = [
  { title: 'Why FinCo', href: '#why-finco' },
  { title: 'The experience', href: '#experience' },
  { title: 'How it works', href: '#how-it-works' },
  { title: 'Questions', href: '#questions' },
]

const featureCards: Array<{ number: string; icon: IconType; title: string; body: string; label: string }> = [
  { number: '01', icon: IconWallet, title: 'Your complete picture.', body: 'Bring accounts, transactions and balances into one organised view. Stop piecing together the story across tabs.', label: 'SEE IT ALL' },
  { number: '02', icon: IconTarget, title: 'Plans you can actually follow.', body: 'Make room for essentials, set meaningful goals and check how your spending fits the bigger picture.', label: 'PLAN WITH INTENT' },
  { number: '03', icon: IconChartDots3, title: 'Understand the patterns.', body: 'Go from individual transactions to useful reporting, categories and recurring expenses without the spreadsheet detour.', label: 'FIND THE SIGNAL' },
  { number: '04', icon: IconSparkles, title: 'A little intelligence, when you want it.', body: 'Optional AI-assisted tools can help you explore financial questions in deployments where those capabilities are enabled.', label: 'STAY IN CONTROL' },
]

const steps = [
  { id: '01', title: 'Get your bearings', description: 'Start with a workspace built around your accounts and your preferences.', icon: IconBuildingBank },
  { id: '02', title: 'Bring the details together', description: 'Organise transactions and budgets; optional imports and connections depend on availability.', icon: IconArrowsExchange },
  { id: '03', title: 'Move with intention', description: 'Review reports, watch what repeats and make a clearer plan for what comes next.', icon: IconCalendarStats },
]

const faqs = [
  { id: 'faq-1', question: 'What is FinCo-Pilot?', answer: 'FinCo-Pilot is a personal finance workspace for tracking accounts and transactions, planning budgets and goals, and exploring reports. Optional features such as bank connections and AI agents depend on configuration and availability.' },
  { id: 'faq-2', question: 'Do I have to connect a bank account?', answer: 'No. FinCo-Pilot supports managing financial accounts and transactions manually. Import and provider-connection options are separate capabilities and may not be available on every deployment.' },
  { id: 'faq-3', question: 'Can I use FinCo-Pilot on my phone?', answer: 'The web application includes responsive screens and progressive web app support. Actual behaviour on your device depends on your browser and the deployment.' },
  { id: 'faq-4', question: 'Is the financial preview on this page real?', answer: 'The preview uses illustrative sample data to explain the interface. It is not a live account, personal financial data or a performance claim.' },
  { id: 'faq-5', question: 'Are AI features required?', answer: 'No. The core financial workspace is independent of optional agent capabilities. AI availability and access depend on the active product configuration.' },
]

const demoData: Record<View, { eyebrow: string; title: string; amount: string; delta: string; detail: string; bars: number[]; transactions: Array<{ name: string; context: string; amount: string; positive?: boolean }> }> = {
  overview: {
    eyebrow: 'All accounts · sample view', title: 'Your financial picture', amount: '₹1,84,250', delta: '+₹12,480', detail: 'This month', bars: [28, 42, 34, 54, 43, 64, 58, 79, 68, 87, 80, 96],
    transactions: [{ name: 'Monthly income', context: 'Income · Example', amount: '+₹42,000', positive: true }, { name: 'Groceries', context: 'Essentials · Example', amount: '−₹2,480' }, { name: 'Monthly savings', context: 'Goal · Example', amount: '−₹5,000' }]
  },
  budgets: {
    eyebrow: 'Spending plan · sample view', title: 'Available to plan', amount: '₹24,800', delta: '62% on track', detail: 'Current period', bars: [48, 46, 50, 55, 58, 54, 63, 67, 70, 72, 78, 82],
    transactions: [{ name: 'Essentials', context: 'Monthly budget · Example', amount: '₹12,200' }, { name: 'Everyday', context: 'Monthly budget · Example', amount: '₹6,400' }, { name: 'Savings goal', context: 'Monthly goal · Example', amount: '₹6,200', positive: true }]
  },
  activity: {
    eyebrow: 'Transactions · sample view', title: 'Activity in focus', amount: '18 items', delta: '3 categories', detail: 'This month', bars: [18, 46, 36, 58, 22, 55, 36, 70, 48, 62, 38, 75],
    transactions: [{ name: 'Grocery market', context: 'Food & drink · Example', amount: '−₹1,640' }, { name: 'Rent', context: 'Housing · Example', amount: '−₹12,000' }, { name: 'Salary', context: 'Income · Example', amount: '+₹42,000', positive: true }]
  }
}

function Mark({ compact = false }: { compact?: boolean }) {
  return <span className="brand-lockup"><span className="brand-symbol"><FinCoLogo size={compact ? 21 : 23} mode="on-dark" /></span><span className="brand-name">FinCo<span className="brand-hyphen">-</span>Pilot<span className="brand-period">.</span></span></span>
}

function ArrowLink({ href, children, light = false, small = false }: { href: string; children: React.ReactNode; light?: boolean; small?: boolean }) {
  return <Button render={<a href={href} />} variant="default" size={small ? 'lg' : 'xl'} className={light ? 'cta-button cta-button-light' : 'cta-button'}>{children}<IconArrowUpRight size={18} stroke={1.8} aria-hidden="true" /></Button>
}

function Navigation() {
  const [menuOpen, setMenuOpen] = useState(false)
  return <header className="site-header" id="top">
    <div className="nav-inner shell">
      <a href="#top" className="brand-link" aria-label="FinCo-Pilot, back to top"><Mark /></a>
      <nav className="nav-desktop" aria-label="Primary navigation">
        {nav.map(item => <SpaceLink key={item.href} href={item.href} variant="secondary" className="nav-text">{item.title}</SpaceLink>)}
      </nav>
      <div className="nav-actions">
        <SpaceLink href={APP_LINKS.login} variant="secondary" className="nav-login">Log in</SpaceLink>
        <ArrowLink href={APP_LINKS.register} small>Get started</ArrowLink>
      </div>
      <Button aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} aria-controls="mobile-menu" size="icon-lg" variant="ghost" className="nav-toggle" onClick={() => setMenuOpen(current => !current)}>
        {menuOpen ? <IconX size={22} /> : <IconMenu2 size={22} />}
      </Button>
    </div>
    <nav id="mobile-menu" className={menuOpen ? 'mobile-nav open' : 'mobile-nav'} aria-label="Mobile navigation" hidden={!menuOpen}>
      {nav.map(item => <SpaceLink key={item.href} href={item.href} onClick={() => setMenuOpen(false)} className="mobile-nav-link">{item.title}<IconChevronRight size={17}/></SpaceLink>)}
      <SpaceLink href={APP_LINKS.login} className="mobile-nav-link">Log in<IconChevronRight size={17}/></SpaceLink>
      <ArrowLink href={APP_LINKS.register}>Get started</ArrowLink>
    </nav>
  </header>
}

function ProductPreview() {
  const [activeView, setActiveView] = useState<View>('overview')
  const sample = demoData[activeView]
  return <div className="preview-frame">
    <div className="preview-browser" id="interactive-preview">
      <div className="preview-topline"><span className="traffic-lights" aria-hidden="true"><i/><i/><i/></span><span>FINCO / WORKSPACE</span><span className="preview-top-right"><IconLock size={13} stroke={1.6} aria-hidden="true"/> PRIVATE VIEW</span></div>
      <div className="preview-window">
        <aside className="preview-sidebar" aria-label="Illustrative app menu">
          <div className="preview-mini-logo"><FinCoLogo size={19} /></div>
          {[IconChartBar, IconWallet, IconReceipt, IconTarget, IconCalendarStats].map((Icon, index) => <div key={index} className={index === 0 ? 'preview-side-icon active' : 'preview-side-icon'} aria-hidden="true"><Icon size={18} stroke={1.7}/></div>)}
        </aside>
        <div className="preview-main">
          <div className="preview-titlebar"><span>My workspace</span><span className="demo-profile">FC</span></div>
          <div role="tablist" aria-label="Explore sample views" className="preview-tabs">
            {(['overview','budgets','activity'] as View[]).map(view => <Button key={view} role="tab" aria-selected={activeView === view} aria-controls="sample-panel" id={'tab-' + view} onClick={() => setActiveView(view)} variant={activeView===view ? 'secondary' : 'ghost'} size="sm" className={activeView===view ? 'preview-tab active' : 'preview-tab'}>{view === 'overview' ? 'Overview' : view === 'budgets' ? 'Budgets' : 'Activity'}</Button>)}
          </div>
          <div id="sample-panel" role="tabpanel" aria-labelledby={'tab-' + activeView} className="preview-body" key={activeView}>
            <div className="mini-eyebrow">{sample.eyebrow}</div>
            <div className="finance-summary"><div><p>{sample.title}</p><div className="finance-amount">{sample.amount}</div></div><div className="finance-trend"><IconArrowUpRight size={14}/>{sample.delta}</div></div>
            <div className="chart-wrap"><div className="chart-intro"><span>Financial trend</span><span>{sample.detail}</span></div>
              <div className="chart-bars" role="img" aria-label={'Illustrative trend for ' + activeView}>{sample.bars.map((v,i) => <span key={i} style={{height:v+'%'}} className={i===sample.bars.length-1?'bright':''}/>)}</div>
              <div className="chart-axis"><span>Start</span><span>Today</span></div>
            </div>
            <div className="tx-heading">Recent items <span>Sample data</span></div>
            <div className="tx-list">{sample.transactions.map((item,i)=><div className="tx-row" key={i}><div className="tx-symbol">{i===0?<IconArrowDownRight size={16}/>:i===1?<IconReceipt size={16}/>:<IconTarget size={16}/>}</div><div className="tx-description"><strong>{item.name}</strong><span>{item.context}</span></div><span className={item.positive?'tx-value positive':'tx-value'}>{item.amount}</span></div>)}</div>
          </div>
        </div>
      </div>
    </div>
    <div className="float-note"><span className="float-icon"><IconCircleCheck size={19}/></span><div><strong>A clearer perspective</strong><span>Everything in its place.</span></div></div>
    <p className="preview-disclaimer"><IconLock size={13}/> Illustrative interface · No real account data</p>
  </div>
}

function Hero() {
  return <section className="hero-section">
    <div className="hero-ambient" aria-hidden="true"><ProximityGrid cellSize={86} gap={2} proximity={3} interactive={false} /></div>
    <div className="hero-halo" aria-hidden="true"/>
    <div className="shell hero-grid">
      <div className="hero-copy">
        <Badge size="lg" variant="outline" className="eyebrow-badge"><span className="status-dot"/> A better way to understand your money <IconArrowUpRight size={13}/></Badge>
        <BlurRevealText as="h1" className="hero-title" text="Money makes more sense together." stagger={0.045} delay={0.06} duration={0.38} blurAmount="7px" />
        <p className="hero-description">Every account. Every decision. One thoughtful place to understand where your money stands — and where it can go next.</p>
        <div className="hero-actions"><ArrowLink href={APP_LINKS.register}>Make money make sense</ArrowLink><SpaceLink href="#experience" variant="secondary" className="secondary-cta">Explore the experience <IconArrowRight size={18}/></SpaceLink></div>
        <div className="hero-footnote"><span className="verified-icon"><IconCircleCheck size={16}/></span> Built for the decisions you make every day. <span className="hero-footnote-divider"/> No invented promises.</div>
      </div>
      <div className="hero-visual"><ProductPreview /></div>
    </div>
    <div className="hero-bottom shell"><span>LESS GUESSWORK. MORE CLARITY.</span><a href="#why-finco" className="scroll-prompt">Discover more <span aria-hidden="true">↓</span></a></div>
  </section>
}

function ProofLine() {
  return <div className="proof-line shell"><p>One place for more than your balance.</p><div className="proof-items"><span><IconWallet size={18}/> Accounts</span><span><IconReceipt size={18}/> Transactions</span><span><IconTarget size={18}/> Budgets & goals</span><span><IconChartDots3 size={18}/> Reports</span></div></div>
}

function WhyFinCo() {
  return <section className="section why-section shell" id="why-finco">
    <div className="section-head"><div><p className="section-kicker"><span>01 /</span> MADE FOR REAL LIFE</p><h2>Less juggling.<br/><span>More knowing.</span></h2></div><p>Money touches every part of life. Your tools should bring the pieces together, not send you looking for them.</p></div>
    <div className="feature-grid">{featureCards.map((item,index)=><Card key={item.number} className={'feature-card feature-'+index}><div className="feature-card-top"><span className="feature-number">{item.number} / 04</span><span className="feature-icon"><item.icon size={23} stroke={1.5}/></span></div><div className="feature-card-bottom"><p className="feature-label">{item.label}</p><h3>{item.title}</h3><p>{item.body}</p><div className="feature-line"/></div></Card>)}</div>
  </section>
}

function Experience() {
  const [selected, setSelected] = useState<'clarity'|'control'>('clarity')
  return <section className="section experience-section" id="experience">
    <div className="shell experience-grid">
      <div className="experience-copy"><p className="section-kicker"><span>02 /</span> BUILT AROUND YOU</p><h2>For the bigger picture. <em>And the little details.</em></h2><p className="section-intro">It’s not about staring at another chart. It’s about making your next financial decision feel more grounded.</p>
        <div className="experience-choices" role="tablist" aria-label="Choose benefit">
          <Button role="tab" aria-selected={selected==='clarity'} onClick={()=>setSelected('clarity')} variant="ghost" className={selected==='clarity'?'choice active':'choice'}><IconChartBar size={20}/> Understand what changed <IconArrowRight size={18}/></Button>
          <Button role="tab" aria-selected={selected==='control'} onClick={()=>setSelected('control')} variant="ghost" className={selected==='control'?'choice active':'choice'}><IconShieldLock size={20}/> Stay in the driver’s seat <IconArrowRight size={18}/></Button>
        </div>
        <p className="choice-description" aria-live="polite">{selected==='clarity'?'See your spending, savings and activity in a context you can actually use.':'Keep your own financial workflow, workspace and permissions at the centre of the experience.'}</p>
      </div>
      <div className="experience-art">
        <div className="orbit orbit-one"/><div className="orbit orbit-two"/>
        <div className="orbit-center"><IconChartDots3 size={34} stroke={1.25}/></div>
        <div className="orbit-tag orbit-tag-a"><IconWallet size={16}/> What you have</div>
        <div className="orbit-tag orbit-tag-b"><IconTarget size={16}/> What matters</div>
        <div className="orbit-tag orbit-tag-c"><IconChartBar size={16}/> What changed</div>
        <div className="orbit-caption">One financial perspective. Many moving parts.</div>
      </div>
    </div>
  </section>
}

function HowItWorks() {
  return <section className="section steps-section shell" id="how-it-works">
    <div className="section-head"><div><p className="section-kicker"><span>03 /</span> YOUR NEXT STEP</p><h2>A little less noise.<br/><span>A lot more direction.</span></h2></div><p>Start simply. Find your rhythm. Use the features that fit your financial life.</p></div>
    <div className="steps-grid">{steps.map(item=><div key={item.id} className="step-item"><span className="step-index">{item.id}</span><div className="step-icon"><item.icon size={24} stroke={1.45}/></div><h3>{item.title}</h3><p>{item.description}</p></div>)}</div>
  </section>
}

function Privacy() {
  return <section className="section privacy-section"><div className="shell privacy-panel">
    <div className="privacy-copy"><div className="privacy-kicker"><IconShieldLock size={18}/> THE TRUST PART</div><h2>Financial clarity should feel <em>personal.</em></h2><p>Your financial information deserves thoughtful access controls. FinCo-Pilot includes workspace permissions, authentication safeguards and configurable provider connections.</p><SpaceLink href={APP_LINKS.privacy} variant="secondary" className="privacy-link">Read the privacy policy <IconArrowUpRight size={18}/></SpaceLink></div>
    <div className="privacy-visual"><div className="privacy-avatar"><IdentityAvatar seed="fincopilot-friendly-guide" size={100}/></div><div className="privacy-pill"><IconLock size={16}/> Your workspace. Your context.</div><span className="privacy-note">No real user data on this page</span></div>
  </div></section>
}

function Questions() {
  return <section className="section faq-section shell" id="questions"><div className="faq-copy"><p className="section-kicker"><span>04 /</span> GOOD TO KNOW</p><h2>Questions?<br/><span>Fair enough.</span></h2><p>Clear answers matter as much as a clear dashboard.</p><SpaceLink href={APP_LINKS.support} variant="secondary" className="faq-contact">Support options <IconArrowUpRight size={17}/></SpaceLink></div>
    <Accordion className="faq-list" defaultValue={['faq-1']} multiple={true}>
      {faqs.map(item=><AccordionItem value={item.id} key={item.id} className="faq-item"><AccordionTrigger className="faq-trigger">{item.question}</AccordionTrigger><AccordionPanel className="faq-panel">{item.answer}</AccordionPanel></AccordionItem>)}
    </Accordion>
  </section>
}

function FinalCTA() {
  return <section className="section final-section"><div className="shell final-inner"><p className="final-kicker">A MORE THOUGHTFUL WAY FORWARD</p><h2>Put your money<br/>into <span>perspective.</span></h2><p>Clarity is a good place to start.</p><ArrowLink href={APP_LINKS.register} light>Go to FinCo-Pilot <IconArrowRight size={18}/></ArrowLink><span className="final-small">Sign-up availability depends on the live application.</span></div></section>
}

function Footer() {
  return <footer className="footer"><div className="shell"><div className="footer-top"><div><a href="#top" className="brand-link"><Mark compact/></a><p>More clarity. Less guesswork.</p></div><div className="footer-links"><SpaceLink href="#why-finco" variant="secondary">Features</SpaceLink><SpaceLink href={APP_LINKS.pricing} variant="secondary">Pricing</SpaceLink><SpaceLink href={APP_LINKS.support} variant="secondary">Support</SpaceLink><SpaceLink href={APP_LINKS.login} variant="secondary">Log in</SpaceLink></div></div><div className="footer-bottom"><span>© 2026 FinCo-Pilot</span><div><SpaceLink href={APP_LINKS.privacy} variant="secondary">Privacy</SpaceLink><SpaceLink href={APP_LINKS.terms} variant="secondary">Terms</SpaceLink></div><span>Designed with intention. Built with Space UI.</span></div></div></footer>
}

export function LandingExperience() {
  return <MotionConfig reducedMotion="user"><div className="marketing-page"><a className="skip-link" href="#main-content">Skip to content</a><Navigation/><main id="main-content"><Hero/><ProofLine/><WhyFinCo/><Experience/><HowItWorks/><Privacy/><Questions/><FinalCTA/></main><Footer/></div></MotionConfig>
}
