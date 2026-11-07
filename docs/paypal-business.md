# Harbor PayPal Business

1. Open [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/applications) → create a **Business** REST app (sandbox first).
2. Copy **Client ID** + **Secret** into `shop/.env`:

```
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
PAYPAL_ENV=sandbox
```

3. Live: set `PAYPAL_ENV=live` and use Live credentials.
4. Optional webhook (recommended): add `https://linkiip.com/paypal/webhook` with events `CHECKOUT.ORDER.APPROVED`, `PAYMENT.CAPTURE.COMPLETED`; put the webhook id in `PAYPAL_WEBHOOK_ID`.
5. Restart shop: `uvicorn shop.app:app` (from `D:\1010`, with venv). Checkout defaults to PayPal and redirects to PayPal approve; return hits `/orders/{id}/paypal` and captures.

Priority: PayPal env → LianLian → Stripe → MemoryStripe (no real charge).
