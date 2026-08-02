# Decision register

This file separates accepted architecture decisions from business choices that still need an owner. Defaults allow foundation work to proceed; a default becomes final only when its due milestone is reached.

## Accepted architecture decisions

| ID | Decision | Reason |
|---|---|---|
| ADR-001 | One shared LaaraLaari network with configurable brands/experiences; no database per flavor | Preserves network effects and avoids duplicated accounts/operations |
| ADR-002 | Include `network_id` as a future isolation boundary | Allows a genuinely separate white-label network without redesigning every table |
| ADR-003 | Modular monolith plus separately runnable workers | Maximizes delivery speed while preserving module and scaling boundaries |
| ADR-004 | REST first; WebSocket only for chat/status fan-out | Keeps a durable, testable contract and avoids realtime coupling |
| ADR-005 | PostgreSQL is the source of truth; objects stay out of the database | Matches relational workflows, transactions, flexible JSON, and initial scale |
| ADR-006 | Transactional outbox for events; EventBridge routes and SQS buffers AWS work | Prevents dual-write loss and provides retries/DLQs without Kafka operations |
| ADR-007 | Core API and durable workers run on ECS Fargate, not Lambda | Better fit for DB-heavy APIs, WebSockets, controlled concurrency, and workers |
| ADR-008 | AI is a provider-neutral domain capability and not required for core correctness | Enables local OpenAI testing and production Bedrock routing/fallback |
| ADR-009 | Compatibility score is deterministic and versioned; an LLM may explain but not invent the score | Improves testability, grounding, transparency, and provider independence |
| ADR-010 | Sensitive identity/community fields are self-declared and never inferred | Required for user control, respect, privacy, and safer model behavior |
| ADR-011 | Backend MVP and versioned OpenAPI precede frontend implementation | Prevents UI work from defining unstable persistence/business behavior |
| ADR-012 | GitHub OIDC assumes AWS deploy roles; no stored long-lived AWS keys | Reduces credential leakage and supports least privilege |

Detailed ADR files can be added when a decision changes or requires deeper trade-off analysis.

## Proposed technical defaults

| ID | Default | Change deadline |
|---|---|---|
| TD-001 | TypeScript, current pinned Node.js LTS, NestJS, `pnpm` | Before task FND-001 |
| TD-002 | Prisma plus reviewed SQL migrations for PostgreSQL-specific features | Before task DAT-001 |
| TD-003 | Redis and BullMQ behind local queue interfaces | Before task EVT-005 |
| TD-004 | Terraform for AWS infrastructure | Before task CLD-001 |
| TD-005 | Vitest/Jest-compatible Nest test setup, Testcontainers, Playwright/API E2E, and k6 | Before task TST-001 |
| TD-006 | OpenTelemetry with JSON logs and CloudWatch in AWS | Before task OBS-001 |
| TD-007 | Hosted checkout; payment provider adapter supports India and international providers | Before task BIL-001 |
| TD-008 | Private S3 buckets with presigned access and CloudFront only where authorization remains enforceable | Before task MED-001 |

## Product/legal decisions required

| ID | Decision needed | Safe working default | Owner / due |
|---|---|---|---|
| OQ-001 | Legal entity, launch countries, and governing jurisdiction | Do not open public registration until counsel reviews applicable obligations | Founder/legal, before beta |
| OQ-002 | Minimum age and jurisdiction-specific marriage eligibility | Platform minimum 18 plus configurable jurisdiction rule; never publish an ineligible profile | Founder/legal, before profile publication |
| OQ-003 | Candidate consent when a parent creates the profile | Candidate must verify and consent before publication; no silent profile creation | Founder/legal, before profile module completion |
| OQ-004 | Initial login methods | Email magic link/password plus phone OTP adapter; require one verified channel | Product, before auth implementation |
| OQ-005 | Initial countries, languages, and translations | English and Punjabi UI-ready fields; AI translation explicitly marked; reference data uses ISO codes | Product, before reference seed freeze |
| OQ-006 | Community/religious-practice taxonomy and wording | User-controlled, optional, multi-select where appropriate, with “prefer not to say” | Product/community review, before beta seed freeze |
| OQ-007 | Gender and match-eligibility model | Do not encode theme assumptions; store user-declared identity and explicit matching preferences separately | Product/legal, before profile schema freeze |
| OQ-008 | Exact compatibility factors, weights, dealbreakers, and explanation wording | Start with equal normalized categories and no hidden hard exclusions; run offline review | Product, before AI compatibility launch |
| OQ-009 | Chat retention, deletion, and moderator-access policy | Retain active chat only as necessary; support deletion workflow; access by case and audit only | Legal/trust, before messaging launch |
| OQ-010 | Contact detail and attachment sharing policy | Block high-risk files; warn/limit early contact sharing; user controls visibility | Trust, before messaging launch |
| OQ-011 | Verification provider and accepted claims by country | Provider-neutral API plus manual sandbox; show only passed claim/date publicly | Product/legal, before verification integration |
| OQ-012 | Payment providers, currencies, prices, taxes, refunds, and renewal terms | Provider-neutral adapter and no card storage; do not enable production checkout until approved | Finance/legal, before billing production |
| OQ-013 | Notification channels and consent | Transactional email first; marketing opt-in separate; SMS/WhatsApp disabled until approved | Product/legal, before notification production |
| OQ-014 | AI data-processing terms, allowed providers/models, retention, and user opt-out | Minimize/redact prompts, disable provider training where available, record model/prompt, allow capability kill switch | Legal/security, before real user AI processing |
| OQ-015 | Moderation policy, sanctions, appeals, and staffing hours | Human review before high-impact sanctions; emergency block permitted with prompt review | Trust/legal, before beta |
| OQ-016 | Data export/deletion timelines and legal holds | Workflow and audit implemented; final deadlines configured after counsel review | Legal, before beta |
| OQ-017 | AWS home region and disaster-recovery region | Choose based on residency, Bedrock availability, latency, and cost; do not hard-code region | Security/product, before Terraform environments |
| OQ-018 | Production availability/cost balance | Two API tasks and Multi-AZ RDS recommended; staging can be smaller | Founder/engineering, before production plan |
| OQ-019 | Final domains and redirect behavior | LaaraLaari canonical; secondary domains resolve or redirect to an explicit experience | Product/SEO, before DNS deployment |
| OQ-020 | Brand visual rules | Theme tokens selected by brand/experience/user preference, accessible contrast, no gender stereotyping | Product/design, before frontend |

## Decision process

For each open item:

1. Record the decision, owner, date, alternatives, and evidence.
2. Identify affected database/API/event contracts and backlog tasks.
3. Add a migration/backward-compatibility plan if implementation already exists.
4. Update this register and the relevant canonical document.
5. Never place credentials or sensitive provider/account details in the decision text.

## Credentials note

An AWS “service account” should be implemented as IAM roles:

- developers authenticate through AWS IAM Identity Center/SSO;
- GitHub Actions uses OIDC to assume environment-specific deployment roles;
- ECS tasks use task roles;
- external provider secrets live in Secrets Manager;
- no access key, secret key, OpenAI key, payment secret, or private document should be pasted into chat or committed to Git.
