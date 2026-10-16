# Payment Methods

## Overview

The API supports a growing set of payment method types. All methods go through the same
`POST /v2/payments` endpoint; the `source` field determines which method is charged.

## Credit and Debit Cards

Cards are the primary payment method. To collect card details without storing them on
your servers, use the JavaScript SDK to tokenise the card client-side:

```javascript
const { token, error } = await payments.tokenize({
  card: {
    number: document.getElementById("card-number").value,
    exp_month: 12,
    exp_year: 2026,
    cvc: "123",
  }
});
// token.id = "card_tok_XXXX"
```

Pass `token.id` as the `source` in your server-side create payment call. The token is
single-use and expires after 15 minutes.

### Storing Cards for Future Use

To store a card for future charges (subscriptions, one-click checkout):

```python
pm = client.payment_methods.create(
    type="card",
    customer_id="cus_ABC123",
    token="card_tok_XXXX",
)
# pm.id = "pm_CARD123" — reusable
```

Stored cards can be listed (`GET /v2/customers/{id}/payment-methods`), updated
(billing address, expiry month), and deleted (`DELETE /v2/payment-methods/{id}`).

### Card Network Tokens

For customers on Visa, Mastercard, and Amex, the platform automatically upgrades stored
cards to network tokens (DPAN). Network tokens follow the card when it is replaced due
to expiry or loss, dramatically reducing soft declines. No action is required from you.

## Bank Debits (ACH / SEPA)

### ACH (US Bank Accounts)

```python
pm = client.payment_methods.create(
    type="ach_debit",
    customer_id="cus_ABC123",
    billing_details={ "name": "Jane Smith" },
    ach_debit={
        "account_number": "000123456789",
        "routing_number": "110000000",
        "account_type": "checking",
    }
)
```

ACH debits take 3–5 business days to settle. The payment is immediately `processing`;
a `payment.succeeded` event fires when the debit clears. ACH failures (e.g. NSF) arrive
up to 4 business days after initiation via `payment.failed`.

**Micro-deposit verification**: new bank accounts must be verified before use. The platform
deposits two small amounts within 1–2 business days. The customer enters these amounts
in your UI:

```python
client.payment_methods.verify_microdeposits(
    pm_id,
    amounts=[32, 45],
)
```

Alternatively, use Instant Account Verification (IAV) via the JavaScript SDK to connect
the account through Open Banking, bypassing micro-deposit delays.

### SEPA Direct Debit (EU)

Same flow as ACH but `type="sepa_debit"` and `iban` replaces account/routing numbers.
SEPA mandates require customer consent; the SDK's mandate collection flow handles the
legal UX requirements automatically.

## Digital Wallets

### Apple Pay

1. Register your domain with Apple: `POST /v2/apple-pay/domains` (serves the verification file).
2. Client-side: call `ApplePaySession.requestPayment()` via the SDK.
3. Server-side: pass the payment token as `source`.

Apple Pay transactions include 3D Secure by default and typically have higher authorisation
rates than manually-entered cards.

### Google Pay

1. Configure Google Pay via the dashboard (no domain registration needed).
2. Client-side: call the Google Pay API; pass the resulting `paymentData` to `payments.tokenize()`.
3. Server-side: use the resulting token as `source`.

### Link (One-Click Checkout)

Customers who have previously paid anywhere on the platform can pay with a single click
using their stored details. Enable via the JavaScript SDK by setting `enableLink: true`.
No additional server-side integration is required.

## Buy Now Pay Later (BNPL)

Supported providers: Klarna, Afterpay/Clearpay, Affirm. Integration follows the same
create-payment flow with `source: "bnpl_{provider}"`. The provider handles the
instalment plan; you receive the full amount immediately.

BNPL refunds are handled via `POST /v2/refunds` as normal; the provider manages the
impact on the customer's instalment schedule.

## Payment Method Limits

| Method | Min Amount | Max Amount | Settlement |
|--------|-----------|-----------|-----------|
| Card | $0.50 | $999,999.99 | 1–2 business days |
| ACH Debit | $1.00 | $500,000 | 3–5 business days |
| SEPA Debit | €0.01 | €500,000 | 2–3 business days |
| Apple Pay | $0.50 | $10,000 | 1–2 business days |
| Google Pay | $0.50 | $10,000 | 1–2 business days |
| Klarna | $10 | $5,000 | 1–2 business days |

## Declining Payment Methods

To stop accepting a stored payment method without deleting it:

**PATCH** `/v2/payment-methods/{id}`

```json
{ "active": false }
```

Inactive payment methods cannot be used in new charges but existing subscriptions will
fail on the next renewal and move to dunning.
