# Fraud Prevention

## Overview

The platform includes a multi-layer fraud prevention system combining machine learning
risk scoring, rules, 3DS authentication, and velocity controls. You can supplement with
custom rules to reflect your specific risk profile.

## Risk Score

Every payment and payment-method creation includes a `risk` object:

```json
{
  "id": "pay_01J8X3K",
  "risk": {
    "score": 42,
    "level": "normal",
    "signals": ["ip_mismatch", "first_time_customer"]
  }
}
```

- `score`: 0 (safe) to 100 (high risk). Not calibrated to a probability; use as an
  ordinal ranking only.
- `level`: `normal` (0–64), `elevated` (65–84), `high` (85+).
- `signals`: list of risk factors contributing to the score.

Common signals: `ip_mismatch`, `velocity_address`, `velocity_card`,
`card_testing_pattern`, `high_risk_country`, `unusual_time`, `suspicious_email`.

## Risk Rules

Create custom rules to automatically block, review, or flag transactions:

**POST** `/v2/fraud/rules`

```json
{
  "name": "Block high-risk countries",
  "condition": {
    "field": "card.country",
    "operator": "in",
    "value": ["XX", "YY"]
  },
  "action": "block",
  "enabled": true
}
```

Actions: `block` (return decline), `flag` (allow but mark for review), `review` (hold
for manual approval before capturing), `allow` (bypass all other checks).

Rules are evaluated in priority order. Use `priority` (1 = highest) to control evaluation
order when multiple rules match.

### Condition Fields

| Field | Type | Examples |
|-------|------|---------|
| `card.country` | string | ISO 3166-1 alpha-2 |
| `card.brand` | string | `visa`, `mastercard`, `amex` |
| `customer.email_domain` | string | `gmail.com` |
| `customer.first_transaction` | boolean | |
| `payment.amount` | integer | in minor units |
| `payment.currency` | string | ISO 4217 |
| `risk.score` | integer | 0–100 |
| `risk.level` | string | `normal`, `elevated`, `high` |
| `metadata.*` | string | any metadata key |

### Operators

`eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `contains`, `starts_with`, `regex`.

For `in` / `not_in`, `value` must be an array. For all others, a scalar string or number.

## Radar Block Lists

Maintain lists of cards, emails, IPs, or customers that should always be blocked:

**POST** `/v2/fraud/block-lists/{list_id}/entries`

```json
{ "type": "email", "value": "fraudster@example.com", "note": "known fraudster" }
```

Supported types: `email`, `email_domain`, `card_fingerprint`, `ip`, `customer_id`, `device_id`.

Block list checks run before risk scoring.

## Allow Lists

Trusted customers (e.g. enterprise accounts) can bypass rules but not block lists:

```python
client.customers.update("cus_ABC123", fraud_bypass="rules")
```

`fraud_bypass: "rules"` skips custom rules. `fraud_bypass: "all"` skips rules and
ML scoring (use sparingly for fully trusted internal accounts only).

## 3D Secure as a Fraud Control

Requiring 3DS on elevated-risk payments is the most effective fraud control available.
Configure automatic 3DS escalation:

**POST** `/v2/fraud/rules`

```json
{
  "name": "Require 3DS for elevated risk",
  "condition": { "field": "risk.level", "operator": "in", "value": ["elevated", "high"] },
  "action": "require_3ds"
}
```

## Fraud Review Queue

Payments blocked by a `review` rule enter the review queue:

**GET** `/v2/fraud/review-queue`

Each entry has `approve` and `decline` actions:

**POST** `/v2/fraud/review-queue/{id}/approve` — captures the payment.
**POST** `/v2/fraud/review-queue/{id}/decline` — voids the payment and notifies the customer.

Set up email notifications for new review items via `POST /v2/alerts` with
`metric: "fraud.review_queue_depth"`.

## Reporting

**GET** `/v2/fraud/summary?from=2024-09-01&to=2024-09-30`

Returns: total blocked payments, total blocked amount, block rate, rule-hit breakdown,
dispute rate (actual fraud that passed), and false-positive rate (estimated from disputes
won on blocked cards).
