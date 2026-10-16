# Deployment & Infrastructure Spec

## Environments

| Environment | URL | Purpose |
|-------------|-----|---------|
| development | localhost:8080 | Local dev |
| staging | staging-api.example.com | Pre-prod integration tests |
| production | api.example.com | Live traffic |

## Container & Compute

- Service runs as a Docker container on AWS ECS Fargate.
- Task definition: 1 vCPU, 2GB memory per task.
- Auto-scaling: min 2, max 20 tasks; scale out at 70% CPU or 80% memory.
- Health check: `GET /health` — must return `200` within 5s.

## CI/CD Pipeline

1. Pull request triggers: lint, unit tests, integration tests (against a test DB).
2. Merge to `main` auto-deploys to staging.
3. Staging smoke tests must pass before production deploy is unlocked.
4. Production deploy is a blue/green deployment with 10-minute canary at 5% traffic.
5. Automated rollback if error rate > 2% during canary window.

## Database

- AWS RDS PostgreSQL 16, Multi-AZ, db.r7g.large.
- Automated daily snapshots, 30-day retention.
- Read replica in the same region for analytics queries.
- Connection pooling via PgBouncer (transaction mode, max 100 connections per task).

## Secrets Management

All secrets (DB credentials, API keys, JWT signing keys) stored in AWS Secrets Manager.
Rotated automatically every 90 days. Services access secrets via IAM role — no hardcoded credentials.

## Observability

- Metrics: CloudWatch + custom Prometheus metrics exposed at `/metrics`.
- Tracing: AWS X-Ray, 5% sampling in production, 100% in staging.
- Logs: structured JSON to CloudWatch Logs, 90-day retention.
- Dashboards: Grafana connected to CloudWatch + Prometheus.
