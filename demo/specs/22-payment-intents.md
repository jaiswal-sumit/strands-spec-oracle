# Payment Intents

## Overview

A `PaymentIntent` is the recommended approach for building checkout flows. Unlike a direct
`POST /v2/payments`, a PaymentIntent is a stateful object that tracks the entire lifecycle
of a payment attempt — from intent creation through authentication, capture, and fulfilment.
Use Payment Intents when:

- You need 3D Secure support
- You accept multiple payment methods and want a unified flow
- You need to separate authorisation from capture
- Your checkout spans multiple pages or sessions

## States

```
created
  → requires_payment_method   (no source yet)
  → requires_confirmation      (source attached, needs confirm)
  → requires_action            (3DS challenge required)
  → processing                 (submitted to network)
  → requires_capture           (authorized; not yet captured)
  → succeeded                  (captured)
  → cancelled
```

## Creating a Payment Intent

**POST** `/v2/payment-intents`

```python
intent = client.payment_intents.create(
    amount=4900,
    currency="USD",
    payment_method_types=["card", "apple_pay"],
    capture_method="automatic",   # or "manual" for auth+capture flows
    metadata={"order_id": "ord_001"},
)
# intent.client_secret — pass to the client-side SDK
```

`client_secret` is a time-limited token for client-side operations. Never log it and
do not expose it to other users. It is scoped to this intent only.

## Confirming Client-Side

```javascript
const { paymentIntent, error } = await payments.confirmPayment({
  clientSecret: intent.client_secret,
  payment_method: {
    card: cardElement,
    billing_details: { name: "Jane Smith" },
  },
  return_url: "https://yoursite.com/payment/complete",
});
```

The SDK handles 3DS automatically. On success `paymentIntent.status === "succeeded"`.

## Server-Side Confirmation

For flows where card data is collected server-side (requires PCI compliance):

```python
intent = client.payment_intents.confirm(
    intent.id,
    payment_method="pm_CARD123",
    return_url="https://yoursite.com/payment/complete",
)
```

## Manual Capture (Auth + Capture)

Set `capture_method="manual"` to authorise funds without capturing:

```python
intent = client.payment_intents.create(
    amount=10000,
    currency="USD",
    capture_method="manual",
)
```

The intent moves to `requires_capture` after confirmation. Funds are reserved on the
card for 7 days (Visa/Mastercard/Discover) or 2 days (Amex).

Capture the full or partial amount:

```python
client.payment_intents.capture(
    intent.id,
    amount_to_capture=8000,   # partial capture; authorisation for remaining 2000 is released
)
```

Cancel the authorisation without charging: `client.payment_intents.cancel(intent.id)`.

## Updating a Payment Intent

You can update `amount`, `currency`, `metadata`, and `payment_method_types` before
confirmation:

```python
client.payment_intents.update(intent.id, amount=5500)
```

After confirmation, only `metadata` may be updated.

## Retrieving a Payment Intent

After the customer returns from `return_url`, retrieve the intent to confirm success:

```python
intent = client.payment_intents.retrieve(request.args["payment_intent"])
if intent.status == "succeeded":
    fulfill_order(intent.metadata["order_id"])
```

Do not rely solely on the `return_url` callback to confirm success — the customer could
have closed the tab or the callback URL could have failed. Always verify via the API.

## Webhook Events

| Event | When Fired |
|-------|-----------|
| `payment_intent.created` | Intent created |
| `payment_intent.succeeded` | Payment completed |
| `payment_intent.payment_failed` | Confirmation or capture failed |
| `payment_intent.requires_action` | 3DS challenge triggered |
| `payment_intent.cancelled` | Intent cancelled |
| `payment_intent.amount_capturable_updated` | Amount changed before capture |
