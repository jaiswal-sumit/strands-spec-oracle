# API Contract — Payments Service v2

## Overview

The Payments Service exposes a REST API for processing transactions, managing
refunds, and querying payment status. All endpoints require authentication via
Bearer tokens issued by the Auth Service.

Base URL: `https://api.example.com/v2/payments`

## Authentication

All requests must include an `Authorization: Bearer <token>` header.
Tokens expire after 3600 seconds. Expired tokens return `401 Unauthorized`.
Service-to-service calls use IAM-signed requests (SigV4) instead of Bearer tokens.

## Create Payment Endpoint

**POST** `/v2/payments`

Request body:

```json
{
  "amount": 1500,
  "currency": "USD",
  "source": "card_abc123",
  "idempotency_key": "order_xyz_001",
  "metadata": { "order_id": "xyz_001" }
}
```

- `amount`: integer, in minor units (cents). Required. Max 999999999.
- `currency`: ISO 4217, 3-letter code. Required.
- `idempotency_key`: string, max 64 chars. Required. Duplicate keys within 24h return the original response.
- `metadata`: object, max 10 keys, values must be strings ≤ 500 chars each. Optional.

Response `201 Created`:

```json
{
  "payment_id": "pay_def456",
  "status": "pending",
  "created_at": "2026-01-15T10:30:00Z"
}
```

## Get Payment Status

**GET** `/v2/payments/{payment_id}`

Returns the current status of a payment. Possible status values:
`pending`, `processing`, `succeeded`, `failed`, `cancelled`, `refunded`.

Response `200 OK`:

```json
{
  "payment_id": "pay_def456",
  "status": "succeeded",
  "amount": 1500,
  "currency": "USD",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:05Z"
}
```

## Refund Endpoint

**POST** `/v2/payments/{payment_id}/refunds`

- Only `succeeded` payments can be refunded.
- Partial refunds allowed; total refunded amount cannot exceed original payment amount.
- Refund processing time: 3–5 business days.

## Rate Limits

- 100 requests/minute per API key for write endpoints (POST, PATCH, DELETE).
- 1000 requests/minute per API key for read endpoints (GET).
- Rate limit headers: `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- Exceeded limits return `429 Too Many Requests`.
