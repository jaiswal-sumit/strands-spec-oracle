# Connect: Marketplace and Platform Payments

## Overview

Connect lets you build a marketplace or platform where you collect payments on behalf of
third-party sellers or service providers, then split and route the funds. Examples:
ride-sharing platforms, freelancer marketplaces, on-demand service apps.

## Account Types

### Standard Accounts

The connected account handles their own onboarding, dashboard, and tax reporting.
Funds land directly in their account; you collect a platform fee via application fees.
Best for: marketplaces where sellers want full control.

### Express Accounts

You control the onboarding UX; the connected account has a limited Stripe-Express dashboard.
Funds land in the connected account by default. You can route to a holding account with
manual payout control. Best for: gig-economy platforms.

### Custom Accounts

You own the entire experience. The connected account has no dashboard access. Full
regulatory responsibility falls on you. Best for: SaaS platforms building embedded finance.

## Onboarding Connected Accounts

```python
account = client.accounts.create(
    type="express",
    country="US",
    email="seller@example.com",
    capabilities={"card_payments": {"requested": True}},
    business_type="individual",
)

link = client.account_links.create(
    account_id=account.id,
    refresh_url="https://yourplatform.com/onboard/retry",
    return_url="https://yourplatform.com/onboard/done",
    type="account_onboarding",
)
# Redirect seller to link.url
```

The seller completes identity verification, banking details, and (for US) SSN/EIN.
Listen for `account.updated` webhooks with `charges_enabled: true` to know when they
can receive payments.

## Charging on Behalf of a Connected Account

### Destination Charge

The charge appears on the platform account; funds are automatically transferred to the
connected account minus fees.

```python
payment = client.payments.create(
    amount=10000,
    currency="USD",
    source="card_tok_XXXX",
    transfer_data={
        "destination": "acct_SELLER123",
        "amount": 8000,           # seller receives $80; platform keeps $20
    }
)
```

### Direct Charge

The charge appears on the connected account's statement. Requires the customer to
explicitly consent to charges by the third party.

```python
payment = client.payments.create(
    amount=10000,
    currency="USD",
    source="card_tok_XXXX",
    on_behalf_of="acct_SELLER123",
)
```

### Separate Charge and Transfer

Charge the customer, then transfer later (useful when payout timing differs from charge):

```python
payment = client.payments.create(amount=10000, currency="USD", source="card_tok_XXXX")

# Later, after service delivery:
transfer = client.transfers.create(
    amount=8000,
    currency="USD",
    destination="acct_SELLER123",
    source_transaction=payment.id,
)
```

## Platform Fees

Collect a fee on each transaction using `application_fee_amount`:

```python
payment = client.payments.create(
    amount=10000,
    currency="USD",
    source="card_tok_XXXX",
    application_fee_amount=500,   # platform earns $5
    transfer_data={"destination": "acct_SELLER123"},
)
```

The fee lands in your platform account's balance. It is non-refundable unless you
explicitly refund it via `POST /v2/application-fee-refunds`.

## Payouts to Connected Accounts

By default, connected accounts receive automatic daily payouts to their registered bank.
Override to manual with:

```python
client.accounts.update("acct_SELLER123", settings={"payouts": {"schedule": {"interval": "manual"}}})
```

Trigger a manual payout:

```python
client.payouts.create(
    amount=8000,
    currency="USD",
    stripe_account="acct_SELLER123",
)
```

## Dispute Handling on Connect

When a customer disputes a charge on a connected account, the disputed amount is debited
from the connected account's balance. If the connected account has insufficient balance,
the platform account is debited (cover liability depends on account type and your
contract). The `charge.dispute.created` webhook fires on both the platform account and
the connected account.

## Compliance Responsibilities

| Responsibility | Standard | Express | Custom |
|---------------|---------|---------|--------|
| AML/KYC | Connected account | Shared | Platform |
| PCI DSS scope | Connected account | Platform | Platform |
| Tax reporting (1099) | Connected account | Platform | Platform |
| Dispute handling | Connected account | Platform | Platform |
