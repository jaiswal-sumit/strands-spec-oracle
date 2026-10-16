# Monitoring and Alerting

## Health Endpoint

**GET** `/v2/health`

Returns the current operational status of the API and its dependent services.

```json
{
  "status": "operational",
  "components": {
    "api": "operational",
    "payment_processing": "operational",
    "webhooks": "degraded",
    "reporting": "operational"
  },
  "latency_ms": {
    "p50": 45,
    "p95": 120,
    "p99": 280
  },
  "checked_at": "2024-10-01T14:32:00Z"
}
```

Possible component status values: `operational`, `degraded`, `outage`, `maintenance`.

Subscribe to the status page at https://status.example.com for incident notifications.

## Metrics Endpoint

**GET** `/v2/analytics/metrics`

Query parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `metric` | string | One of: `payment.volume`, `payment.success_rate`, `payment.avg_latency`, `refund.volume`, `dispute.rate` |
| `interval` | string | `minute`, `hour`, `day` |
| `from` | ISO 8601 | Start of time range |
| `to` | ISO 8601 | End of time range |
| `currency` | string | Filter to a single currency |

```json
{
  "metric": "payment.success_rate",
  "interval": "hour",
  "data": [
    { "timestamp": "2024-10-01T00:00:00Z", "value": 0.987 },
    { "timestamp": "2024-10-01T01:00:00Z", "value": 0.992 }
  ]
}
```

## Setting Up Alerts

Configure automated alerts on metric thresholds via the dashboard or the API.

**POST** `/v2/alerts`

```json
{
  "name": "High failure rate",
  "condition": {
    "metric": "payment.success_rate",
    "operator": "lt",
    "threshold": 0.95,
    "window_minutes": 5
  },
  "channels": [
    { "type": "email", "address": "oncall@example.com" },
    { "type": "pagerduty", "integration_key": "PD_KEY_XXXX" },
    { "type": "webhook", "url": "https://hooks.example.com/payments-alert" }
  ],
  "cooldown_minutes": 30
}
```

- `cooldown_minutes`: minimum time between repeated firings for the same condition.
- Supported operators: `lt` (less than), `gt` (greater than), `lte`, `gte`.

## Key Metrics to Monitor

### Payment Success Rate

Alert if it drops below 97% over a 5-minute window. A drop usually indicates a card
network issue, a recently deployed breaking change, or exhausted fraud detection capacity.

Baseline: 98–99.5% on typical traffic. Below 95% is an incident.

### Latency (p95)

Normal p95: 80–150 ms for authorised cards. Above 400 ms sustained indicates infrastructure
trouble. Above 1000 ms will cause integrations that don't set explicit timeouts to start failing.

### Dispute Rate

Alert if the 7-day rolling dispute rate exceeds 0.75%. Above 1% risks card network penalties.
Investigate immediately: it usually indicates a fraud pattern or fulfilment problem.

### Webhook Delivery Failure Rate

Alert if the delivery failure rate exceeds 5% over 10 minutes. Check endpoint availability
and certificate validity. Undelivered events back up in the retry queue and can delay
fulfilment.

## Dashboard

The payments dashboard (https://dashboard.example.com) provides real-time charts for all
key metrics, a live transaction log with filtering, dispute management, webhook delivery logs,
and API key management. Integrate SSO via SAML 2.0 or OIDC under `Settings → Authentication`.

## Audit Log Streaming

Stream audit logs to your SIEM or observability stack:

**POST** `/v2/log-streams`

```json
{
  "destination": "s3",
  "config": {
    "bucket": "myco-payments-audit",
    "prefix": "audit/",
    "region": "us-east-1",
    "role_arn": "arn:aws:iam::123456789012:role/PaymentsLogWriter"
  },
  "filter": {
    "event_types": ["payment.*", "refund.*", "dispute.*"]
  }
}
```

Supported destinations: `s3`, `splunk`, `datadog`, `cloudwatch`.

Logs arrive within 60 seconds of event creation. Format is newline-delimited JSON.
Fields include `event_id`, `event_type`, `timestamp`, `actor`, `resource_id`, `changes`.
