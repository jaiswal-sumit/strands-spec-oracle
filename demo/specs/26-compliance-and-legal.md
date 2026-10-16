# Compliance and Legal

## PCI DSS

The Payments Service is certified as a PCI DSS Level 1 Service Provider, the highest
certification tier. Our certificate is published at https://example.com/pci.

### Your PCI Scope

The scope of PCI compliance required on your side depends on your integration method:

| Integration | Your Scope |
|-------------|-----------|
| Hosted fields / JS SDK | SAQ A (simplest; card data never touches your servers) |
| Redirect to hosted checkout | SAQ A-EP |
| Server-side API with tokenised card | SAQ C-VT |
| Server-side API with raw PAN | Full PCI DSS assessment required |

For most integrations, use the JavaScript SDK or hosted checkout to stay in SAQ A.
If you pass raw card numbers through your servers, engage a Qualified Security Assessor (QSA).

## SOC 2 Type II

We maintain SOC 2 Type II certification covering Security, Availability, and Confidentiality
trust service criteria. The report is available under NDA via your account executive or
by emailing compliance@example.com.

## ISO 27001

Information Security Management System certification. Certificate available on request.

## GDPR

### As a Controller

For data collected directly by you (customer names, emails) and passed to us as payment
metadata, you are a controller and we act as your processor. Our Data Processing Agreement
(DPA) is available in your dashboard under `Settings → Legal`. Sign the DPA to formalise
the relationship before processing EU personal data.

### As a Processor

For payment data we collect directly (card data, bank account details), we act as a
controller under our privacy policy (https://example.com/privacy).

### Data Subject Rights

| Right | How to Handle |
|-------|--------------|
| Access | Export customer data via `GET /v2/customers/{id}/data-export` |
| Erasure | `DELETE /v2/customers/{id}/personal-data` |
| Portability | Data export returns JSON including all payments, methods, and invoices |
| Rectification | Update customer via `PATCH /v2/customers/{id}` |

## Anti-Money Laundering (AML)

All merchants are subject to AML screening at onboarding and ongoing monitoring. We may
request additional documentation for:

- High transaction volumes or unusual spikes
- High-risk industry codes (MCC)
- Payments to or from high-risk jurisdictions

If your account is placed under review, payouts are paused. Respond to information
requests within 5 business days to avoid account suspension.

Prohibited business categories are listed at https://example.com/legal/prohibited-businesses.
Do not attempt to process payments for prohibited categories; violations result in immediate
account termination and potential regulatory referral.

## Transaction Monitoring

We automatically flag transactions that match patterns associated with:
- Structuring (multiple transactions just below reporting thresholds)
- Rapid round-trip payments
- Payments to sanctioned entities (OFAC, EU, UN lists)

Sanctioned transactions are blocked automatically and reported to the relevant authorities.
You cannot override a sanctions block.

## Terms of Service

By using the API you accept the Terms of Service (https://example.com/legal/tos). Key
provisions relevant to developers:

- You may not use the API to facilitate payments for prohibited businesses.
- Storing cardholder data beyond what is necessary for processing is prohibited.
- You must maintain accurate business information; material changes must be reported.
- Violation of terms can result in immediate account termination without refund of fees.

## Tax Obligations

We collect and remit sales tax, VAT, and GST in jurisdictions where we are the Merchant
of Record. In jurisdictions where you are the Merchant of Record, you are responsible for
tax compliance. The reporting tools in the Reporting spec provide the data you need for
filing. Consult a tax professional for jurisdiction-specific obligations.
