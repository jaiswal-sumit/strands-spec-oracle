# Reporting and Analytics

## Overview

The Reporting API provides pre-built and custom reports for reconciliation, finance,
and business intelligence. Reports are generated asynchronously and available as
downloadable CSV or JSON files.

## Pre-Built Reports

### Daily Summary Report

**GET** `/v2/reports/daily-summary?date=2024-10-01`

Returns a summary for the given calendar day in your account's timezone:

```json
{
  "date": "2024-10-01",
  "total_payments": 1423,
  "total_volume": { "amount": 8432150, "currency": "USD" },
  "successful_payments": 1398,
  "failed_payments": 25,
  "success_rate": 0.9824,
  "total_refunds": 12,
  "refund_volume": { "amount": 45600, "currency": "USD" },
  "net_volume": { "amount": 8386550, "currency": "USD" },
  "disputes_opened": 2,
  "new_customers": 183
}
```

### Payout Report

**GET** `/v2/reports/payouts?from=2024-09-01&to=2024-09-30`

Lists all payouts to your bank account in the date range with full reconciliation:

```json
{
  "payouts": [
    {
      "id": "po_XXXX",
      "amount": 482310,
      "currency": "USD",
      "arrival_date": "2024-09-15",
      "status": "paid",
      "included_payments": 234,
      "included_refunds": 8,
      "fees": 1420,
      "net": 480890
    }
  ]
}
```

### Dispute Summary

**GET** `/v2/reports/disputes?from=2024-01-01&to=2024-09-30`

Returns dispute counts, win rate, and total amounts at risk broken down by card network,
reason code, and resolution outcome.

## Custom Reports

For ad-hoc analysis, use the report builder:

**POST** `/v2/reports`

```json
{
  "report_type": "payments_detail",
  "from": "2024-09-01T00:00:00Z",
  "to": "2024-09-30T23:59:59Z",
  "filters": {
    "status": ["succeeded"],
    "currency": "USD",
    "metadata.plan": "enterprise"
  },
  "columns": [
    "id", "created_at", "amount", "currency", "status",
    "customer_id", "payment_method_type", "metadata.order_id"
  ],
  "format": "csv"
}
```

Report generation is asynchronous. The response includes a report ID:

```json
{ "report_id": "rpt_XXXX", "status": "pending" }
```

Poll status: **GET** `/v2/reports/{id}` until `status: "ready"`.
Download: **GET** `/v2/reports/{id}/download` returns the file.

Large reports (>1M rows) are split into parts. Check `part_count` in the status response
and download each: **GET** `/v2/reports/{id}/download?part=1`.

Reports expire 7 days after generation.

## Data Export

For continuous export to your data warehouse, use log streaming (see Monitoring spec).
For one-time bulk exports, use the custom report builder above.

Supported export formats:
- `csv`: comma-separated, UTF-8, header row included
- `json`: newline-delimited JSON (each line is one record)
- `parquet`: Apache Parquet, gzip-compressed (for large exports)

## Reconciliation

### Reconciling Payments with Payouts

Payouts aggregate multiple payments, refunds, and fees into a single bank transfer.
To match a payout to individual transactions:

```python
payout = client.payouts.retrieve("po_XXXX")
transactions = client.balance_transactions.list(payout="po_XXXX")
for txn in transactions:
    print(txn.type, txn.amount, txn.source_id)
    # type: "payment", "refund", "fee", "dispute"
```

### Fee Breakdown

Each payment has a `fee_detail` field:

```json
{
  "fee_detail": {
    "platform_fee": 120,
    "processing_fee": 59,
    "fx_fee": 0,
    "total": 179,
    "currency": "USD"
  }
}
```

- `platform_fee`: your SaaS subscription fee pro-rated per transaction.
- `processing_fee`: card network and acquiring costs.
- `fx_fee`: foreign exchange markup (0 for same-currency transactions).

## Analytics Dashboard API

The same data powering the dashboard charts is accessible via the metrics API
(see Monitoring and Alerting spec). Embed charts in your own dashboard using the
charting endpoint:

**GET** `/v2/analytics/charts/payment-volume?interval=day&from=2024-09-01&to=2024-09-30&currency=USD`

Returns pre-aggregated time-series suitable for direct plotting.

## Tax Reporting

For US merchants, the platform generates 1099-K forms for qualifying accounts.
Forms are available via `GET /v2/tax-documents` each January for the prior year.
For EU merchants, VAT reports are available on request by emailing tax@example.com.
