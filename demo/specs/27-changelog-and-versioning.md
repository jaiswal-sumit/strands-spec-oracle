# Changelog and API Versioning

## Versioning Policy

The API uses date-based versioning in the format `YYYY-MM-DD`. Each API key is pinned to
a version at creation time. Breaking changes are only introduced in new versions;
non-breaking additions (new fields, new optional parameters, new event types) are added
to the current version without a version bump.

### Breaking vs. Non-Breaking Changes

Breaking (require a version bump):
- Removing or renaming a field
- Changing a field's type
- Removing an endpoint
- Changing the meaning of an existing status or enum value
- Changing required → optional for response fields

Non-breaking (added to current version):
- New optional request fields
- New response fields (clients must ignore unrecognised fields)
- New enum values for existing fields
- New endpoints
- New webhook event types

### Checking Your Version

Your current pinned version is in every API response header:

```
API-Version: 2024-06-01
```

To test a different version on a single request:

```
API-Version: 2024-09-01
```

This header overrides your account default for that request only. Upgrade your account
version in the dashboard under `Settings → API → Version`.

## Version Deprecation Timeline

When a new version is released, the previous version enters deprecation:

- **Month 1–3**: New version available; old version fully supported.
- **Month 4–5**: Deprecation warnings emitted via `Deprecation-Warning` response header.
- **Month 6**: Old version sunset. Requests return `410 Gone`.

You receive 30-day and 7-day email notices before sunset. Subscribe to
https://status.example.com for real-time deprecation reminders.

## Recent Changelog

### 2024-09-01

Breaking changes:
- `payment.status` value `pending` renamed to `processing`. Update status checks accordingly.
- `customer.sources` array removed; use `GET /v2/customers/{id}/payment-methods` instead.
- Webhook payload `event.created` field renamed to `event.created_at` for consistency.

New features:
- `SetupIntents` are now GA. `SetupIntent.usage = "on_session"` is a new option.
- `POST /v2/payment-intents/{id}/increment_authorization` added for incremental auth on hotel/car rental flows.
- 3DS2 challenge flow now fires `payment_intent.requires_action` webhooks in addition to the client-side callback.

Bug fixes:
- `refund.created_at` was incorrectly populated with `payment.created_at` in some edge cases. Fixed.
- `GET /v2/customers` with `email` filter was case-sensitive; now case-insensitive.

### 2024-06-01

Breaking changes:
- `POST /v2/charges` renamed to `POST /v2/payments`. Old endpoint deprecated; sunset 2024-12-01.
- `charge.captured` boolean field removed; use `payment.status === "succeeded"` instead.

New features:
- Multi-currency pricing (`POST /v2/prices` with `tiers` array) is now GA.
- Apple Pay domain verification now automated via `POST /v2/apple-pay/domains`.
- Connect: `application_fee_amount` is now returned on destination-charge refunds.

### 2024-03-01

New features:
- `SetupIntents` (beta) — save payment methods without charging.
- FX rates endpoint: `GET /v2/fx-rates`.
- Radar inline rule language (see Advanced Features spec).
- Webhook retry attempts now capped at 10 (was 15).

Deprecations:
- `payment.source` field deprecated; use `payment.payment_method_id` instead.

## Migration Guide: 2024-06-01 → 2024-09-01

1. Search for `payment.status === "pending"` and replace with `=== "processing"`.
2. Replace `customer.sources` reads with `GET /v2/customers/{id}/payment-methods`.
3. Update webhook handlers for `event.created_at` (was `event.created`).
4. Test in sandbox with `API-Version: 2024-09-01` header before upgrading your account key.
