# Data Model Specification

## Entity: User

```
users
  id            UUID        PK
  email         VARCHAR(255) UNIQUE NOT NULL
  password_hash VARCHAR(255) NOT NULL
  org_id        UUID        FK → organisations.id
  roles         TEXT[]      DEFAULT ['viewer']
  mfa_enabled   BOOLEAN     DEFAULT false
  created_at    TIMESTAMPTZ DEFAULT now()
  updated_at    TIMESTAMPTZ DEFAULT now()
  deleted_at    TIMESTAMPTZ NULL     -- soft delete
```

Users are soft-deleted. The email column enforces uniqueness only on active
(non-deleted) rows via a partial unique index.

## Entity: Payment

```
payments
  id              UUID        PK
  org_id          UUID        FK → organisations.id
  amount          INTEGER     NOT NULL CHECK (amount > 0)
  currency        CHAR(3)     NOT NULL
  status          payment_status_enum NOT NULL DEFAULT 'pending'
  idempotency_key VARCHAR(64) UNIQUE NOT NULL
  source_id       VARCHAR(255) NOT NULL
  metadata        JSONB       DEFAULT '{}'
  created_at      TIMESTAMPTZ DEFAULT now()
  updated_at      TIMESTAMPTZ DEFAULT now()
```

`payment_status_enum`: `pending | processing | succeeded | failed | cancelled | refunded`

Status transitions are validated in the application layer. Invalid transitions
(e.g. `succeeded → pending`) return a `422 Unprocessable Entity`.

## Entity: Refund

```
refunds
  id          UUID        PK
  payment_id  UUID        FK → payments.id
  amount      INTEGER     NOT NULL CHECK (amount > 0)
  reason      TEXT        NULL
  status      refund_status_enum NOT NULL DEFAULT 'pending'
  created_at  TIMESTAMPTZ DEFAULT now()
```

A database constraint ensures `SUM(refunds.amount) <= payments.amount` per payment.

## Indexes

Critical performance indexes:
- `payments(org_id, created_at DESC)` — paginated payment listing
- `payments(idempotency_key)` — idempotency lookups
- `users(email)` WHERE `deleted_at IS NULL` — login lookups

## Migrations

All schema changes go through Flyway migrations under `db/migrations/`.
Migrations must be backward-compatible for at least one deploy cycle
(additive changes only; destructive changes need a two-phase migration).
