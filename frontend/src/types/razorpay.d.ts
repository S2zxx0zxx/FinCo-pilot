/**
 * Razorpay Standard Checkout – TypeScript type declarations.
 *
 * These cover the browser-side Razorpay SDK (checkout.js) surface used by
 * FinCo-Pilot. Extend as new features are integrated.
 *
 * KEY_SECRET must never appear here or anywhere in frontend code.
 * Only KEY_ID (public, safe) may be referenced.
 */

export interface RazorpaySuccessResponse {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
}

export interface RazorpayFailedResponse {
  error: {
    code: string;
    description: string;
    source: string;
    step: string;
    reason: string;
    metadata: {
      order_id: string;
      payment_id: string;
    };
  };
}

export interface RazorpayModalOptions {
  ondismiss?: () => void;
}

export interface RazorpayCheckoutOptions {
  /** Public KEY_ID only — never KEY_SECRET. */
  key: string;
  amount: number;
  currency: string;
  name: string;
  description?: string;
  order_id: string;
  handler: (response: RazorpaySuccessResponse) => void;
  modal?: RazorpayModalOptions;
  theme?: { color?: string };
  prefill?: {
    name?: string;
    email?: string;
    contact?: string;
  };
}

export interface RazorpayInstance {
  open(): void;
  on(event: 'payment.failed', handler: (response: RazorpayFailedResponse) => void): void;
}

export interface RazorpayConstructor {
  new (options: RazorpayCheckoutOptions): RazorpayInstance;
}

declare global {
  interface Window {
    Razorpay?: RazorpayConstructor;
  }
}
