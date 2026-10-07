import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { act, screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import { FALLBACK_PRICING } from '@/billing/catalog'
import PricingPage from './pricing'
import type { RazorpayCheckoutOptions, RazorpayConstructor } from '@/types/razorpay'
const mocks = vi.hoisted(() => ({ refresh: vi.fn(), error: vi.fn(), info: vi.fn(), success: vi.fn() }))
vi.mock('@/contexts/auth-context', () => ({useAuth:()=>({user:{id:'synthetic-user'}, token:'synthetic-token'})}))
vi.mock('@/contexts/billing-context', () => ({useBilling:()=>({catalog:FALLBACK_PRICING, founderCampaign:null, refreshFounderCampaign:mocks.refresh,plan:'free',isLoading:false})}))
vi.mock('@/lib/razorpay-sdk', () => ({ensureRazorpaySdk:()=>Promise.resolve()}))
vi.mock('sonner', () => ({toast:{error:mocks.error,info:mocks.info,success:mocks.success}}))
let options: RazorpayCheckoutOptions
let opens: number
const quote = {key_id:'rzp_test_server', order_id:'order_Synthetic123',amount:9900,currency:'INR',plan:'pro',interval:'monthly',reservation_id:'01234567-89ab-cdef-0123-456789abcdef',reservation_expires_at:new Date(Date.now()+600000).toISOString(),service_period_days:60,renewal_amount_minor:9900}
beforeEach(()=>{
  vi.clearAllMocks();opens=0
  window.Razorpay = class {constructor(value:RazorpayCheckoutOptions){options=value}open(){opens++}on(){}} as unknown as RazorpayConstructor
})
afterEach(()=>{vi.unstubAllGlobals();delete window.Razorpay})
async function start(response=quote){
  const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify(response),{status:200}))
  vi.stubGlobal('fetch',(url: string, init?: RequestInit) => (url === '/api/billing/cancellation' || url === '/api/billing/refunds')
    ? Promise.resolve(new Response(JSON.stringify({ available: false }), { status: 200 }))
    : fetcher(url, init))
  const {user}=renderWithProviders(<PricingPage/>,{route:'/pricing?plan=pro'})
  await user.click(screen.getByRole('button',{name:'Continue with Pro'}))
  return {user,fetcher}
}
it('uses server key and keeps one modal open across repeated clicks',async()=>{
  const {user,fetcher}=await start()
  expect(options.key).toBe('rzp_test_server');expect(options.retry).toEqual({enabled:false});expect(opens).toBe(1)
  await user.click(screen.getByRole('button',{name:'Continue with Pro'}))
  expect(opens).toBe(1);expect(fetcher).toHaveBeenCalledTimes(1)
})
it('does not open an invalid foreign plan order',async()=>{
  await start({...quote,plan:'max'})
  expect(opens).toBe(0);expect(mocks.error).toHaveBeenCalledWith(expect.stringContaining('could not be validated'))
})
it('does not claim release when cancellation returns a conflict',async()=>{
  const {fetcher}=await start()
  fetcher.mockResolvedValueOnce(new Response('{}',{status:409}))
  await act(async()=>{options.modal?.ondismiss?.()})
  await waitFor(()=>expect(mocks.info).toHaveBeenCalledWith(expect.stringContaining('pending reconciliation')))
  expect(mocks.refresh).not.toHaveBeenCalled()
})
it('never sends cancellation after success callback has begun',async()=>{
  const {fetcher}=await start()
  let resolve!: (v:Response)=>void
  fetcher.mockReturnValueOnce(new Promise<Response>(done=>{resolve=done}))
  let verification!:Promise<void>|void
  await act(async()=>{verification=options.handler({razorpay_order_id:quote.order_id,razorpay_payment_id:'pay_Synthetic123',razorpay_signature:'0'.repeat(64)});options.modal?.ondismiss?.()})
  expect(fetcher.mock.calls.map(call=>call[0])).toEqual(['/api/checkout/create-order','/api/checkout/verify-payment'])
  await act(async()=>{resolve(new Response('{}',{status:200}));await verification})
  expect(mocks.success).toHaveBeenCalledWith(expect.stringContaining('Activation is pending'))
})
