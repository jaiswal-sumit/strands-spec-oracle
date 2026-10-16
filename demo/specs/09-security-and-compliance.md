# Security and Compliance

## TLS Requirements

All API communication must use TLS 1.2 or higher. TLS 1.0 and 1.1 are rejected at the
network layer. We recommend TLS 1.3 for all new integrations. Certificate pinning is
not required but is supported via our published certificate fingerprints.

## API Key Security

API keys are sensitive credentials:

- **Never embed keys in client-side code** (browser JavaScript, mobile apps).
- Store keys in environment variables or secret management systems (AWS Secrets Manager,
  HashiCorp Vault, etc.).
- Use restricted keys with only the scopes your integration needs.
- Rotate keys every 90 days or immediately after any suspected exposure.
- If a key is compromised, revoke it via `DELETE /v2/api-keys/{id}` immediately.

## API Key Scopes

| Scope | Endpoints Accessible |
|-------|---------------------|
| `payments:read` | GET /payments, GET /payments/{id} |
| `payments:write` | POST /payments, PATCH /payments |
| `refunds:write` | POST /refunds |
| `webhooks:manage` | All /webhooks endpoints |
| `reporting:read` | GET /reports, GET /analytics |
| `admin` | All endpoints (for internal use only) |

Create scope-restricted keys for third-party integrations. Never issue `admin` scope to
external systems.

## PCI DSS Compliance

The Payments Service is PCI DSS Level 1 certified. When using our hosted fields or
JavaScript SDK, cardholder data (PAN, CVV, expiry) never touches your servers. Your
PCI scope is reduced to SAQ A.

If you are transmitting raw card data via the server-side API (e.g., migration scenarios),
you must be PCI DSS certified at the appropriate level. Contact compliance@example.com for
scope assessment.

## GDPR and Data Residency

By default, payment data is stored in the EU (AWS eu-west-1). US accounts can opt into
US-only storage (us-east-1) via account settings. Data is never replicated across regions
without explicit consent.

### Right to Erasure

To delete a customer's personal data:

**DELETE** `/v2/customers/{id}/personal-data`

This removes name, email, billing address, and tokenised card references. The payment
transaction records (amounts, timestamps, status) are retained for legal and financial
audit purposes per local regulations (7 years in most EU jurisdictions).

## Encryption at Rest

All data is encrypted at rest using AES-256. Encryption keys are managed via AWS KMS with
annual rotation. Customers with enterprise contracts can bring their own KMS key (BYOK).

## Audit Logs

Every API call is logged with:
- Timestamp (nanosecond precision)
- API key ID and account ID
- Source IP
- Request path, method, status code
- Request/response payload hash (not the payload itself)

Audit logs are retained for 3 years and are available via:

**GET** `/v2/audit-logs`

Logs can also be streamed to your S3 bucket or Splunk instance via the Log Streaming feature.

## Vulnerability Disclosure

Report security issues to security@example.com. We follow responsible disclosure:
- Acknowledgement within 24 hours
- Status update within 72 hours
- Target remediation within 30 days for critical, 90 days for high severity

We operate a bug bounty programme. See https://example.com/security/bounty for scope and rewards.
