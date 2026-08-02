# LaaraLaari engineering documentation

**Planning baseline:** 2026-07-18  
**Initial capacity target:** 1,000 registered users  
**Delivery order:** backend first, frontend after the backend release gate

This folder is the canonical source for product and engineering decisions. The original brainstorming notes are preserved unchanged in [source-notes](source-notes/).

## Agreed product direction

- Build one AI-assisted Punjabi matchmaking platform, not a collection of disconnected sites.
- Launch LaaraLaari first. Domains and experiences such as Amritdhari, NRI, Jatt, Ramgarhia, or future communities become configurable entry points into the same network.
- Keep identity labels self-declared. The platform must never infer religion, caste, community, or other sensitive identity traits.
- Support candidates and trusted profile managers such as parents or guardians, with explicit consent and visible attribution.
- Optimize for trust and outcomes: verified profiles, explainable compatibility, safe communication, moderation, and curated recommendations.
- Develop and test locally with an OpenAI-compatible GPT provider. Route production AI through Amazon Bedrock without changing domain code.
- Use asynchronous work when it improves response time or reliability, but do not introduce microservices prematurely.

## Architecture baseline

- TypeScript modular monolith with a REST API and separately scalable worker processes.
- PostgreSQL as the system of record; Redis for cache, rate limits, and local jobs; object storage for media.
- Transactional outbox for reliable domain events.
- Local event/job adapters during development; EventBridge plus SQS and dead-letter queues on AWS.
- ECS Fargate for API and worker containers; RDS, ElastiCache, S3, CloudFront, ALB, WAF, and CloudWatch.
- Infrastructure as code and GitHub Actions using GitHub OIDC—never long-lived AWS access keys.

Any baseline can be changed through an architecture decision record before implementation makes it expensive.

## Canonical documents

1. [Product scope](01-product-scope.md) — users, workflows, MVP boundaries, quality targets, and launch criteria.
2. [Component catalog and architecture](02-component-catalog-and-architecture.md) — module ownership, runtime topology, repository layout, and scaling path.
3. [Database blueprint](03-database-blueprint.md) — PostgreSQL schemas, tables, relationships, indexes, retention, and data ownership.
4. [API catalog](04-api-catalog.md) — public, authenticated, administrative, webhook, and real-time contracts.
5. [Events and background jobs](05-events-and-background-jobs.md) — event envelope, outbox, queues, retries, idempotency, and event catalog.
6. [AI architecture and evaluation](06-ai-architecture-and-evaluation.md) — capability boundaries, OpenAI/Bedrock adapters, safety, quality gates, and cost controls.
7. [Security, privacy, and trust](07-security-privacy-and-trust.md) — authorization, sensitive data, chat safety, moderation, and operational security.
8. [Local development and test strategy](08-local-development-and-test-strategy.md) — local services, test pyramid, seed data, and backend release gate.
9. [AWS infrastructure and CI/CD](09-aws-infrastructure-and-cicd.md) — environments, Terraform stacks, pipelines, deployments, backups, and rollback.
10. [Implementation backlog](10-implementation-backlog.md) — end-to-end tasks in execution order with dependencies and acceptance criteria.
11. [Decision register](11-decision-register.md) — accepted assumptions and questions to settle at the appropriate milestone.

## Implementation protocol

1. Select the first unchecked task whose dependencies are complete.
2. Implement only that task and any explicitly listed prerequisite.
3. Add or update automated tests, API contracts, migrations, and observability in the same change.
4. Run the task's acceptance checks and the repository quality gates.
5. Update the checkbox and add links to the implementation or decision record.
6. Never place secrets, real identity documents, production exports, or real user conversations in Git, fixtures, AI evaluation sets, or chat prompts.

### Global definition of done

A task is complete only when:

- behavior and failure cases are implemented;
- authorization and network scoping are enforced;
- tests cover the primary path and important rejection paths;
- logs/metrics do not expose personal or secret data;
- database/API/event changes are documented and versioned;
- lint, type checking, tests, migration checks, and secret scanning pass;
- rollback or backward compatibility is understood.

## Delivery gates

- **Foundation gate:** repository, local environment, CI, migrations, health endpoints, and module boundaries work.
- **Core backend gate:** auth, brands, profiles, preferences, media, discovery, interests, matches, and authorization work without AI.
- **Backend MVP gate:** chat, trust/reporting, notifications, billing, AI MVP capabilities, admin operations, observability, load/security tests, and OpenAPI are complete.
- **Cloud gate:** staging passes smoke, migration, backup/restore, rollback, and cost checks.
- **Frontend gate:** frontend work may begin against the versioned OpenAPI contract and stable backend MVP behaviors.
- **Launch gate:** production runbooks, legal copy, moderation staffing, support process, monitoring, and incident response are approved.

## Source notes

- [AI capabilities](source-notes/AI_capabilities.md)
- [Discussion](source-notes/Discussion.md)
- [Pointers](source-notes/pointers.md)
- [Technical suggestion](source-notes/technical%20suggestion.md)
- [UI capabilities](source-notes/UI_capabilities.md)
