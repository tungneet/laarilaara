# Local development and test strategy

## 1. Goals

The backend must be fully developable and testable without AWS credentials. Real GPT calls are opt-in; deterministic fake AI is the default. Local behavior must preserve the same domain, API, database, event schema, idempotency, authorization, and provider interfaces used in AWS.

## 2. Local prerequisites

Pin exact versions in repository files when scaffolding:

- Git.
- Active Node.js LTS through `.nvmrc`/`.node-version` and `package.json#engines`.
- `pnpm` through Corepack with a pinned package-manager version.
- Docker Desktop with Compose v2.
- An editor configured for TypeScript, ESLint, formatting, and tests.

No globally installed database, Redis, MinIO, or mail server is required.

## 3. Local service composition

| Service | Purpose | Persistence |
|---|---|---|
| PostgreSQL 16+ | Authoritative database and outbox | Named volume; disposable profile for tests |
| Redis | Cache, rate limits, local BullMQ adapter, ephemeral realtime state | Disposable by default |
| MinIO | S3-compatible media/document storage | Named volume; separate media/restricted buckets |
| Mailpit | Captures transactional email safely | Disposable |
| ClamAV or approved scanner emulator | File malware scan integration | Optional default profile; required media integration profile |
| LocalStack | EventBridge/SQS/S3 AWS adapter smoke tests | Optional integration profile, not daily dependency |
| OpenTelemetry Collector | Local traces/metrics export | Optional observability profile |

Compose health checks and deterministic ports support one-command startup. Containers run non-root where images permit, use no production credentials, and bind only to localhost.

## 4. Configuration contract

Commit `.env.example` with names and safe local defaults only. Validate all configuration at process start and fail clearly on missing/invalid values.

Required configuration groups:

- runtime: environment, port, public base URL, trusted hosts;
- database: application and migration connection URLs;
- Redis/queue adapter;
- object-storage endpoint, bucket names, local credentials, upload limits;
- auth token issuer/audience/expiry and local-only signing secret;
- encryption/key-provider adapter and local test keys;
- mail/SMS/payment/verification provider mode (`fake` by default);
- AI provider mode (`fake` by default), capability limits, optional OpenAI-compatible endpoint/model;
- telemetry/log level and redaction mode;
- feature flags and seed mode.

Rules:

- `.env`, `.env.local`, test outputs, provider cassettes, object volumes, exports, and secrets are ignored.
- `.env.example` contains no usable cloud/provider secret.
- Production configuration does not load dotenv files.
- Tests set configuration explicitly and do not depend on a developer's environment.

## 5. Expected developer commands

Repository scaffolding should provide these stable scripts:

| Script | Behavior |
|---|---|
| `pnpm setup` | Validate tools, install hooks, copy safe env template if absent, start dependencies, migrate, seed synthetic data |
| `pnpm dev` | Run API and workers in watch mode with local adapters |
| `pnpm dev:services` / `dev:services:down` | Start/stop Compose dependencies |
| `pnpm db:migrate` | Apply local migrations through migration role |
| `pnpm db:reset` | Recreate local DB and synthetic seed after explicit confirmation |
| `pnpm db:seed` | Idempotently load reference and synthetic demo data |
| `pnpm check` | Formatting check, lint, type check, architecture rules, generated-contract drift |
| `pnpm test` | Fast unit tests |
| `pnpm test:integration` | PostgreSQL/Redis/provider-adapter integration tests |
| `pnpm test:contract` | OpenAPI, event schema, provider, local/AWS adapter contracts |
| `pnpm test:e2e` | Backend full-journey tests with fake providers |
| `pnpm test:ai-eval` | Versioned synthetic AI evaluations; fake by default, real provider via explicit profile |
| `pnpm test:load` | k6 initial-capacity scenarios |
| `pnpm test:security` | API authorization/abuse/DAST-focused suite |
| `pnpm verify` | CI-equivalent required checks excluding explicitly external/provider suites |

Scripts must work on Windows, macOS, Linux, and CI; implement cross-platform Node scripts rather than shell-specific logic where practical.

## 6. Synthetic development data

Seed data includes:

- one LaaraLaari network, primary brand/domain, and several experience configurations;
- reviewed reference countries, regions, languages, communities/practices, education, occupations, and interests;
- candidate/self-manager, parent-managed, collaborator, moderator, verifier, support, and admin accounts;
- draft/published/paused profiles with intentionally diverse but fictional facts;
- preference combinations, compatibility cases, interests, matches, blocks, reports, chats, subscriptions, and AI operation states;
- provider/webhook examples using fake external identifiers;
- media generated specifically for testing, containing no real people or documents.

All names, contacts, photos, documents, conversations, and credentials are synthetic and clearly marked. The seed generator is deterministic from a versioned seed, except where uniqueness is required.

## 7. Test pyramid

### 7.1 Static and architecture checks

Run on every change:

- format, lint, strict TypeScript type checking;
- forbidden dependency/import rules between modules;
- OpenAPI/event/JSON Schema generation drift;
- Prisma schema and migration lint;
- secret scanning, dependency/license review, SAST, Dockerfile and Terraform policy checks;
- dead code and circular dependency detection where reliable.

### 7.2 Unit tests

Test domain behavior without NestJS/AWS/real database:

- profile publication/manager consent state machines;
- compatibility eligibility, factor calculation, weights, versioning, and hidden-factor views;
- interest/match transitions and canonical pair handling;
- conversation authorization, block/sanction and message policy decisions;
- entitlements, notification preferences, trust/moderation transitions;
- redaction, rate-limit keying, idempotency hashes, cursor signing;
- AI input minimization, output schemas, grounding, stale artifact prevention, and fallbacks.

Use injected clock, ID generator, provider fakes, and deterministic randomness.

### 7.3 Integration tests

Use isolated PostgreSQL/Redis/object-store instances or schemas with real migrations:

- constraints, composite network foreign keys, indexes, transaction boundaries, optimistic locking;
- outbox/inbox claim, crash, duplicate, retry, and ordering behavior;
- repository query plans on representative data;
- upload/scan/variant/quarantine and signed access;
- auth challenge/session rotation/token-family reuse detection;
- billing/verification signed webhook capture and idempotent processing;
- encryption/hash rotation adapters;
- Redis loss behavior and distributed rate limits.

Testcontainers is preferred where stable; Compose-backed test services are an acceptable fallback on supported CI runners.

### 7.4 Contract tests

- Every API route conforms to OpenAPI request, response, status, security, and error schemas.
- Consumer fixtures validate event/job JSON Schemas and compatibility across supported versions.
- Fake, OpenAI-compatible, and Bedrock AI adapters satisfy the same provider contract.
- Local Redis/BullMQ and AWS EventBridge/SQS adapters pass shared delivery/idempotency semantics.
- Storage, notification, payment, and verification providers have shared adapter contract suites.

External provider contract tests run in sandbox accounts on a scheduled/manual pipeline, not on every pull request.

### 7.5 End-to-end backend tests

A backend API client completes:

1. resolve brand context and reference data;
2. register, verify, login, refresh, and manage sessions;
3. create a self-managed and parent-managed profile, capture candidate consent, upload/process media, complete and publish;
4. create preferences, structured search, natural-language filter draft, profile view, shortlist, hide/unhide;
5. calculate compatibility and grounded explanation;
6. send/accept/decline/withdraw interests and verify match atomicity/idempotency;
7. send/edit/read messages, reconnect realtime, draft/translate/tone-check, attachment scan, manager revocation;
8. block/report, confirm immediate suppression, moderate, sanction, and appeal;
9. start/complete fake verification and show only safe claim;
10. checkout through fake provider, process duplicate/out-of-order webhooks, update entitlements, cancel/refund;
11. process email/in-app notifications and preferences;
12. export/delete account/profile with retention/legal-hold paths;
13. disable AI/provider and confirm core fallback behavior.

Each journey includes unauthorized, stale-version, duplicate, blocked, suspended, wrong-network, and provider-failure branches.

### 7.6 AI evaluation tests

- Synthetic versioned datasets are capability-specific.
- Real OpenAI-compatible tests require `AI_REAL_PROVIDER_TESTS=1`, an ignored local secret, explicit budget, and test-only data.
- Assertions cover schema validity, controlled values, fact grounding, no sensitive inference, hidden/contact/secret leakage, score consistency, tone/safety, latency, and cost.
- Provider outputs are not committed unless transformed into reviewed synthetic fixtures.
- CI uses fake adapter for deterministic behavior; scheduled evaluation may compare approved providers/models.

### 7.7 Security tests

- Broken object authorization across every resource, acting profile, brand, and network.
- Auth enumeration, OTP brute force, refresh reuse, CSRF, CORS, session revocation, admin MFA/role scope.
- SQL/template/command injection, XSS payload persistence/encoding, SSRF, oversized/deep JSON, malicious cursors.
- Upload MIME spoof, malware, image bomb, metadata, path/key manipulation, signed URL expiry/reuse.
- Message/contact scraping/spam, block race, evidence access, report privacy, manager revocation.
- Webhook invalid signature, replay, old timestamp, duplicate and out-of-order provider events.
- Prompt injection, output injection, hidden data/system prompt/secret leakage, arbitrary tool attempt, stale AI overwrite.
- Log/error/event/trace inspection for prohibited personal and secret fields.

### 7.8 Load and resilience tests

Initial scenarios are sized above the 1,000-user launch expectation:

- 100 concurrent virtual users;
- 20 requests/second sustained for 30 minutes;
- 100 requests/second short burst for public context/profile/search paths;
- profile search with a synthetic dataset of at least 10,000 profiles to expose query issues early;
- chat send/read and WebSocket fan-out with concurrent connections;
- interest acceptance race and duplicate message requests;
- queue burst of 5,000 projection/notification jobs and controlled AI queue concurrency;
- provider latency/timeouts/throttling, worker crash after side effect, Redis restart, database failover simulation where feasible;
- outbox backlog and DLQ/redrive recovery.

Pass criteria use product targets: ordinary non-AI API p95 under 400 ms, search p95 under 700 ms, bounded error rate, no lost/duplicated business effect, no DB connection exhaustion, and recovery without data corruption. Exact k6 thresholds are versioned after baseline measurement.

## 8. Database test lifecycle

- Unit tests do not touch a database.
- Integration test workers receive isolated databases/schemas and run migrations from zero.
- Migration tests apply all migrations, load previous-version fixture schema/data, upgrade, and verify invariants.
- Destructive migration is split into expand/backfill/contract releases.
- Query-plan snapshots or assertions cover critical discovery/chat/admin queries with realistic cardinality.
- Test cleanup deletes databases/objects, not shared rows through brittle teardown.

## 9. Local AI workflow

1. Develop capability against fake adapter and frozen fixtures.
2. Run unit, schema, policy, and grounding tests.
3. Opt into real GPT provider with synthetic evaluation set and explicit spend cap.
4. Save only aggregate evaluation output and approved redacted failure examples.
5. Compare prompt/model versions; never tune solely against a single anecdotal output.
6. Promote the same capability contracts to Bedrock development evaluation.

A developer should never need a production database export or real conversation to test AI.

## 10. CI check tiers

### Pull request, required

- install with frozen lockfile;
- generated-file and formatting check;
- lint, type, architecture, unit tests;
- migration from empty and integration tests;
- OpenAPI/event/provider contracts;
- backend E2E with fake providers;
- secret/SAST/dependency/license/container/IaC scans;
- build reproducible API/worker image.

### Main branch, required before staging

- all pull-request checks;
- publish image by immutable commit digest;
- AWS adapter smoke tests in development;
- staged migrations and smoke/E2E subset;
- AI synthetic evaluation against approved Bedrock route when AI changes;
- DAST/API security scan.

### Scheduled/manual

- full load/resilience suite;
- full AI provider comparison/red-team suite;
- dependency/base-image refresh validation;
- backup restore and disaster-recovery exercises;
- external payment/verification/notification sandbox contracts.

## 11. Backend release gate before frontend

Frontend implementation starts only after:

- versioned OpenAPI is complete for the MVP path and generated client smoke test passes;
- backend E2E journey passes with fake providers;
- all object/network/profile authorization and block/manager-revocation tests pass;
- local event queue can be stopped/restarted without lost effects;
- AI can be disabled and OpenAI-compatible capabilities pass approved evaluations;
- seed/demo environment is available for frontend development;
- stable error codes, pagination, idempotency, concurrency, and operation status are documented;
- no critical/high security or migration defect remains unaccepted.

## 12. Test evidence

CI publishes:

- unit/integration/E2E summaries and coverage trends (coverage is not the only quality measure);
- OpenAPI/event schema artifacts and drift result;
- migration and query-plan checks;
- security/secret/dependency/IaC/container reports;
- AI evaluation summary with capability, route alias, prompt/data/code versions, quality/safety/cost;
- load report and thresholds;
- image digest/SBOM/provenance.

Artifacts must be access-controlled, retained by policy, and scrubbed of credentials and real user data.
