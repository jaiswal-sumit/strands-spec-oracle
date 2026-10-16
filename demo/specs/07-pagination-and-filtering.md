# Pagination and Filtering

## Cursor-Based Pagination

All list endpoints use cursor-based pagination. Page-number pagination is not supported
because it is inconsistent when records are created or deleted between requests.

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 20 | Records per page. Min 1, max 100. |
| `starting_after` | string | — | Return records after this object ID (exclusive). |
| `ending_before` | string | — | Return records before this object ID (exclusive). |

Only one of `starting_after` or `ending_before` may be specified per request.

### Response Structure

```json
{
  "data": [ { ... }, { ... } ],
  "has_more": true,
  "next_cursor": "pay_01J8X3K",
  "prev_cursor": "pay_01J8X1A",
  "total_count": 4821
}
```

- `total_count` is an estimate for collections > 10,000 records. Do not rely on it for
  exact counts.
- `next_cursor` / `prev_cursor` are null when there are no further pages in that direction.

### Iterating All Records

```python
cursor = None
while True:
    params = {"limit": 100}
    if cursor:
        params["starting_after"] = cursor
    page = client.payments.list(**params)
    process(page.data)
    if not page.has_more:
        break
    cursor = page.next_cursor
```

## Filtering

All list endpoints accept filter parameters as query strings.

### Date Range Filters

```
GET /v2/payments?created[gte]=2024-01-01T00:00:00Z&created[lte]=2024-01-31T23:59:59Z
```

Operators: `gt`, `gte`, `lt`, `lte`. Value must be an ISO 8601 timestamp.

Filters are also supported on `updated_at` and, for payments, `settled_at`.

### Status Filter

```
GET /v2/payments?status=succeeded&status=failed
```

Multiple values produce an OR query. Valid values per resource type are documented
in the data model spec.

### Amount Filter

```
GET /v2/payments?amount[gte]=1000&amount[lte]=50000
```

Amounts are always in minor units (cents). Both bounds are inclusive.

### Currency Filter

```
GET /v2/payments?currency=USD&currency=EUR
```

Accepts ISO 4217 3-letter codes. Multiple values produce an OR query.

### Metadata Filter

```
GET /v2/payments?metadata[order_id]=ord_001
```

Filters on exact metadata key-value pairs. Only one metadata key may be filtered per
request. This filter is O(n) and should not be used for high-frequency list operations;
use a dedicated search index instead.

### Customer Filter

```
GET /v2/payments?customer=cus_ABC123
```

Returns all payments for the given customer ID, across all payment methods.

### Combining Filters

All filters are ANDed. For example:

```
GET /v2/payments?status=succeeded&currency=USD&created[gte]=2024-09-01T00:00:00Z&limit=50
```

Returns up to 50 succeeded USD payments created on or after 2024-09-01.

## Sorting

List endpoints are sorted by `created_at` descending by default (newest first).
Specify `sort=created_at:asc` to reverse. Custom sort fields are not supported.

## Search Endpoint

For full-text or complex queries, use the dedicated search endpoint:

**POST** `/v2/payments/search`

```json
{
  "query": "status:'succeeded' AND currency:'USD' AND amount>5000",
  "limit": 50
}
```

The search endpoint supports a subset of Elasticsearch query syntax. Results are ranked
by relevance descending and do not support cursor pagination — use `from` / `size` instead
(max `from` + `size` ≤ 1000). Search indexes have up to 60 seconds of propagation delay.
