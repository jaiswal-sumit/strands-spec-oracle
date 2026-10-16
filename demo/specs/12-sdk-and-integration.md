# SDK and Integration Guide

## Official SDKs

| Language | Package | Minimum Version |
|----------|---------|----------------|
| Python | `payments-sdk` | 3.1.0 |
| Node.js / TypeScript | `@payments/sdk` | 4.2.0 |
| Java | `com.example.payments:sdk` | 2.0.0 |
| Go | `github.com/example/payments-go` | 1.5.0 |
| Ruby | `payments-ruby` | 3.0.0 |

All SDKs share the same underlying REST API and have feature parity. Use the REST API
directly for languages without an official SDK.

## Python SDK Quick Start

```python
from payments import Client, PaymentError

client = Client(api_key="sk_live_...", timeout=30)

# Create a payment
try:
    payment = client.payments.create(
        amount=2000,
        currency="USD",
        source="card_abc123",
        idempotency_key="order_001",
    )
    print(payment.status)  # "succeeded"
except PaymentError as e:
    print(e.code, e.message)
```

## Authentication in the SDK

```python
# From environment variable (recommended)
import os
client = Client(api_key=os.environ["PAYMENTS_API_KEY"])

# Explicit key rotation (e.g. after Secrets Manager retrieval)
client.api_key = new_key
```

## Idempotency Keys

All create operations accept an `idempotency_key`. If a request with the same key is
retried within 24 hours, the original response is returned without re-executing the
operation. This is critical for safe retries on network errors.

```python
import uuid

key = f"order_{order_id}_{uuid.uuid4().hex}"
payment = client.payments.create(
    amount=5000,
    currency="USD",
    source=card_token,
    idempotency_key=key,
)
```

Guidelines:
- Include a domain-specific prefix (`order_`, `refund_`, etc.) to aid debugging.
- Generate a new UUID suffix for each distinct attempt; reuse the same key for retries.
- Keys must be unique per endpoint — the same key on two different endpoints creates two records.

## Retry Logic in the SDK

The SDK retries `429 Too Many Requests` and `5xx` responses automatically with exponential
backoff (max 3 attempts by default).

```python
client = Client(
    api_key=os.environ["PAYMENTS_API_KEY"],
    max_retries=5,           # retry up to 5 times
    retry_on_timeout=True,   # also retry on network timeouts
)
```

Idempotency keys are sent on all retried requests automatically.

## Webhook Integration

```python
from payments.webhooks import WebhookHandler

handler = WebhookHandler(secret=os.environ["WEBHOOK_SECRET"])

@app.route("/hooks/payments", methods=["POST"])
def handle_webhook():
    event = handler.parse(
        payload=request.data,
        signature=request.headers["Stripe-Signature"],
    )
    if event.type == "payment.succeeded":
        fulfill_order(event.data.object.metadata["order_id"])
    return "", 200
```

## Mock Mode for Testing

```python
from payments import Client
from payments.testing import MockServer

with MockServer() as mock:
    client = Client(api_key="sk_test_mock", base_url=mock.url)
    mock.stub("POST", "/v2/payments", status=201, body={"id": "pay_test"})
    result = client.payments.create(amount=100, currency="USD", source="card_test")
    assert result.id == "pay_test"
```

The mock server records all requests; use `mock.requests` to assert call counts and payloads.

## Logging and Tracing

```python
import logging
logging.getLogger("payments.http").setLevel(logging.DEBUG)
# Logs every request URL, method, status code, and latency
```

For distributed tracing, set `trace_id` in the request context:

```python
from payments.context import set_trace_id
set_trace_id(request.headers.get("X-Trace-Id", str(uuid.uuid4())))
```

The trace ID is forwarded in the `X-Trace-Id` header on all outbound API requests and is
included in API audit logs, enabling end-to-end request tracing.
