# Events and background jobs

## 1. Why events are used

Events keep slow or unreliable work out of user requests while preserving a simple modular monolith. They improve UX for AI generation, media processing, notifications, verification, analytics, and projection refreshes. They do not replace normal transactions or turn each module into a microservice.

### Definitions

- **Domain event:** immutable fact that committed successfully, such as `profile.updated.v1`.
- **Integration event:** minimized version published outside the owning transaction/module.
- **Job/command:** request for one worker action, such as `ai.profile-bio.generate.v1`.
- **Operation:** user-visible status resource for asynchronous work.

Events are past tense. Jobs use imperative capability names. A domain event may fan out to several jobs.

## 2. Delivery path

1. API/application service changes business state and inserts one or more `core.outbox_events` in the same PostgreSQL transaction.
2. Outbox dispatcher claims committed rows with `FOR UPDATE SKIP LOCKED` and a lease.
3. Local adapter routes to Redis/BullMQ during development; AWS adapter publishes to a custom EventBridge bus.
4. EventBridge rules route to a dedicated SQS queue per workload and a queue-specific DLQ.
5. Worker records `(consumerName,eventId)` in `core.inbox_events`, performs the idempotent transaction, and acknowledges only after commit.
6. Worker emits completion/failure domain events where other modules or the UI need them.
7. Realtime/notification consumers tell the client to fetch authoritative state.

Delivery is **at least once**. Exactly-once behavior is achieved at the business-effect level through inbox deduplication, unique constraints, expected versions, and provider idempotency keys.

## 3. Event envelope

```json
{
  "id": "0190...uuidv7",
  "type": "profile.updated.v1",
  "source": "laaralaari.profile",
  "specVersion": "1.0",
  "occurredAt": "2026-07-18T00:00:00.000Z",
  "networkId": "uuid",
  "brandId": "uuid-or-null",
  "actor": {
    "type": "account",
    "id": "uuid"
  },
  "aggregate": {
    "type": "profile",
    "id": "uuid",
    "version": 7
  },
  "correlationId": "uuid",
  "causationId": "uuid-or-null",
  "traceId": "safe-trace-id",
  "data": {
    "changedSections": ["narratives", "preferences"]
  }
}
```

Rules:

- JSON Schema for every `type` is versioned in the contracts package.
- Additive optional fields may remain in the same version. Rename/removal/semantic change creates `.v2` and a migration window.
- Consumers ignore unknown optional fields but reject unsupported versions into quarantine with an alert.
- Events contain identifiers, state/version, and reason codes—not contact values, message text, document content, exact birth date, hidden preferences, provider secrets, or raw AI prompts.
- `correlationId` follows the user/business flow; `causationId` identifies the triggering event/job.
- Event time is not trusted for ordering. Aggregate version is authoritative.

## 4. Domain event catalog

### Network, identity, and consent

| Event | Emitted when | Primary consumers |
|---|---|---|
| `brand.configuration-updated.v1` | Brand/experience config activated | Cache invalidation, audit, analytics |
| `account.registered.v1` | Verified account becomes active | Welcome notification, analytics |
| `account.contact-verified.v1` | Contact proof succeeds | Security notification, audit |
| `account.session-revoked.v1` | Session/family revoked | Realtime disconnect, security analytics |
| `account.suspended.v1` | Sanction changes account access | Realtime disconnect, notification, audit |
| `consent.recorded.v1` | Versioned consent decision saved | Audit, capability enforcement projection |
| `data-request.created.v1` | Export/deletion/correction requested | Compliance queue, notification |

### Profile and media

| Event | Emitted when | Primary consumers |
|---|---|---|
| `profile.created.v1` | Candidate draft committed | Completion projector, analytics |
| `profile.updated.v1` | Compatibility/discovery-relevant profile version changes | Completion, discovery projection, compatibility invalidation, AI refresh, analytics |
| `profile.manager-changed.v1` | Manager permission/consent changes | Conversation authorization refresh, security notification, audit |
| `profile.submitted.v1` | Publication review requested | Moderation/policy worker, notification |
| `profile.published.v1` | Profile becomes discoverable | Discovery projection, recommendation refresh, analytics |
| `profile.paused.v1` | Profile leaves discovery | Projection removal, match/notification policy refresh |
| `profile.deleted.v1` | Deletion/anonymization state begins/completes | Purge coordinators, projection cleanup, audit |
| `media.upload-completed.v1` | Object existence/checksum confirmed | Media processing job router |
| `media.ready.v1` | Scan/processing/moderation passes | Profile completion, notification, audit |
| `media.quarantined.v1` | Media fails or needs review | Moderation case, user-safe notification |

### Discovery and matchmaking

| Event | Emitted when | Primary consumers |
|---|---|---|
| `discovery.profile-viewed.v1` | Meaningful authorized view recorded | Analytics, Phase 2 recommendation signals |
| `discovery.search-saved.v1` | Saved-search alert enabled/changed | Scheduler, analytics |
| `compatibility.calculated.v1` | Versioned deterministic score committed | AI explanation job, realtime operation update |
| `interest.sent.v1` | Pending interest committed | Recipient notification, analytics, optional intro AI hint |
| `interest.accepted.v1` | Interest accepted and match created | Match notification, conversation realtime, analytics |
| `interest.declined.v1` | Interest declined | Sender-safe notification if policy allows, analytics |
| `interest.withdrawn.v1` | Sender withdraws pending interest | Recipient state update, analytics |
| `match.created.v1` | Canonical active match committed | Messaging projection, recommendation exclusion |
| `match.ended.v1` | Match/unmatch ends | Conversation policy, notifications, analytics |
| `match.outcome-reported.v1` | Consented outcome report committed | Human verification/analytics; AI learning only after governance approval |

### Chat and safety

| Event | Emitted when | Primary consumers |
|---|---|---|
| `message.created.v1` | Authorized message durably stored | WebSocket fan-out, notification, analytics counters, optional deeper safety job |
| `message.updated.v1` | Allowed edit committed | WebSocket fan-out, safety reevaluation |
| `message.deleted.v1` | User-visible deletion state committed | WebSocket fan-out, retention/evidence policy |
| `conversation.read.v1` | Read marker advances | WebSocket receipt fan-out, notification suppression |
| `profile.blocked.v1` | Safety block becomes active | Discovery/match/chat suppression, realtime disconnect, notification cancellation |
| `profile.unblocked.v1` | Block removed | Policy projections; never auto-restores relationships |
| `report.created.v1` | User report committed | Moderation queue, reporter acknowledgement |
| `moderation.case-opened.v1` | Case enters review | Admin queue/SLA alert |
| `moderation.action-applied.v1` | Human/policy action committed | Owning domain enforcement, security notification, audit |
| `moderation.appeal-decided.v1` | Appeal decision committed | Sanction update, notification, audit |
| `verification.claim-updated.v1` | Claim passes/expires/revokes | Trust summary, profile projection, notification |
| `trust.summary-updated.v1` | Versioned trust summary changes | Profile view projection, notification only if policy permits |

### Billing, notification, and AI

| Event | Emitted when | Primary consumers |
|---|---|---|
| `billing.webhook-captured.v1` | Valid/invalid signed envelope durably captured | Billing processing queue/audit |
| `subscription.updated.v1` | Normalized subscription state commits | Entitlement projector, notification, analytics |
| `payment.succeeded.v1` | Transaction succeeds | Receipt notification, analytics |
| `payment.failed.v1` | Transaction fails | Safe recovery notification, analytics |
| `entitlements.updated.v1` | Effective grants change | Cache invalidation, realtime status |
| `notification.requested.v1` | Domain policy requests a user notification | Preference/template/delivery worker |
| `notification.delivery-updated.v1` | Provider delivery/bounce/complaint state changes | Suppression policy, analytics |
| `ai.job-requested.v1` | Capability job committed | Capability-specific AI queue |
| `ai.artifact-created.v1` | Structured artifact passes schema/basic policy | Operation/realtime update, optional quality review |
| `ai.job-failed.v1` | Job reaches terminal failure | Operation/realtime update, alarm threshold, safe fallback |
| `ai.artifact-accepted.v1` | User confirms/applies artifact | Profile/messaging action, quality analytics |
| `ai.feedback-recorded.v1` | User rates artifact | AI evaluation/quality projection |

## 5. Jobs and queues

EventBridge routes business events to SQS. Work that needs separate concurrency, timeout, cost, permissions, or DLQ gets a separate queue.

| Queue / local logical name | Job names | Worker permission boundary |
|---|---|---|
| `profile-projection` | `profile.completion.recalculate.v1`, `discovery.profile-project.v1`, `discovery.profile-remove.v1` | Profile/discovery tables only |
| `media-processing` | `media.scan.v1`, `media.metadata-strip.v1`, `media.variants-generate.v1`, `media.moderate.v1`, `document.biodata-generate.v1` | S3 media prefixes, media tables; no verification bucket by default |
| `ai-profile` | `ai.profile-extract.v1`, `ai.bio-generate.v1`, `ai.profile-quality.v1` | Approved profile read view, AI tables, provider invoke |
| `ai-match` | `ai.compatibility-explain.v1`, later `ai.recommendations-rank.v1` | Visible compatibility facts only |
| `ai-communication` | `ai.message-draft.v1`, `ai.translate.v1`, `ai.tone-check.v1` | Explicit supplied/authorized text, AI tables |
| `safety` | `safety.message-review.v1`, `safety.media-review.v1`, `trust.summary-recalculate.v1` | Restricted evidence refs, trust tables |
| `notifications` | `notification.compose.v1`, `notification.deliver.v1`, `notification.digest.v1` | Notification tables and channel providers; masked destinations |
| `verification` | `verification.submit.v1`, `verification.poll.v1`, `verification.provider-event-process.v1`, `verification.expire.v1` | Verification tables/restricted S3/provider |
| `billing` | `billing.webhook-process.v1`, `billing.subscription-reconcile.v1`, `billing.entitlements-project.v1` | Billing tables/provider; no profile content |
| `analytics` | `analytics.event-project.v1`, `analytics.daily-rollup.v1` | Minimized events/analytics tables only |
| `compliance` | `data-export.generate.v1`, `data-deletion.execute.v1`, `retention.purge.v1` | Dedicated privileged task role; explicit audit/legal-hold checks |

The outbox dispatcher and scheduler are their own worker modes. A single worker artifact may run these modes, but each AWS ECS service has a narrow task role and queue allowlist.

## 6. Job payload

```json
{
  "jobId": "uuid",
  "jobType": "ai.bio-generate.v1",
  "networkId": "uuid",
  "subject": { "type": "profile", "id": "uuid", "version": 7 },
  "operationId": "uuid",
  "requestedByAccountId": "uuid",
  "correlationId": "uuid",
  "causationId": "event-id",
  "attempt": 1,
  "requestedAt": "2026-07-18T00:00:00Z",
  "parameters": { "locale": "en", "variantCount": 3 }
}
```

The worker loads authoritative authorized inputs by ID at execution time. It rejects stale versions or records the result as stale. Large text/binary content is never placed on EventBridge or SQS.

## 7. Retry, timeout, and DLQ policy

Use workload-specific values; baseline:

| Workload | Visibility timeout | Attempts | Retry pattern | Terminal handling |
|---|---:|---:|---|---|
| Projection/cache | 60 seconds | 5 | Fast exponential + jitter | DLQ and stale-projection alarm |
| Notification | 60 seconds | 5 | Respect provider `Retry-After`; channel-specific | Mark failed, DLQ, suppress permanent destination errors |
| AI | 2–10 minutes by capability | 3 | Retry throttling/5xx/timeouts; not schema/safety failures | Mark operation failed, optional approved fallback, DLQ |
| Media | 5 minutes | 3 | Retry infrastructure failures | Quarantine and case/user-safe status |
| Billing webhook | 2 minutes | 8 | Conservative exponential | Critical DLQ/age alarm; reconciliation catches drift |
| Verification | Provider-specific | 5 | Retry safe provider errors; polling scheduled separately | Manual review/reconciliation |
| Compliance/export | 15 minutes | 3 | Controlled retry | Critical case and operator runbook |

Rules:

- Worker timeout is shorter than queue visibility; heartbeat extends only for bounded jobs.
- Retry only classified transient errors. Validation, unsupported version, authorization, stale subject, and policy rejection are terminal or no-op outcomes.
- Do not retry non-idempotent provider calls unless the provider supports an idempotency key or status reconciliation.
- DLQ redrive is an audited operation through tooling; never blindly replay all messages.
- Alarms cover oldest message age, DLQ count, retry rate, processing latency, failure ratio, and outbox unpublished age.

## 8. Ordering and concurrency

- Do not assume global ordering from EventBridge/SQS standard queues.
- Aggregate version prevents older profile/config results replacing newer state.
- For strict pair state (interest/match), the database transaction is authoritative; events are notifications/projections.
- Where ordered processing is essential, use a FIFO queue with `MessageGroupId = aggregateId` only after measuring the need. Prefer version checks first.
- Worker concurrency is bounded by RDS connection budget, provider quota, Bedrock/OpenAI rate/cost limits, and downstream capacity—not only CPU.
- AI queues are separate by capability so a slow compatibility run cannot starve message assistance.

## 9. Idempotency patterns

| Effect | Idempotency mechanism |
|---|---|
| API mutation | `core.idempotency_keys`, request hash, returned resource |
| Event consume | `core.inbox_events` plus one transaction |
| Search projection | Upsert only if incoming profile version is newer |
| Compatibility | Unique input profile versions + policy version |
| Notification | Stable dedupe key per account/category/subject/window |
| Provider send | Stable internal delivery ID as provider idempotency key |
| Billing webhook | Unique `(provider,externalEventId)` and normalized transaction ref |
| Message send | Unique conversation/sender/client message ID |
| Interest acceptance | State check plus unique active canonical match pair |
| AI job | Unique active capability/subject/version/parameter fingerprint |
| Media variant | Unique asset/variant type and deterministic object key |
| Data purge | Per-subject workflow checkpoints and legal-hold recheck |

## 10. User experience contract for async work

- API acknowledges after durable enqueue/outbox commit, never after an in-memory publish.
- UI receives operation status and can subscribe to `operation.updated`; polling with exponential backoff remains supported.
- User sees `queued`, `working`, `ready`, or a useful retry/fallback message—not broker terminology.
- Duplicate taps/clicks return the same operation/result.
- Core features remain usable while noncritical AI, analytics, email, or recommendation work is delayed.
- Failed AI never empties or corrupts an existing approved bio/explanation.
- A canceled/stale operation cannot later overwrite current state.

## 11. Local-to-AWS adapter contract

Application code depends on:

- `DomainEventPublisher.append(transaction,event)` — always writes outbox.
- `EventTransport.publish(envelope)` — local or EventBridge adapter used only by dispatcher.
- `JobQueue.enqueue(job)` / `JobQueue.consume(handler)` — local Redis/BullMQ or SQS adapter.
- `Scheduler.schedule(job,runAt,dedupeKey)` — PostgreSQL schedule table; scheduler then uses queue adapter.

Contract tests run the same event schemas and idempotent handlers against both adapters. Local development may optionally use LocalStack for AWS adapter smoke tests, but ordinary tests do not require cloud credentials.

## 12. Event release gate

- Every event/job has JSON Schema, owner, producer, consumer, version, data classification, retry policy, and sample fixture.
- Outbox crash tests prove no committed event is lost and duplicate publishing is harmless.
- Consumer tests deliver each event twice and out of order.
- Poison messages reach DLQ and produce an actionable alert without blocking the queue.
- Stale profile/AI/projection jobs cannot overwrite newer versions.
- Event payload inspection finds no direct contact data, message body, raw document, hidden preference, secret, or raw provider payload.
- Local and AWS transport contract suites pass.
- Runbook proves selective DLQ replay and outbox recovery.
