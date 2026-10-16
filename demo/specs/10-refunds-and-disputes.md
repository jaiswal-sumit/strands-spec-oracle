# Refunds and Disputes

## Refunds

### Creating a Refund

**POST** `/v2/refunds`

```json
{
  "payment_id": "pay_01J8X3K9F0",
  "amount": 1500,
  "reason": "requested_by_customer",
  "metadata": { "support_ticket": "TKT-4821" }
}
```

- `amount`: optional. Defaults to the full remaining capturable amount. Partial refunds
  are supported on payments in `succeeded` or `partially_refunded` state.
- `reason`: one of `duplicate`, `fraudulent`, `requested_by_customer`. Required.
- Refunds can only be created within 180 days of the original payment.
- Refunds are non-cancellable once created.

### Refund State Machine

```
created → pending → succeeded
                 ↘ failed
```

- `created`: Refund record created, not yet submitted to the network.
- `pending`: Submitted to the card network. Typical processing time: 5–10 business days.
- `succeeded`: Funds returned to cardholder.
- `failed`: Processing failed (e.g. card account closed). Failed refunds do not automatically
  retry; create a new refund or issue a manual payment.

### Querying Refunds

**GET** `/v2/refunds?payment_id={payment_id}` — all refunds for a payment.

**GET** `/v2/refunds/{id}` — single refund.

### Refund Fees

Platform processing fees are not refunded. Only the charged amount is returned to the
cardholder. For example, on a $20.00 payment with a $0.88 fee, the cardholder receives
$20.00 and the platform fee of $0.88 is retained.

## Disputes (Chargebacks)

### Overview

A dispute (chargeback) occurs when a cardholder contacts their bank to reverse a charge.
When a dispute is opened, the disputed amount is immediately debited from your account
balance and placed in a reserve while the case is reviewed.

You are notified via a `payment.dispute_opened` webhook within 5 minutes of a dispute filing.
You typically have 7–21 calendar days to submit evidence (exact deadline varies by card network).

### Dispute States

| State | Meaning |
|-------|---------|
| `warning_needs_response` | Inquiry; respond to avoid formal dispute |
| `needs_response` | Formal dispute; evidence submission open |
| `under_review` | Evidence submitted; awaiting card network decision |
| `charge_refunded` | Refunded before decision; dispute closed |
| `won` | Dispute decided in your favour; funds released |
| `lost` | Dispute decided against you; funds forfeited |

### Submitting Evidence

**POST** `/v2/disputes/{id}/evidence`

```json
{
  "customer_email": "jane@example.com",
  "customer_name": "Jane Smith",
  "product_description": "Annual SaaS subscription",
  "shipping_documentation": "base64_encoded_pdf",
  "service_date": "2024-08-15",
  "uncategorized_text": "Customer used the product until the day of the dispute."
}
```

The more evidence you provide the better. Disputes with comprehensive evidence have a
win rate ~65% higher than those with minimal evidence.

Allowed file types for documentation uploads: PDF, JPEG, PNG. Max 5 MB per file, 8 files per dispute.

### Accepting a Dispute

If you choose not to contest a dispute:

**POST** `/v2/disputes/{id}/close`

This immediately releases the reserve back to the cardholder and closes the case.
Accepted disputes do not appear on your dispute win/loss record.

### Dispute Fees

A $15 fee is charged for each dispute regardless of outcome. The fee is waived if the
dispute is resolved in your favour.
