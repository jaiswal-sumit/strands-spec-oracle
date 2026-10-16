# Idempotency and Retries

## Why Idempotency Matters

Networks fail. Servers restart. Mobile clients timeout. When a payment request times out,
you do not know whether it succeeded. Without idempotency keys, a retry creates a second
charge — potentially double-billing the customer.

With idempotency keys, a retry of the same logical operation returns the original outcome
instead of creating a new transaction. The key is the contract: "this is the same
operation, not a new one."

## Idempotency Key Semantics

- An idempotency key is a string of up to 255 characters in the `Idempotency-Key` request header.
- Within a 24-hour window, any request with the same key returns the original response.
- After 24 hours the key expires; a new request with the same key starts fresh.
- Keys are scoped per endpoint. `Idempotency-Key: abc` on `POST /payments` and
  `POST /refunds` are independent.
- If the original request is still in flight, a second request with the same key returns
  `409 Conflict` until the first completes.

## Generating Keys

```python
import uuid

def make_idempotency_key(domain: str, entity_id: str) -> str:
    """Stable key for a given logical operation."""
    # Combine a domain prefix with the entity ID and a UUID suffix.
    # The UUID suffix ensures re-runs of failed jobs don't collide
    # with future legitimate retry attempts.
    return f"{domain}_{entity_id}_{uuid.uuid4().hex[:16]}"

# Examples:
# "pay_order_8823_a1b2c3d4e5f67890"
# "refund_order_8823_line2_f1e2d3c4b5a67890"
```

Store the key alongside the order or task so you can reuse the exact key on retries.
Never generate a new UUID per retry attempt — that defeats idempotency.

## Recommended Retry Strategy

```python
import time, random, httpx

def create_payment_with_retry(client, payload, *, max_attempts=4):
    key = f"pay_{payload['order_id']}_{uuid.uuid4().hex[:16]}"
    delay = 1.0

    for attempt in range(1, max_attempts + 1):
        try:
            resp = client.payments.create(
                **payload,
                idempotency_key=key,   # same key every attempt
            )
            return resp
        except httpx.TimeoutException:
            # Timeout: we don't know if it succeeded — retry with same key
            pass
        except PaymentError as e:
            if e.http_status in (429, 500, 502, 503, 504):
                # Retriable server errors
                pass
            else:
                # 4xx client errors are not retriable
                raise

        if attempt == max_attempts:
            raise MaxRetriesExceeded(f"Failed after {max_attempts} attempts")

        jitter = random.uniform(0, delay * 0.3)
        time.sleep(delay + jitter)
        delay = min(delay * 2, 30)   # cap at 30 seconds

    return None  # unreachable
```

## Retriable vs. Non-Retriable Errors

| Status | Retriable? | Notes |
|--------|-----------|-------|
| 200, 201 | n/a | Success; no retry needed |
| 400 Bad Request | No | Fix the payload |
| 401 Unauthorised | No | Check / rotate API key |
| 402 Payment Required | No | Balance issue; do not retry |
| 404 Not Found | No | Resource does not exist |
| 409 Conflict (idempotency in-flight) | Yes, with backoff | Wait and retry |
| 422 Unprocessable | No | Business rule failure (e.g. insufficient funds) |
| 429 Too Many Requests | Yes | Honour `Retry-After` header |
| 500 Internal Server Error | Yes | With backoff |
| 502 / 503 / 504 | Yes | With backoff |
| Network timeout | Yes | Must use same idempotency key |

## Checking for Duplicate Charges

If you lose track of a key, check whether a payment was created before retrying:

```python
existing = client.payments.list(
    metadata={"order_id": order_id},
    created__gte=datetime.utcnow() - timedelta(minutes=10),
)
if existing.data:
    return existing.data[0]   # found it — don't charge again
```

## Idempotency in Webhooks

Webhook deliveries are also idempotent: each event has a unique `event_id`. If your
endpoint returns a non-2xx status, the event is retried with the same `event_id`.
Check `event_id` before processing to guard against duplicate side effects:

```python
def handle(event):
    if db.event_already_processed(event.id):
        return   # discard duplicate
    db.process(event)
    db.mark_processed(event.id)
```
