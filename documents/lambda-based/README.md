# LaaraLaari — serverless (Lambda) architecture variant

**Status:** exploratory alternative to the modular monolith in [../monolythic/](../monolythic/README.md). Nothing here is implemented yet.

## Why this folder exists

The monolithic variant assumes ECS Fargate, an ALB, and ElastiCache Redis. This folder captures a **simplest-possible serverless** variant for the same product, aimed at very low idle cost and near-zero ops at low traffic:

- **Route 53** — DNS only.
- **API Gateway** — HTTP API (REST) + a separate WebSocket API. No ALB.
- **AWS Lambda** — one Lambda running the FastAPI app (via an ASGI adapter such as Mangum) behind an API Gateway `{proxy+}` route. No per-endpoint Lambdas.
- **RDS (micro/small) PostgreSQL** — same system of record as the monolithic design.
- **S3** — media and generated documents, via presigned URLs (unchanged).
- **SQS + EventBridge** — async jobs, now consumed by Lambda workers instead of ECS worker services.
- **CloudWatch** — logs, metrics, alarms.
- **No ALB, no ElastiCache.** Caching is best-effort, in-memory, per Lambda execution environment only.

## What is unchanged from the monolithic docs

These are architecture-neutral and stay authoritative for this variant too:

- Product scope: [../monolythic/01-product-scope.md](../monolythic/01-product-scope.md)
- Database schema: [../monolythic/03-database-blueprint.md](../monolythic/03-database-blueprint.md)
- Event catalog and payload shapes (transport changes, event *names/semantics* do not): [../monolythic/05-events-and-background-jobs.md](../monolythic/05-events-and-background-jobs.md)
- AI capability boundaries and safety rules: [../monolythic/06-ai-architecture-and-evaluation.md](../monolythic/06-ai-architecture-and-evaluation.md)
- Security, privacy, and trust model: [../monolythic/07-security-privacy-and-trust.md](../monolythic/07-security-privacy-and-trust.md)

## What this folder defines so far

- [04-api-catalog.md](04-api-catalog.md) — standalone REST/WebSocket/webhook contract for the serverless runtime. Business endpoints are the same as the monolithic catalog; the execution model, WebSocket transport, rate limiting, caching, and connection handling are rewritten for Lambda + API Gateway constraints.

## Not written yet (follow-up docs, only build if this variant is chosen)

- `02-component-catalog-and-architecture.md` — Lambda packaging (one ASGI Lambda vs. per-domain functions), repository layout, deployment unit boundaries.
- `03/05` deltas — outbox dispatcher and schedulers as EventBridge-scheduled Lambdas instead of long-running ECS processes.
- `08-local-development-and-test-strategy.md` — local FastAPI + Docker Postgres/S3(MinIO)/SQS(ElasticMQ or LocalStack) loop, SAM/CDK local invoke.
- `09-aws-infrastructure-and-cicd.md` — Terraform/SAM/CDK stack for API Gateway, Lambda, RDS, RDS Proxy, SQS, EventBridge, IAM, CI/CD.
- `10-implementation-backlog.md` — task list, only after the team commits to this variant over the monolithic one.

## Open decisions specific to this variant

Record final choices in the shared decision register ([../monolythic/11-decision-register.md](../monolythic/11-decision-register.md)) once settled.

1. **RDS Proxy.** Not in the user's original service list, but Lambda concurrency opens/closes many short-lived DB connections; without pooling, concurrent invocations will exhaust `max_connections` on a micro/small RDS instance quickly. Recommended default: add RDS Proxy in front of RDS from day one (small added cost, ~$10–15/month) rather than treating it as an optional later fix.
2. **WebSocket connection registry.** No ElastiCache/DynamoDB in the user's list. Default in this doc: a plain `realtime_connections` table in RDS (simplest, one less service). DynamoDB is the standard AWS reference pattern for API Gateway WebSocket connection registries and is cheaper/faster at higher concurrency — worth revisiting if RDS write volume from connection churn becomes a bottleneck.
3. **Single Lambda vs. per-domain Lambdas.** Default: one Lambda running the whole FastAPI app (simplest deploy, one cold start profile to manage). Splitting hot paths (e.g., messaging, discovery) into their own functions is a later optimization, not a starting point.
4. **HTTP API vs. REST API (API Gateway).** Default: HTTP API for REST (cheaper, lower latency, sufficient feature set) plus a WebSocket API. REST API is only needed if a specific feature (e.g., request validation models, certain WAF integrations) turns out to be required.
5. **Provisioned concurrency.** Not included by default (adds fixed cost, contradicts "simplest design"). Revisit only if p95 cold-start latency violates a stated UX budget.
6. **Custom domain edge.** Default: Route 53 alias record directly to a regional API Gateway custom domain with a regional ACM certificate and a regional WAF Web ACL attached to the API Gateway stage. CloudFront is optional and deferred — only add it later for edge caching of the public/reference endpoints or for edge-optimized global latency.
