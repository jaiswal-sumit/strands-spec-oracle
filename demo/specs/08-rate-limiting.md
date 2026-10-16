# Rate Limiting

## Overview

The API enforces rate limits to protect service availability. Limits are applied per API
key and reset on a rolling 60-second window. Exceeding a limit returns `429 Too Many Requests`.

## Default Limits

| Endpoint Category | Limit |
|-------------------|-------|
| Read endpoints (`GET`) | 500 req/min |
| Write endpoints (`POST`, `PUT`, `PATCH`) | 100 req/min |
| Delete endpoints (`DELETE`) | 30 req/min |
| Search endpoint | 20 req/min |
| Webhook deliveries (outbound) | unlimited |

Limits are independent per category. Exhausting write limits does not affect read limits.

## Response Headers

Every response includes rate-limit metadata:

```
X-RateLimit-Limit:     100
X-RateLimit-Remaining: 73
X-RateLimit-Reset:     1726394260
X-RateLimit-Retry-After: 0
```

- `X-RateLimit-Reset`: Unix timestamp when the window resets.
- `X-RateLimit-Retry-After`: Seconds until retry is safe (0 if no limit breach).

## Handling 429 Responses

When you receive `429 Too Many Requests`:

1. Read `X-RateLimit-Retry-After` from the response header.
2. Wait that many seconds before retrying.
3. If `Retry-After` is 0 or missing, wait 1 second.
4. Use exponential backoff with jitter for subsequent retries.

```python
import time, random

def with_rate_limit_retry(fn, max_attempts=5):
    for attempt in range(max_attempts):
        resp = fn()
        if resp.status_code != 429:
            return resp
        retry_after = int(resp.headers.get("X-RateLimit-Retry-After", 1))
        jitter = random.uniform(0, 0.5)
        time.sleep(retry_after + jitter)
    raise Exception("Rate limit retries exhausted")
```

## Burst Allowance

A 10-second burst of up to 2× the per-minute limit is allowed before limiting kicks in.
This accommodates short spikes without requiring back-off logic for typical traffic.

## Enterprise Limits

Enterprise accounts have customised limits defined in their contract. Contact support
to retrieve your effective limits via `GET /v2/account/rate-limits`.

## IP-Based Limits

In addition to per-key limits, a secondary IP-based limit of 1,000 req/min applies to
prevent DDoS. This limit is shared across all API keys originating from the same IP.
It cannot be increased.

## Webhook Endpoint Rate Limits

Your webhook endpoint should be able to handle bursts of up to 200 req/s. If your
infrastructure cannot sustain this, set a queue in front of your endpoint and return
`200 OK` immediately after enqueuing, then process asynchronously.
