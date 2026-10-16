# Error Handling & Retry Spec

## Standard Error Response Format

All API errors return a consistent JSON envelope:

```json
{
  "error": {
    "code": "PAYMENT_NOT_FOUND",
    "message": "No payment found with id pay_xyz",
    "request_id": "req_abc123",
    "doc_url": "https://docs.example.com/errors/PAYMENT_NOT_FOUND"
  }
}
```

`request_id` is always present and should be included in support tickets.

## HTTP Status Code Mapping

| Status | Usage |
|--------|-------|
| 400 | Malformed request, validation failure |
| 401 | Missing or expired authentication |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (e.g. duplicate idempotency key with different payload) |
| 422 | Business rule violation (e.g. invalid status transition) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
| 503 | Downstream dependency unavailable |

## Retry Strategy for Clients

Clients SHOULD implement exponential backoff with jitter for retryable errors:

- **Retryable**: `429`, `500`, `503`
- **Non-retryable**: `400`, `401`, `403`, `404`, `409`, `422`

Recommended backoff formula:
```
wait = min(base * 2^attempt + random(0, base), max_wait)
base = 1s, max_wait = 32s, max_attempts = 5
```

Always include the original `idempotency_key` on retried POST requests to
prevent duplicate payments.

## Internal Retry Policy (Service-to-Service)

The Payments Service retries failed calls to downstream services (card processor,
fraud detector) with:
- Max 3 attempts
- 200ms base delay, exponential backoff
- Circuit breaker: opens after 5 consecutive failures, half-open after 30s

## Error Logging

All 5xx errors are logged to CloudWatch with:
- `request_id`, `user_id`, `org_id`, `endpoint`, `status_code`, `error_code`
- Stack traces are included for 500 errors only (never exposed to clients)
- Alerts fire on PagerDuty when 5xx error rate exceeds 1% over 5 minutes

## Idempotency Error Handling

If a request arrives with an existing `idempotency_key` but a different request
body, the server returns `409 Conflict` with error code `IDEMPOTENCY_KEY_CONFLICT`.
This is not retryable.
