'use client'
import { useState } from 'react'
import { Button, Card, Chip, Disclosure, Link, Table, Tabs } from '@heroui/react'
import { ArrowRight, Check, Download, FileText } from 'lucide-react'
import { landingAsset } from '@/lib/asset'
const steps = [
  { id: 'file', title: '1. Choose a file' },
  { id: 'mapping', title: '2. Check the mapping' },
  { id: 'review', title: '3. Review the proposal' },
]
export function ImportWalkthrough() {
  const [step, setStep] = useState('file')
  return (
    <Card className="import-callout" id="import-walkthrough">
      <Card.Content>
        <div className="import-copy">
          <Chip size="sm" variant="soft">
            BRING YOUR RECORDS WITH YOU
          </Chip>
          <h3>
            A fresh start.
            <br />
            With your history.
          </h3>
          <p>
            See how a tiny synthetic CSV becomes a proposal to review. This
            guided illustration never uploads a file or changes records.
          </p>
          <Link
            href={landingAsset('/guides/import-transactions/')}
            className="button button--secondary"
          >
            Read the import guide
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
          <Link
            href={landingAsset('/samples/transactions-example.csv')}
            download
            className="sample-download"
          >
            <Download size={16} aria-hidden="true" />
            Download the sample CSV
          </Link>
        </div>
        <Tabs
          selectedKey={step}
          onSelectionChange={(key) => setStep(String(key))}
          className="import-wizard"
        >
          <Tabs.ListContainer>
            <Tabs.List aria-label="Sample import walkthrough">
              {steps.map((item) => (
                <Tabs.Tab key={item.id} id={item.id}>
                  {item.title}
                  <Tabs.Indicator />
                </Tabs.Tab>
              ))}
            </Tabs.List>
          </Tabs.ListContainer>
          <Tabs.Panel id="file">
            <div className="specimen-file">
              <span className="file-icon">
                <FileText aria-hidden="true" />
              </span>
              <strong>transactions-example.csv</strong>
              <p>2 synthetic records · INR · CSV</p>
              <pre tabIndex={0} role="region" aria-label="Synthetic CSV sample">
                date,description,amount,currency{'\n'}2026-10-01,Synthetic
                grocery,-250.00,INR{'\n'}2026-10-02,Synthetic income,1000.00,INR
              </pre>
            </div>
            <Button variant="secondary" onPress={() => setStep('mapping')}>
              Inspect the mapping
              <ArrowRight size={15} aria-hidden="true" />
            </Button>
          </Tabs.Panel>
          <Tabs.Panel id="mapping">
            <p className="wizard-intro">
              Match the meaning before applying a file.
            </p>
            <dl className="mapping-rows">
              {[
                ['date', 'Transaction date'],
                ['description', 'Description'],
                ['amount', 'Signed amount'],
                ['currency', 'Currency code'],
              ].map(([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>
                    <ArrowRight size={14} aria-hidden="true" />
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
            <p className="capture-note">
              Destination account, date interpretation and duplicate handling
              also need review in the application.
            </p>
            <Button variant="secondary" onPress={() => setStep('review')}>
              Review sample rows
              <ArrowRight size={15} aria-hidden="true" />
            </Button>
          </Tabs.Panel>
          <Tabs.Panel id="review">
            <div className="review-heading">
              <Chip size="sm" variant="soft">
                <Check size={13} aria-hidden="true" />
                Illustrative preview
              </Chip>
              <span>2 rows</span>
            </div>
            <Table>
              <Table.ScrollContainer>
                <Table.Content aria-label="Synthetic transaction import preview">
                  <Table.Header>
                    <Table.Column isRowHeader>Description</Table.Column>
                    <Table.Column>Amount</Table.Column>
                  </Table.Header>
                  <Table.Body>
                    <Table.Row>
                      <Table.Cell>Synthetic grocery</Table.Cell>
                      <Table.Cell>−₹250</Table.Cell>
                    </Table.Row>
                    <Table.Row>
                      <Table.Cell>Synthetic income</Table.Cell>
                      <Table.Cell>+₹1,000</Table.Cell>
                    </Table.Row>
                  </Table.Body>
                </Table.Content>
              </Table.ScrollContainer>
            </Table>
            <div className="import-net">
              <span>Net sample flow</span>
              <strong>₹750</strong>
            </div>
            <p className="capture-note">
              Net flow is not an account balance. In the app, review excluded
              rows and duplicates before confirming. Nothing is submitted here.
            </p>
            <Button variant="tertiary" onPress={() => setStep('file')}>
              Back to the sample file
            </Button>
          </Tabs.Panel>
        </Tabs>
        <Disclosure className="detail-disclosure import-checklist">
          <Disclosure.Heading>
            <Disclosure.Trigger>
              What should I check before confirming an import?
              <Disclosure.Indicator />
            </Disclosure.Trigger>
          </Disclosure.Heading>
          <Disclosure.Content>
            <ul className="detail-checks">
              <li>Destination: confirm the account type, account and currency.</li>
              <li>Dates: verify the day/month interpretation against your source.</li>
              <li>Amounts: check positive income and negative expenses where expected.</li>
              <li>Currency: a currency label does not perform a conversion.</li>
              <li>Duplicates: inspect proposed, skipped and failed rows against the source.</li>
            </ul>
            <p>Some QIF reference tags are not retained as unique transaction IDs. This synthetic example never submits records.</p>
          </Disclosure.Content>
        </Disclosure>
      </Card.Content>
    </Card>
  )
}
