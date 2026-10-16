# Integration Best Practices

## Security Best Practices

### API Key Management
- Store API keys in a secret manager (AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager).
- Never hardcode keys in source code or commit them to version control.
- Use a `.gitignore` entry for `.env` files and rotate keys if they are ever committed by accident.
- Issue scope-restricted keys for each service or integration; never share a single admin key.
- Rotate keys every 90 days as a routine hygiene practice.
- Revoke compromised keys immediately via the dashboard or `DELETE /v2/api-keys/{id}`.

### Webhook Signature Verification
Always verify the `HMAC-SHA256` signature on every incoming webhook payload. Skip signature
verification in a test environment only, and never in production.

```python
def verify(payload: bytes, signature_header: str, secret: str) -> bool:
    timestamp, sig = signature_header.split(",", 1)
    signed_payload = f"{timestamp}.{payload.decode()}"
    expected = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig.split("=", 1)[1])
```

### HTTPS Everywhere
Use HTTPS for all API calls and webhook endpoints. Reject any webhook deliveries arriving
over plain HTTP. Certificate errors should fail loudly, not be silently ignored.

## Reliability Best Practices

### Idempotency Keys
Use idempotency keys on every mutating request. Generate a new key per logical operation
(not per network call). Store the key alongside your order or task before making the API
call so retries can reuse it.

### Graceful Degradation
Design your checkout to handle API unavailability:
- Show a friendly error and retry rather than silently failing.
- Queue refunds and secondary operations if the primary payment succeeded.
- Never block order fulfilment on secondary API calls (e.g. adding loyalty points).

### Timeouts and Circuit Breakers
Set explicit HTTP timeouts (recommended: 30 seconds). Implement a circuit breaker that
opens after 5 consecutive 5xx responses and half-opens after 60 seconds, preventing
a cascade of slow failed requests.

### Webhook Idempotency
Deduplicate webhook events by `event.id` in your handler. The platform retries delivery;
your handler may receive the same event multiple times. A simple database table with
`event_id` as a unique key and a processed flag is sufficient.

## Performance Best Practices

### Caching
Cache immutable or slowly changing data:
- FX rates (cache for 5 minutes)
- Currency list (cache for 24 hours)
- Price objects (cache until your next deployment)

Never cache payment status — always fetch live state.

### Batch Where Possible
Use the batch endpoint for bulk operations instead of issuing individual API calls in a
tight loop. This reduces round-trip latency, connection overhead, and the risk of hitting
rate limits.

### Asynchronous Webhook Processing
Return `200 OK` immediately from your webhook endpoint after persisting the raw payload.
Process the event in a background queue. This keeps your endpoint's p99 response time
well under 30 seconds (the platform's delivery timeout) and allows horizontal scaling.

## Testing Best Practices

### Test Every Error Path
Most production bugs involve error handling, not happy paths. Use the test cards in the
Testing Guide to exercise every decline, timeout, and 3DS scenario.

### Use the Test Clock
Simulate subscription renewals, trial expirations, and dunning retries without waiting in
real time. Use `POST /v2/test/clock` to advance the sandbox clock before writing long-
running integration tests.

### Automate Integration Tests in CI
Run your integration test suite against the sandbox in every CI pipeline. Gate deployments
on a passing suite. This catches regressions before they reach production.

### Contract Tests
Write contract tests for your webhook handler: given a known JSON payload, assert the
correct side effects (order fulfilled, access granted, etc.). Contract tests catch
breaking changes introduced by your own code without requiring a full end-to-end run.

## Monitoring Best Practices

Set up alerting before go-live:
- Payment success rate drops below 97% in any 5-minute window
- p95 authorisation latency exceeds 400 ms
- Dispute rate exceeds 0.5% (7-day rolling)
- Webhook failure rate exceeds 5% (10-minute window)

These four metrics cover the most common post-launch incidents. See the Monitoring
and Alerting spec for alert creation details.
