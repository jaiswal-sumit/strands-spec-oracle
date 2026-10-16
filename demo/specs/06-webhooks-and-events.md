# Webhooks and Events

## Overview

The Payments Service emits webhooks for all significant state transitions. Webhooks are
HTTP POST requests sent to your registered endpoint within 30 seconds of the event occurring.
Each event is delivered at least once (at-least-once semantics); design your endpoint to be
idempotent using the `event_id` field.

## Registering a Webhook Endpoint

**POST** `/v2/webhooks`

```json
{
  "url": "https://your-service.example.com/hooks/payments",
  "events": ["payment.succeeded", "payment.failed", "refund.created"],
  "secret": "whsec_your_signing_secret",
  "active": true,
  "metadata": { "env": "production" }
}
```

- `url`: must be HTTPS. HTTP endpoints are rejected with `400 Bad Request`.
- `events`: array of event types to subscribe to. Use `["*"]` to subscribe to all events.
- `secret`: used to compute HMAC-SHA256 signatures. Must be 32–128 characters.
- Maximum 20 webhook endpoints per account.

Response `201 Created` includes the webhook `id`, which is required for updates and deletion.

## Event Payload Structure

All events share the same envelope:

```json
{
  "event_id":   "evt_01J8X3K9F0ABC",
  "event_type": "payment.succeeded",
  "api_version": "2024-01-01",
  "created_at": "2024-09-15T10:30:00Z",
  "livemode":   true,
  "data": {
    "object": { ... }
  },
  "previous_attributes": { ... }
}
```

- `event_id`: globally unique, stable. Use this for deduplication.
- `previous_attributes`: only present for update events (`payment.updated`, `refund.updated`).
  Contains only the fields that changed, with their previous values.

## Event Types

### Payment Events

| Event | Trigger |
|-------|---------|
| `payment.created` | A new payment intent is created |
| `payment.succeeded` | Payment is fully captured and settled |
| `payment.failed` | Capture fails (insufficient funds, card declined, etc.) |
| `payment.cancelled` | Payment is cancelled before capture |
| `payment.updated` | Any mutable field changes (metadata, description) |
| `payment.dispute_opened` | Cardholder files a chargeback |
| `payment.dispute_closed` | Dispute is resolved (won or lost) |

### Refund Events

| Event | Trigger |
|-------|---------|
| `refund.created` | Refund is initiated |
| `refund.succeeded` | Funds returned to cardholder |
| `refund.failed` | Refund processing error |

### Subscription Events

| Event | Trigger |
|-------|---------|
| `subscription.created` | New subscription started |
| `subscription.renewed` | Billing cycle completes successfully |
| `subscription.payment_failed` | Renewal payment fails |
| `subscription.cancelled` | Subscription ends (immediately or at period end) |
| `subscription.trial_ending` | 3 days before trial expiration |

## Signature Verification

Every webhook request includes the `Stripe-Signature` header:

```
Stripe-Signature: t=1726394200,v1=a5d3f8...
```

To verify:

1. Extract `t` (timestamp) and `v1` (HMAC) from the header.
2. Construct the signed payload: `{t}.{raw_request_body}`.
3. Compute `HMAC-SHA256(signed_payload, your_webhook_secret)`.
4. Compare the result to `v1` using a constant-time comparison.
5. Check that `|now - t| < 300` seconds to prevent replay attacks.

**Never skip signature verification.** Unsigned endpoints can be spoofed.

Python verification example:

```python
import hmac, hashlib, time

def verify_webhook(payload: bytes, header: str, secret: str) -> bool:
    parts = dict(item.split("=", 1) for item in header.split(","))
    timestamp = parts["t"]
    signature = parts["v1"]
    signed = f"{timestamp}.{payload.decode()}"
    expected = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return False
    if abs(time.time() - int(timestamp)) > 300:
        return False
    return True
```

## Retry Policy

If your endpoint returns any status other than `2xx`, the platform retries with
exponential backoff:

| Attempt | Delay |
|---------|-------|
| 1       | immediate |
| 2       | 5 minutes |
| 3       | 30 minutes |
| 4       | 2 hours |
| 5       | 5 hours |

After 5 failed attempts the webhook is marked `failed` and no further retries occur.
A notification email is sent to your account's billing email.

## Webhook Logs

**GET** `/v2/webhooks/{webhook_id}/deliveries`

Returns a paginated list of delivery attempts with request/response body, status code,
latency, and next scheduled retry time. Logs are retained for 30 days.

You can manually retry a failed delivery:

**POST** `/v2/webhooks/{webhook_id}/deliveries/{delivery_id}/retry`

## Disabling and Deleting Webhooks

To temporarily pause delivery: `PATCH /v2/webhooks/{id}` with `{ "active": false }`.
To permanently remove: `DELETE /v2/webhooks/{id}`. Deletion cannot be undone.

## Testing Webhooks Locally

Use our CLI to forward webhook events to a local server:

```bash
payments-cli webhook listen --forward-to http://localhost:3000/hooks
```

Or send a test event manually:

```bash
payments-cli webhook trigger payment.succeeded --data '{"amount": 2000}'
```
