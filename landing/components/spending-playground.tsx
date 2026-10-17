'use client'
import { useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Chip,
  Label,
  NumberField,
  Popover,
  Slider,
  ToggleButton,
  ToggleButtonGroup,
} from '@heroui/react'
import { ArrowDown, Info, RotateCcw } from 'lucide-react'
import {
  SAMPLE_CASH,
  spendingRemainder,
  spendingScenarios,
  formatMoney,
} from '@/lib/spending-example'

function ReserveField({
  label,
  value,
  onChange,
  hint,
}: {
  label: string
  value: number
  onChange: (value: number) => void
  hint: string
}) {
  return (
    <div className="reserve-field">
      <NumberField
        value={value}
        onChange={(value) => onChange(value ?? NaN)}
        minValue={0}
        maxValue={SAMPLE_CASH}
        step={1000}
        formatOptions={{
          style: 'currency',
          currency: 'INR',
          maximumFractionDigits: 0,
        }}
        className="buffer-input"
      >
        <Label>{label}</Label>
        <NumberField.Group>
          <NumberField.DecrementButton
            aria-label={'Decrease ' + label.toLowerCase()}
          />
          <NumberField.Input />
          <NumberField.IncrementButton
            aria-label={'Increase ' + label.toLowerCase()}
          />
        </NumberField.Group>
      </NumberField>
      <Slider
        aria-label={label + ' slider'}
        value={Number.isFinite(value) ? value : 0}
        onChange={(next) => onChange(Array.isArray(next) ? next[0] : next)}
        minValue={0}
        maxValue={SAMPLE_CASH}
        step={1000}
        formatOptions={{
          style: 'currency',
          currency: 'INR',
          maximumFractionDigits: 0,
        }}
      >
        <Slider.Track>
          <Slider.Fill />
          <Slider.Thumb />
        </Slider.Track>
      </Slider>
      <p className="field-hint">{hint}</p>
    </div>
  )
}
export function SpendingPlayground() {
  const [bills, setBills] = useState<number>(22000)
  const [buffer, setBuffer] = useState<number>(10000)
  const [goal, setGoal] = useState<number>(5000)
  const [scenario, setScenario] = useState<string>('balanced')
  const remainder = spendingRemainder(bills, buffer, goal)
  function selectScenario(id: string) {
    const value = spendingScenarios.find((item) => item.id === id)
    if (!value) return
    setScenario(id)
    setBills(value.bills)
    setBuffer(value.buffer)
    setGoal(value.goal)
  }
  const update = (setValue: (value: number) => void) => (value: number) => {
    setScenario('')
    setValue(value)
  }
  return (
    <Card className="planning-demo">
      <Card.Header>
        <div className="demo-topline">
          <Chip size="sm" variant="soft">
            YOUR TURN
          </Chip>
          <Button
            variant="tertiary"
            size="sm"
            onPress={() => selectScenario('balanced')}
            aria-label="Reset spending example"
          >
            <RotateCcw size={14} aria-hidden="true" />
            Reset
          </Button>
        </div>
        <Card.Title>Give every rupee a little context.</Card.Title>
        <Card.Description>
          Try a sample month. All changes stay on this page.
        </Card.Description>
      </Card.Header>
      <Card.Content>
        <ToggleButtonGroup
          aria-label="Sample month scenarios"
          selectionMode="single"
          selectedKeys={scenario ? [scenario] : []}
          onSelectionChange={(keys) => {
            const id = keys.values().next().value
            if (typeof id === 'string') selectScenario(id)
          }}
          isDetached
          className="scenario-picker"
        >
          {spendingScenarios.map((item) => (
            <ToggleButton id={item.id} key={item.id}>
              {item.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
        <div className="sample-cash">
          <span>Sample cash balance</span>
          <strong>{formatMoney(SAMPLE_CASH)}</strong>
        </div>
        <div className="reserve-fields">
          <ReserveField
            label="Bills and EMI to set aside"
            value={bills}
            onChange={update(setBills)}
            hint="Upcoming commitments in this simplified month."
          />
          <ReserveField
            label="Emergency buffer to protect"
            value={buffer}
            onChange={update(setBuffer)}
            hint="A reserve you choose to leave untouched."
          />
          <ReserveField
            label="Savings goal reserve"
            value={goal}
            onChange={update(setGoal)}
            hint="Money with a longer-term purpose."
          />
        </div>
        <div
          className={
            'example-result' +
            (remainder !== null && remainder < 0 ? ' result-shortfall' : '')
          }
          aria-live="polite"
          aria-atomic="true"
        >
          {remainder === null ? (
            <p>
              {!Number.isFinite(buffer)
                ? 'Enter a buffer to see the example.'
                : 'Complete each amount to see the example.'}
            </p>
          ) : (
            <>
              <div className="result-caption">
                <span>
                  {remainder < 0
                    ? 'Illustrative shortfall'
                    : 'Illustrative remainder'}
                </span>
                <ArrowDown size={18} aria-hidden="true" />
              </div>
              <strong className="amount-change" key={remainder}>
                {formatMoney(Math.abs(remainder))}
              </strong>
              <p>
                {remainder < 0
                  ? 'These sample commitments exceed the sample balance.'
                  : 'After the sample bills, goal reserve and your chosen buffer.'}
              </p>
            </>
          )}
        </div>
        <Popover>
          <Button variant="tertiary" size="sm" className="calculation-help">
            <Info size={16} aria-hidden="true" />
            What is included in this example?
          </Button>
          <Popover.Content placement="top" className="calculation-popover">
            <Popover.Arrow />
            <Popover.Dialog>
              <Popover.Heading>
                Three reserves. One sample balance.
              </Popover.Heading>
              <p>
                ₹62,000 cash − bills and EMI − emergency buffer − savings goal
                reserve.
              </p>
              <p>
                This illustration excludes separate card debt, timing, interest
                and missing records. The application's spending plan checks
                additional inputs and can withhold an estimate.
              </p>
            </Popover.Dialog>
          </Popover.Content>
        </Popover>
      </Card.Content>
      <Card.Footer>
        <Alert status="default">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Title>Example only</Alert.Title>
            <Alert.Description>
              Synthetic numbers, simplified arithmetic and no connected account.
              This is not a spending recommendation.
            </Alert.Description>
          </Alert.Content>
        </Alert>
      </Card.Footer>
    </Card>
  )
}
