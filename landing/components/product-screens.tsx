'use client'

import { Tabs, Chip } from '@heroui/react'
import { LayoutDashboard, Landmark } from 'lucide-react'
import { landingAsset } from '@/lib/asset'

const screens = [
  {
    id: 'dashboard',
    title: 'Dashboard',
    icon: <LayoutDashboard aria-hidden="true" />,
    description:
      'Balances, income, expenses and category activity. Review the month with your accounts in context.',
    alt: 'Original FinCo-Pilot dashboard with two synthetic accounts and sample monthly activity.',
  },
  {
    id: 'accounts',
    title: 'Accounts',
    icon: <Landmark aria-hidden="true" />,
    description:
      'Keep everyday and savings accounts organised in one workspace. These examples are manually managed accounts.',
    alt: 'Original FinCo-Pilot Accounts screen showing synthetic everyday and savings accounts.',
  },
]

export function ProductScreens() {
  return (
    <section
      className="section shell"
      id="experience"
      aria-labelledby="product-title"
    >
      <div className="section-head">
        <div>
          <p className="section-kicker">TAKE A LOOK AROUND</p>
          <h2 id="product-title">
            Your money.
            <br />
            One working picture.
          </h2>
        </div>
        <p>
          The actual application, with sample records. Take a closer look before
          you create an account.
        </p>
      </div>
      <Tabs defaultSelectedKey="dashboard" className="product-tabs">
        <div className="product-toolbar">
          <Tabs.ListContainer>
            <Tabs.List aria-label="Explore FinCo-Pilot screens">
              {screens.map((screen) => (
                <Tabs.Tab id={screen.id} key={screen.id}>
                  {screen.icon}
                  {screen.title}
                  <Tabs.Indicator />
                </Tabs.Tab>
              ))}
            </Tabs.List>
          </Tabs.ListContainer>
          <Chip size="sm" variant="soft">
            Actual application · Sample data
          </Chip>
        </div>
        {screens.map((screen) => (
          <Tabs.Panel id={screen.id} key={screen.id}>
            <>
              <div className="product-capture">
                <picture>
                  <source
                    media="(max-width:620px)"
                    srcSet={landingAsset(
                      '/product/' + screen.id + '-mobile.webp',
                    )}
                  />
                  <img
                    src={landingAsset(
                      '/product/' + screen.id + '-desktop.webp',
                    )}
                    width={1440}
                    height={920}
                    loading="lazy"
                    decoding="async"
                    alt={screen.alt}
                  />
                </picture>
              </div>
              <div className="product-caption">
                <p>{screen.description}</p>
                <p className="capture-note">
                  Actual application screens · Synthetic sample data ·
                  Screenshots, not live accounts
                </p>
              </div>
            </>
          </Tabs.Panel>
        ))}
      </Tabs>
    </section>
  )
}
