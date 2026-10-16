# Authentication & Authorization Spec

## Token Issuance

Users authenticate via the `/v2/auth/token` endpoint using email + password
or OAuth2 social login (Google, GitHub). On success, the server issues:

- **Access token**: JWT, 1-hour TTL, signed with RS256.
- **Refresh token**: opaque string, 30-day TTL, stored in HttpOnly cookie.

The access token payload includes: `sub` (user_id), `exp`, `iat`, `roles`, `org_id`.

## Token Refresh

**POST** `/v2/auth/refresh`

Requires the refresh token cookie. Returns a new access token. If the refresh
token is expired or revoked, returns `401` — the user must re-authenticate.

Refresh tokens are rotated on each use (rotation strategy). The old refresh
token is immediately invalidated after a successful refresh.

## Role-Based Access Control (RBAC)

Roles are embedded in the access token. Supported roles:

| Role | Description |
|------|-------------|
| `viewer` | Read-only access to own org resources |
| `editor` | Create and update resources in own org |
| `admin` | Full access including user management |
| `superadmin` | Cross-org access (internal use only) |

Middleware checks the `roles` claim on every request. Missing or insufficient
role returns `403 Forbidden`.

## Password Policy

- Minimum 10 characters.
- Must contain uppercase, lowercase, digit, and special character.
- Passwords are hashed with Argon2id (memory=64MB, iterations=3, parallelism=2).
- Breached password check via HaveIBeenPwned k-anonymity API on registration.

## Session Management

- Concurrent sessions: max 5 active sessions per user.
- Oldest session is invalidated when the limit is exceeded.
- Sessions can be revoked individually via `DELETE /v2/auth/sessions/{session_id}`.

## MFA

- TOTP (RFC 6238) is supported and encouraged.
- MFA is enforced for `admin` and `superadmin` roles.
- Backup codes: 10 single-use codes issued at MFA setup, stored as bcrypt hashes.
