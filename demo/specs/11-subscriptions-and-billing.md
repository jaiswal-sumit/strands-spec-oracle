# Subscriptions and Billing

## Overview

Subscriptions automate recurring billing against a stored payment method on a defined
billing cycle. The platform handles dunning (automatic retry on payment failure), trial
periods, proration, and plan changes.

## Creating a Subscription

**POST** `/v2/subscriptions`

```json
{
  "customer_id": "cus_ABC123",
  "plan_id": "plan_monthly_pro",
  "payment_method_id": "pm_CARD123",
  "trial_end": "2024-10-15T00:00:00Z",
  "metadata": { "crm_id": "sfdc_001" }
}
```

- `trial_end`: optional. While in trial the subscription is active but no charges occur.
  If omitted the subscription bills immediately.
- `payment_method_id`: must belong to the specified customer.
- The first invoice is created synchronously and returned in the response.

## Subscription States

```
trialing → active → past_due → cancelled
                 ↘ cancelled (immediate)
```

- `trialing`: No charges. Transitions to `active` at `trial_end`.
- `active`: Billing normally on the renewal date.
- `past_due`: Renewal payment failed; dunning in progress.
- `cancelled`: No further charges. Cannot be reactivated; create a new subscription.

## Billing Cycles

Plans define the billing interval:

| Interval | Billing Date |
|----------|-------------|
| `monthly` | Same date each month (e.g. 15th). If a month is shorter, bills on the last day. |
| `yearly` | Same date each year. Feb 29 → Feb 28 on non-leap years. |
| `weekly` | Every 7 days from the subscription start date. |
| `custom` | `interval_count` × `interval_unit` (e.g. every 3 months). |

## Plan Changes (Upgrades / Downgrades)

**PATCH** `/v2/subscriptions/{id}`

```json
{
  "plan_id": "plan_annual_enterprise",
  "proration_behavior": "create_prorations"
}
```

- `proration_behavior`:
  - `create_prorations`: generates a credit for unused time and a charge for the new plan,
    both on the next invoice.
  - `none`: switches the plan at the next renewal with no proration.
  - `always_invoice`: generates and collects an invoice immediately for the price difference.

## Dunning (Payment Failure Handling)

When a renewal payment fails, the platform retries automatically:

| Attempt | Timing |
|---------|--------|
| 1 | 3 days after failure |
| 2 | 5 days after attempt 1 |
| 3 | 7 days after attempt 2 |

On each retry a `subscription.payment_failed` webhook fires. If all retries fail, the
subscription moves to `cancelled` and a `subscription.cancelled` event fires.

You can configure the dunning schedule via `PATCH /v2/account/dunning-config`.

## Invoices

Every billing cycle generates an `Invoice` object. Invoices are in `draft` state briefly
before being finalised. Once finalised, they cannot be edited.

**GET** `/v2/invoices?subscription_id={id}` — list all invoices for a subscription.

Invoice line items reflect:
- Recurring plan charge
- Proration credits and charges
- One-time add-ons (if any)
- Taxes (calculated based on customer billing address)

## Cancellation

**DELETE** `/v2/subscriptions/{id}?at_period_end=true`

- `at_period_end=true` (default): subscription stays active until the current period ends,
  then cancels. No refund.
- `at_period_end=false`: cancels immediately. A prorated credit is applied to the next invoice
  if on an annual plan.
