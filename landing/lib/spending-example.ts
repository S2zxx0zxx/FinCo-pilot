export const SAMPLE_CASH = 62000
export const spendingScenarios = [
  {
    id: 'balanced',
    label: 'Everyday month',
    bills: 22000,
    buffer: 10000,
    goal: 5000,
  },
  {
    id: 'bills-heavy',
    label: 'Bills-heavy month',
    bills: 38000,
    buffer: 10000,
    goal: 5000,
  },
  {
    id: 'goal-focused',
    label: 'Bigger savings goal',
    bills: 22000,
    buffer: 10000,
    goal: 20000,
  },
] as const
export function spendingRemainder(bills: number, buffer: number, goal: number) {
  const values = [bills, buffer, goal]
  if (
    values.some(
      (value) => !Number.isFinite(value) || value < 0 || value > SAMPLE_CASH,
    )
  )
    return null
  return SAMPLE_CASH - bills - buffer - goal
}
export const formatMoney = (value: number) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value)
