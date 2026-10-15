'use client'

import { landingAsset } from '@/lib/asset'

import { IconChartBar, IconWallet } from '@tabler/icons-react'
import { Card } from '@/components/spaceui/card'
import { Tabs, TabsList, TabsTab, TabsPanel } from '@/components/spaceui/tabs'
import { Animoji } from '@/components/spaceui/animoji'
import { useLandingSound } from '@/components/landing-sound'

const screens = [
  { id: 'dashboard', title: 'Dashboard', icon: IconChartBar, description: 'See available balances, income and expenses together. Review the month before making your next decision.', alt: 'Original FinCo-Pilot dashboard with two synthetic accounts and sample monthly activity.' },
  { id: 'accounts', title: 'Accounts', icon: IconWallet, description: 'Keep everyday and savings accounts organised in one workspace. These examples are manually managed accounts.', alt: 'Original FinCo-Pilot Accounts screen showing synthetic everyday and savings accounts.' },
]

export function ProductScreens() {
  const { cue } = useLandingSound()
  return <section className="section product-section shell" id="experience">
    <div className="section-head"><div><p className="section-kicker">INSIDE YOUR WORKSPACE <Animoji className="product-heading-emoji" localAssets>{'🧭'}</Animoji></p><h2>The details.<br/><span>In their own place.</span></h2></div><p>A closer look at the FinCo-Pilot interface, captured from the actual application with sample data.</p></div>
    <Tabs defaultValue="dashboard" className="product-tabs" onValueChange={() => cue()}>
      <TabsList activateOnFocus aria-label="Explore FinCo-Pilot screens" className="product-tabs-list">
        {screens.map(screen => <TabsTab value={screen.id} key={screen.id} className="product-tab"><screen.icon aria-hidden="true"/>{screen.title}</TabsTab>)}
      </TabsList>
      {screens.map(screen => <TabsPanel value={screen.id} key={screen.id}>
        <Card className="product-capture"><picture><source media="(max-width:620px)" srcSet={landingAsset('/product/' + screen.id + '-mobile.webp')} /><img src={landingAsset('/product/' + screen.id + '-desktop.webp')} width={1440} height={920} loading="lazy" decoding="async" alt={screen.alt} /></picture></Card>
        <div className="product-caption"><p>{screen.description}</p><p className="capture-note">Actual application screens · Synthetic sample data · Screenshots, not live accounts</p></div>
      </TabsPanel>)}
    </Tabs>
  </section>
}
