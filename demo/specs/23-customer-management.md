# Customer Management

## Overview

A `Customer` object represents a buyer in your system. Attaching customers to payments
enables saved payment methods, subscription management, receipts, and dispute assistance.
Customers are optional for one-off payments but required for subscriptions.

## Creating a Customer

**POST** `/v2/customers`

```json
{
  "email": "jane@example.com",
  "name": "Jane Smith",
  "phone": "+1-555-123-4567",
  "description": "Premium subscriber since 2024",
  "metadata": { "internal_id": "usr_12345", "plan": "enterprise" },
  "address": {
    "line1": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "postal_code": "94105",
    "country": "US"
  }
}
```

The `email` field is used to send automated receipts. Ensure you have consent before
adding customers' email addresses.

## Updating a Customer

**PATCH** `/v2/customers/{id}`

Any field may be updated at any time. To remove an optional field, set it to `null`.
Updating `email` does not retroactively affect previously sent receipts.

## Customer Portals

The Customer Portal is a hosted, pre-built UI where customers can manage their own
payment methods, view invoices, update billing addresses, and cancel subscriptions.

**POST** `/v2/customer-portals`

```json
{
  "customer_id": "cus_ABC123",
  "return_url": "https://yoursite.com/account",
  "features": {
    "payment_method_update": true,
    "subscription_cancel": true,
    "invoice_history": true
  }
}
```

Returns a `url` valid for 5 minutes. Redirect the customer directly; do not link to it
from a public page as it grants access without re-authentication.

Configure the portal's appearance (logo, colours, business name) in your dashboard under
`Settings → Customer Portal`.

## Payment Methods on a Customer

### Listing

**GET** `/v2/customers/{id}/payment-methods`

### Setting a Default

**PATCH** `/v2/customers/{id}`

```json
{ "default_payment_method": "pm_CARD456" }
```

The default payment method is used for subscriptions when no explicit method is specified.

### Detaching

**DELETE** `/v2/customers/{id}/payment-methods/{pm_id}`

The payment method is removed from the customer and deactivated. Any subscriptions using
this method will fail on the next renewal.

## Merging Customers

When a guest checkout customer creates an account, merge their payments history:

**POST** `/v2/customers/{target_id}/merge`

```json
{ "source_customer_id": "cus_GUEST" }
```

The source customer's payment methods, subscriptions, and payment history are transferred
to the target. The source is then deleted. Irreversible.

## Deleting Customers

**DELETE** `/v2/customers/{id}`

Soft-deletes the customer. Active subscriptions are cancelled immediately. Payment methods
are deactivated. Historical payment records are retained (required for audit purposes).
The customer object is retrievable but `deleted: true` is set.

## Customer Search

**GET** `/v2/customers/search?q=jane`

Full-text search across `email`, `name`, `phone`, and metadata values. Returns up to 10
results per query. For programmatic pagination over large customer lists, use the standard
list endpoint with filters.

## Tax IDs

Store customer tax identifiers for invoice and receipt rendering:

**POST** `/v2/customers/{id}/tax-ids`

```json
{ "type": "eu_vat", "value": "DE123456789" }
```

Supported types: `eu_vat`, `gb_vat`, `au_abn`, `ca_bn`, `us_ein`, `in_gst`, `sg_gst`,
`my_sst`, `br_cnpj`, `jp_cn`, and more. Tax IDs are validated against official registries
where APIs are available.

Once a tax ID is attached, VAT is stripped from invoices for B2B EU transactions (reverse
charge applies). Configure VAT rates per country under `Settings → Tax`.
