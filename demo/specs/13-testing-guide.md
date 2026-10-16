# Testing Guide

## Overview

The platform provides a full sandbox environment with mirrored endpoints, test-mode API
keys, and a library of pre-built card numbers and scenarios for simulating every payment
outcome. No real money moves in the sandbox.

## Test vs. Live Mode

Test-mode keys begin with `sk_test_`; live keys with `sk_live_`. All requests made with
a test key are isolated to the sandbox database — they never affect live balances or
trigger real network calls. Switch modes by using the correct key; the base URL is the same.

## Test Cards

Use these card numbers in the sandbox to trigger specific outcomes:

### Success Scenarios

| Card Number | Brand | Outcome |
|-------------|-------|---------|
| 4111 1111 1111 1111 | Visa | Succeeds immediately |
| 5500 0000 0000 0004 | Mastercard | Succeeds immediately |
| 3782 822463 10005 | Amex | Succeeds immediately |
| 6011 1111 1111 1117 | Discover | Succeeds immediately |
| 4000 0027 6000 3184 | Visa | Requires 3D Secure authentication |
| 4000 0025 0000 3155 | Visa | 3DS required; authentication fails |
| 4000 0000 0000 0069 | Visa | Charge succeeds, refund fails |

### Decline Scenarios

| Card Number | Decline Reason |
|-------------|---------------|
| 4000 0000 0000 0002 | Generic decline (card_declined) |
| 4000 0000 0000 9235 | Insufficient funds |
| 4000 0000 0000 0127 | Incorrect CVC |
| 4000 0000 0000 0069 | Expired card |
| 4000 0000 0000 0101 | Card velocity exceeded |
| 4000 0000 0000 0036 | Card do not honor |
| 4000 0000 0000 8016 | Bank connection timeout (network error) |

Use any future expiry date and any 3-digit CVV (4 digits for Amex).

### Delayed Outcomes

Some scenarios involve delayed status changes (simulating asynchronous bank processing):

| Card Number | Behaviour |
|-------------|-----------|
| 4000 0000 0000 1891 | Payment stuck in `processing` for 3 minutes, then succeeds |
| 4000 0000 0000 2685 | Payment stuck in `processing` for 3 minutes, then fails |

These are useful for testing your polling logic and timeout handling.

## Test Bank Accounts (ACH / SEPA)

For direct debit testing:

| Account Number | Routing Number | Outcome |
|---------------|----------------|---------|
| 000111111116 | 110000000 | Succeeds |
| 000111111113 | 110000000 | Fails with `insufficient_funds` |
| 000222222227 | 110000000 | Fails with `account_closed` |

## Simulating Webhooks

You can trigger a webhook event without performing the underlying action:

**POST** `/v2/test/webhook-triggers`

```json
{
  "event_type": "payment.succeeded",
  "webhook_id": "wh_TEST123",
  "payload_overrides": {
    "payment.amount": 9999
  }
}
```

This sends the event to all webhook endpoints registered for your test-mode account.
Use it to test your webhook handler without needing to create real objects.

## Simulating Clock Advancement

The sandbox includes a test-mode clock that you can advance to test time-dependent logic
like subscription renewals, trial expirations, and dunning retries:

**POST** `/v2/test/clock`

```json
{ "advance_to": "2025-02-01T00:00:00Z" }
```

The clock can only move forward. Advancing the clock triggers all events that would
occur in the intervening period (renewals, dunning retries, etc.) and fires associated
webhooks synchronously before the response is returned.

Reset the clock to wall time: `DELETE /v2/test/clock`.

## Test Disputes

To trigger a dispute on a test-mode payment:

**POST** `/v2/test/disputes`

```json
{
  "payment_id": "pay_test_XXXX",
  "reason": "fraudulent"
}
```

The dispute is created in `needs_response` state. You can then test your dispute-handling
logic including evidence submission and resolution.

## Integration Testing Checklist

Before going live, verify:

- [ ] Successful payment creates the correct database records and triggers downstream actions
- [ ] Failed payments are surfaced to customers with an appropriate message
- [ ] Retried payments use idempotency keys to prevent double charges
- [ ] Webhook signature verification rejects unsigned or tampered payloads
- [ ] Refund flow handles `refund.failed` (retry with new refund object)
- [ ] Disputed payments are flagged in your dashboard
- [ ] 3D Secure redirects complete the payment intent correctly
- [ ] Subscription renewals fire events your app consumes
- [ ] Trial-to-paid transitions trigger fulfilment
- [ ] Cancellation at period end blocks access at the right time
