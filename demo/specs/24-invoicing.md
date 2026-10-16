# Invoicing

## Overview

The Invoice API lets you create, send, and collect payment for itemised bills. Invoices
are useful for B2B billing, metered usage charges, and one-off professional service fees.
They differ from subscription renewals (which are auto-generated) by being manually
drafted, reviewed, and sent.

## Invoice States

```
draft → open → paid
             ↘ uncollectible
             ↘ void
```

- `draft`: Editable. Not yet sent. Default state on creation.
- `open`: Finalised and sent. Payment is due. Can no longer be edited; only voided.
- `paid`: Payment received.
- `uncollectible`: Marked as bad debt. No further collection attempts.
- `void`: Cancelled before payment. Creates a zero-amount credit note.

## Creating a Draft Invoice

**POST** `/v2/invoices`

```json
{
  "customer_id": "cus_ABC123",
  "currency": "USD",
  "due_date": "2024-11-01",
  "auto_advance": false,
  "metadata": { "project": "Q4-consulting" }
}
```

- `auto_advance: true` automatically finalises and sends the invoice one hour after creation.
- `auto_advance: false` keeps it in draft until you call `/finalize` explicitly.

## Adding Line Items

**POST** `/v2/invoices/{id}/line-items`

```json
{
  "description": "Platform development — October 2024",
  "amount": 1200000,
  "currency": "USD",
  "quantity": 1,
  "tax_rates": ["txr_VAT20"],
  "metadata": { "hours": "80", "rate": "150" }
}
```

Multiple line items can be added. Discounts are applied at the invoice level:

**POST** `/v2/invoices/{id}/discounts`

```json
{ "coupon_id": "cpn_FALL15", "amount_off": 15000 }
```

## Tax Rates

Create reusable tax rates:

**POST** `/v2/tax-rates`

```json
{
  "display_name": "VAT",
  "percentage": 20.0,
  "inclusive": false,
  "country": "GB",
  "jurisdiction": "UK",
  "tax_type": "vat"
}
```

`inclusive: false` adds the tax on top of the line item amount.
`inclusive: true` treats the line item amount as tax-inclusive.

Attach a tax rate to a line item via `tax_rates: ["txr_VAT20"]`. If a customer has a
valid tax ID (see Customer Management spec), reverse-charge rules override the tax rate
automatically.

## Finalising and Sending

**POST** `/v2/invoices/{id}/finalize`

Locks the invoice, assigns an invoice number (e.g. `INV-2024-0042`), and sends it to the
customer's email with a pay-now link. The invoice status moves to `open`.

The hosted invoice page lets customers pay with any enabled payment method. It is mobile-
friendly and supports multiple languages (see `invoice.locale` to override the language).

## Payment Collection

### Manual Collection

The customer pays via the hosted invoice page or you collect payment server-side:

**POST** `/v2/invoices/{id}/pay`

```json
{ "payment_method": "pm_CARD123" }
```

### Auto-Collection

Set `collection_method: "charge_automatically"` at creation to charge the customer's
default payment method immediately upon finalisation.

### Installments

For large invoices, enable installments:

```json
{ "installments": { "enabled": true, "plan": { "intervals": 3 } } }
```

Three equal payments are charged automatically: one at finalisation, one after 30 days,
one after 60 days.

## Credit Notes

If goods are returned or a partial refund is needed after the invoice is paid:

**POST** `/v2/credit-notes`

```json
{
  "invoice_id": "inv_XXXX",
  "lines": [
    { "line_item_id": "li_YYYY", "quantity": 1 }
  ],
  "reason": "product_returned",
  "refund_amount": 50000
}
```

The credit note reduces the customer's balance. If connected to a payment, the specified
`refund_amount` is returned to their card.

## Sending Reminders

Overdue reminders are sent automatically on days 3, 7, and 14 after the due date.
Configure the reminder schedule under `Settings → Invoicing → Reminders`.

Manually send a one-off reminder:

**POST** `/v2/invoices/{id}/send`

```json
{ "include_pdf": true, "email": "billing@client.com" }
```
