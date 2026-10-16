# Advanced Features

## Charges vs. Payment Intents

The direct charges API (`POST /v2/payments`) and the Payment Intents API are both
supported but serve different use cases:

| Use Case | Recommended API |
|----------|----------------|
| Server-side, PCI-compliant direct charge | Charges |
| Client-side checkout with 3DS | Payment Intents |
| Stored cards, subscriptions | Either (charges preferred for simplicity) |
| Multi-step checkout | Payment Intents |

New integrations should prefer Payment Intents for flexibility.

## Radar Machine Learning Model

The platform's ML model is trained on payments across all accounts and updated weekly.
It automatically adapts to new fraud patterns. You can see the model version applied to
each payment: `payment.risk.model_version`.

To provide feedback that improves the model's accuracy for your account, mark payments
as fraudulent or legitimate:

**POST** `/v2/payments/{id}/feedback`

```json
{ "label": "fraudulent", "notes": "customer reported card stolen" }
```

Feedback is incorporated into your account's personalised risk profile within 24 hours.

## SetupIntents

A `SetupIntent` saves a payment method without charging it. Use this to:
- Collect card details at signup and charge later
- Add a card to a customer's profile without a zero-authorisation charge
- Pre-authorise a card for a subscription that starts after a trial

```python
setup_intent = client.setup_intents.create(
    customer_id="cus_ABC123",
    payment_method_types=["card"],
    usage="off_session",   # card will be charged without the customer present
)
# Pass setup_intent.client_secret to the client-side SDK
```

After the customer completes setup, the `PaymentMethod` is attached to the customer
and marked as confirmed for off-session use.

## Off-Session Payments

Charges without the customer present (subscription renewals, usage billing, split payments):

```python
payment = client.payments.create(
    amount=4900,
    currency="USD",
    source="pm_CARD123",
    customer_id="cus_ABC123",
    off_session=True,
    confirm=True,
)
```

If the issuer requires authentication, the charge fails with error
`authentication_required`. Recover by creating a Payment Intent with `return_url` and
redirecting the customer to re-authenticate out-of-band.

## Bulk Operations

For high-volume operations (e.g. mass refunds, batch customer import), use the batch API:

**POST** `/v2/batch`

```json
{
  "operations": [
    { "method": "POST", "path": "/v2/refunds", "body": {"payment_id": "pay_A", "amount": 1000} },
    { "method": "POST", "path": "/v2/refunds", "body": {"payment_id": "pay_B", "amount": 2000} }
  ]
}
```

Up to 25 operations per batch request. Each operation is independent; a failure in one
does not roll back the others. The response contains an `outcomes` array with the result
of each operation in order.

## Metadata

Every resource accepts a `metadata` field: a key-value map of up to 50 keys, each key
up to 40 characters and each value up to 500 characters.

Metadata is queryable on list endpoints (see Pagination spec). It is visible in the
dashboard and included in webhooks and reports. Use it to store your internal IDs,
enabling easy correlation without a separate cross-reference table.

```json
"metadata": {
  "order_id": "ord_001",
  "user_id": "usr_12345",
  "campaign": "summer-sale",
  "region": "EMEA"
}
```

## Radar Rules Syntax

For advanced rule expressions, use the inline rule language:

```
::charge::risk_score > 80 AND :card_country: IN (XX, YY) AND ::customer::first_charge = true
```

Prefix `:resource_field:` selects a field from a related resource. Supported resources:
`charge`, `card`, `customer`, `invoice`. Operators: `=`, `!=`, `<`, `>`, `<=`, `>=`,
`IN`, `NOT IN`, `CONTAINS`.

Rules are limited to 5 conditions connected by `AND`. Nested `OR` is not supported in
rule expressions; create multiple rules instead.

## Versioning and Migrations

The API is versioned by date. Your account is pinned to the version set on your API key.
When a new version is released, you have 6 months to migrate before the old version is
deprecated. Use the changelog endpoint to see what changed:

**GET** `/v2/changelog?from_version=2024-06-15`

Test against a new version by sending `API-Version: 2024-09-01` in any request header.
The response reflects the new version's behaviour without affecting your account's default
version.
