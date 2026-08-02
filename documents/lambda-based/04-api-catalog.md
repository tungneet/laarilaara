# API catalog — serverless (Lambda + API Gateway) variant

This is the standalone implementation contract for the serverless deployment variant described in [README.md](README.md). Business resources, permissions, and domain rules are identical to [../monolythic/04-api-catalog.md](../monolythic/04-api-catalog.md); what changes is *how* the contract is served: one Lambda behind API Gateway, RDS instead of RDS+Redis, and API Gateway WebSocket instead of an ALB-fronted socket.

## 1. Serverless execution model

- **Compute shape.** One Lambda function runs the whole FastAPI application via an ASGI adapter (Mangum). API Gateway HTTP API forwards every request through a single `ANY /{proxy+}` route to that Lambda. There is no per-endpoint Lambda; this keeps IAM, deployment, and cold-start behavior manageable at this scale.
- **Transport.** API Gateway **HTTP API** for REST (`/v1/...`), plus a separate API Gateway **WebSocket API** for realtime (see §9). No ALB, no CloudFront requirement — Route 53 aliases directly to the API Gateway regional custom domain (see [README.md](README.md) open decision 6).
- **Hard platform limits that shape the contract:**
  - API Gateway integration timeout is fixed at **29 seconds**. Treat **~20 seconds** as the practical synchronous budget so the Lambda can time out cleanly before API Gateway does and still return a shaped error.
  - API Gateway payload limit is **10 MB** (request and response); Lambda synchronous invoke payload is **6 MB**. Media/file bytes never transit the API — uploads/downloads always use S3 presigned URLs (unchanged from the monolithic catalog).
  - Lambda execution environments are not guaranteed warm between requests. Anything held "in memory" (see caching, below) is best-effort only and must never be relied on for authorization, rate-limit correctness, or idempotency.
  - Anything that cannot reliably finish in a few seconds — AI generation, biodata PDF rendering, verification provider round-trips, moderation scans, bulk exports — is **always** `202 Accepted` plus the `Operation` resource (§2), processed by a separate SQS/EventBridge-triggered Lambda worker. The monolithic catalog already models these as async; that pattern carries over unchanged and is in fact a better fit for Lambda than for a long-lived process.
- **No dedicated cache tier (no ElastiCache).**
  - Per-Lambda-execution-environment in-memory caching is allowed only for read-mostly, low-sensitivity reference data (countries, languages, active plans, feature flags) with a short TTL (for example 60 seconds) and must tolerate being cold on every invocation.
  - Anything that needs correctness across concurrent invocations (rate limits, idempotency keys, distributed locks/leases) is backed by RDS, not memory.
- **Rate limiting without Redis.** Two layers:
  1. Coarse **API Gateway usage plans / throttling** (per-route burst and steady-state limits) as the first line of defense against abusive traffic, configured per stage.
  2. Fine-grained per-account/per-IP/per-action domain limits enforced in application code against an RDS-backed sliding-window/token-bucket table (`core.rate_limit_counters`) using a single conditional upsert per check. This adds one extra RDS round trip per rate-limited request compared to the Redis-based design — acceptable at this scale; revisit (e.g., DynamoDB) only if RDS load becomes the bottleneck.
- **Idempotency and outbox storage.** The transactional outbox already lives in PostgreSQL in the monolithic design, so it is unchanged here. `Idempotency-Key` records also live in RDS (`core.idempotency_keys`, unique on `(accountId, key, route)`, with a TTL cleanup job) rather than Redis.
- **Database connections.** Lambda concurrency opens and closes many short-lived connections; without pooling this exhausts `max_connections` on a micro/small RDS instance under even light concurrent load. The default in this variant is **RDS Proxy** in front of RDS (see [README.md](README.md) open decision 1); each Lambda execution environment holds at most one proxied connection.
- **Background jobs.** EventBridge → SQS (unchanged) → **Lambda worker** consumers (replacing the ECS worker services from the monolithic design). Idempotent consumers, DLQs per queue, and the event envelope/catalog are unchanged — see [../monolythic/05-events-and-background-jobs.md](../monolythic/05-events-and-background-jobs.md).
- **Health checks.** `/health/live` and `/health/ready` still exist for synthetic canaries, but liveness is close to meaningless for a stateless function. `/health/ready` checks RDS Proxy connectivity. An EventBridge scheduled rule may periodically invoke it as a cheap warm-up ping; this is not a substitute for provisioned concurrency if a stricter cold-start SLO is ever required.
- Everything not called out above — auth model, authorization rules, brand/network resolution, pagination, error envelope, status codes, and domain error codes — is unchanged from the monolithic catalog and reproduced in §2–§17 so this document is usable on its own.

## 2. Common resources

### Operation

```json
{
  "id": "uuid",
  "kind": "profile.bio.generate",
  "status": "queued",
  "progress": 0,
  "subject": { "type": "profile", "id": "uuid", "version": 7 },
  "result": null,
  "error": null,
  "createdAt": "2026-07-18T00:00:00Z",
  "completedAt": null
}
```

States: `queued`, `running`, `succeeded`, `failed`, `canceled`, `expired`. A safe retry can create or return the same operation through idempotency. `queued`/`running` transitions happen inside SQS-triggered Lambda workers, not the API Lambda.

### Cursor list

```json
{
  "items": [],
  "page": { "nextCursor": null, "hasMore": false }
}
```

### Acting profile

Endpoints that act for a candidate require `X-Acting-Profile-Id`, unless the profile ID is unambiguous in the path. The server verifies current manager permission on every request; it never trusts the header alone, and never trusts anything cached in a warm Lambda environment from a previous invocation.

## 3. Public and platform endpoints

| Method and path | Purpose | Notes |
|---|---|---|
| `GET /health/live` | Process liveness | Always returns fast; no dependency calls |
| `GET /health/ready` | Readiness | Checks RDS Proxy/DB connectivity only; may be invoked by a scheduled warm-up rule |
| `GET /v1/context` | Resolved public brand/experience configuration | Host-derived; optional explicit experience slug; eligible for best-effort in-memory caching |
| `GET /v1/reference/countries` | Active countries | Public, locale-aware; eligible for best-effort in-memory caching |
| `GET /v1/reference/regions?countryCode=` | Active regions | Public |
| `GET /v1/reference/languages` | Active languages | Public |
| `GET /v1/reference/communities` | Reviewed self-identification options | Public labels only |
| `GET /v1/reference/religious-practices` | Reviewed optional practices | Public labels only |
| `GET /v1/reference/education-levels` | Education options | Public |
| `GET /v1/reference/occupation-categories` | Occupation options | Public |
| `GET /v1/reference/interests` | Interest options | Public |
| `GET /v1/plans` | Public active plan/price summaries | Country/currency derived or validated |

Public endpoints have strict API Gateway usage-plan limits and must not reveal whether a contact/account exists.

## 4. Authentication and account

| Method and path | Purpose | Required behavior |
|---|---|---|
| `POST /v1/auth/register` | Start account registration | Generic response; creates verification challenge; idempotent |
| `POST /v1/auth/challenges` | Request login/contact/recovery challenge | Rate-limit contact hash, account, IP, and device via RDS-backed counters |
| `POST /v1/auth/challenges/{challengeId}/verify` | Verify one-time challenge | Bounded attempts, one-time consume, generic failures |
| `POST /v1/auth/login` | Password/provider login where enabled | Session rotation and audit; no account enumeration |
| `POST /v1/auth/refresh` | Rotate refresh token and issue access token | Reuse detection revokes token family |
| `POST /v1/auth/logout` | Revoke current session | Idempotent |
| `POST /v1/auth/logout-all` | Revoke all account sessions | Requires recent authentication |
| `POST /v1/auth/password/forgot` | Start password reset | Generic response |
| `POST /v1/auth/password/reset` | Complete reset | One-time challenge; revoke prior sessions according to policy |
| `GET /v1/me` | Current account, roles, profile access, safe entitlements | Authenticated |
| `PATCH /v1/me` | Locale, timezone, display preferences | `If-Match` |
| `GET /v1/me/contacts` | Masked contacts and verification state | Recent auth for sensitive operations |
| `POST /v1/me/contacts` | Add contact and challenge | Idempotent |
| `POST /v1/me/contacts/{contactId}/verify` | Verify added contact | Challenge proof |
| `DELETE /v1/me/contacts/{contactId}` | Remove non-required contact | Cannot remove last verified login contact |
| `GET /v1/me/sessions` | Active session summaries | No raw token/IP |
| `DELETE /v1/me/sessions/{sessionId}` | Revoke one session | Idempotent |
| `GET /v1/me/consents` | Current and historical consent summary | Authenticated |
| `POST /v1/me/consents` | Record a versioned decision | Append-only; separate marketing/AI/profile consents |
| `POST /v1/me/data-requests` | Request export, correction, or deletion | `202`; recent auth; legal hold/state explained safely |
| `GET /v1/me/data-requests/{requestId}` | Read request status | Owner only |

Refresh-token rotation still uses secure `HttpOnly`, `Secure`, `SameSite` cookies where the client deployment permits; API Gateway proxies cookies/headers transparently, so this needs no special handling.

## 5. Profiles, managers, family, and preferences

### Aggregate and lifecycle

| Method and path | Purpose | Permission/state |
|---|---|---|
| `POST /v1/profiles` | Create candidate draft | Authenticated; idempotent; declares self/other relationship |
| `GET /v1/profiles/{profileId}` | Manager-authorized complete profile view | `profile.read_private` |
| `PATCH /v1/profiles/{profileId}` | Update root fields such as locale | `profile.edit`; `If-Match` |
| `GET /v1/profiles/{profileId}/preview` | Publication preview using viewer rules | `profile.read_private` |
| `GET /v1/profiles/{profileId}/completion` | Deterministic completion score/missing items | Manager read |
| `POST /v1/profiles/{profileId}/submit` | Submit for policy/moderation review | Validates age, consent, required fields, media |
| `POST /v1/profiles/{profileId}/publish` | Publish approved profile | `profile.publish`; idempotent; policy gate |
| `POST /v1/profiles/{profileId}/pause` | Remove from discovery | `profile.publish`; immediate projection event |
| `POST /v1/profiles/{profileId}/resume` | Return eligible profile to discovery | Full publication checks rerun |
| `DELETE /v1/profiles/{profileId}` | Start profile deletion workflow | Recent auth; `202`; blocked by policy/legal holds as applicable |

### Sections

Use one current resource per single-valued section and collection resources for repeated facts.

| Method and path | Purpose |
|---|---|
| `GET/PATCH /v1/profiles/{profileId}/personal-details` | Restricted candidate facts; field-level visibility in response |
| `GET/PATCH /v1/profiles/{profileId}/narratives` | Headline, bios, expectations, family narrative |
| `GET/PATCH /v1/profiles/{profileId}/lifestyle` | Diet, smoking, alcohol, fitness, values, plans |
| `GET/PATCH /v1/profiles/{profileId}/visibility` | Discoverability, photo/name/location/contact policy |
| `GET/PUT /v1/profiles/{profileId}/communities` | Replace reviewed self-declarations |
| `GET/PUT /v1/profiles/{profileId}/religious-practices` | Replace optional self-declared practices |
| `GET/PUT /v1/profiles/{profileId}/languages` | Replace profile language set |
| `GET/PUT /v1/profiles/{profileId}/interests` | Replace interest set |
| `GET/POST /v1/profiles/{profileId}/education` | List/add education records |
| `GET/PATCH/DELETE /v1/profiles/{profileId}/education/{recordId}` | Change/remove one education record |
| `GET/POST /v1/profiles/{profileId}/employment` | List/add employment records |
| `GET/PATCH/DELETE /v1/profiles/{profileId}/employment/{recordId}` | Change/remove one employment record |
| `GET/PUT /v1/profiles/{profileId}/family` | Family summary resource |
| `GET/POST /v1/profiles/{profileId}/family/members` | List/add minimized family members |
| `PATCH/DELETE /v1/profiles/{profileId}/family/members/{memberId}` | Change/remove one family item |
| `GET/PUT /v1/profiles/{profileId}/preferences` | Main partner preferences and priorities |
| `GET/PUT /v1/profiles/{profileId}/preferences/countries` | Country preference set |
| `GET/PUT /v1/profiles/{profileId}/preferences/languages` | Language preference set |
| `GET/PUT /v1/profiles/{profileId}/preferences/communities` | Private community preference set |
| `GET/PUT /v1/profiles/{profileId}/preferences/religious-practices` | Private practice preference set |
| `GET/PUT /v1/profiles/{profileId}/preferences/education-levels` | Education preference set |
| `GET/PUT /v1/profiles/{profileId}/brands` | Brand visibility memberships |
| `GET/PUT /v1/profiles/{profileId}/experiences` | Explicit experience selections |

All writes require `profile.edit`, validate controlled values, append a safe revision, increment profile version when compatibility/discovery input changes, and write an outbox row (published to EventBridge by the outbox-dispatcher Lambda, see §1).

### Managers and consent

| Method and path | Purpose |
|---|---|
| `GET /v1/profiles/{profileId}/managers` | Current and invited managers, masked appropriately |
| `POST /v1/profiles/{profileId}/manager-invitations` | Invite candidate/parent/collaborator with permission set |
| `POST /v1/profile-manager-invitations/{token}/accept` | Accept one-time invitation after authentication |
| `PATCH /v1/profiles/{profileId}/managers/{accountId}` | Change allowed permissions/primary status |
| `DELETE /v1/profiles/{profileId}/managers/{accountId}` | Revoke manager; cannot orphan profile or violate candidate control |
| `POST /v1/profiles/{profileId}/candidate-consent` | Record verified candidate publication/management decision |

## 6. Media and generated documents

| Method and path | Purpose | Notes |
|---|---|---|
| `POST /v1/uploads` | Create upload session and presigned URL | Purpose/content type/size/checksum; idempotent; bytes never pass through API Gateway/Lambda |
| `POST /v1/uploads/{uploadId}/complete` | Confirm object and enqueue processing | `202`; object head/checksum validation; enqueues SQS message for the media worker Lambda |
| `GET /v1/media/{assetId}` | Authorized metadata and short-lived access URL | Never exposes storage bucket/key |
| `DELETE /v1/media/{assetId}` | Remove unused/owned asset or queue policy deletion | Idempotent |
| `GET /v1/profiles/{profileId}/media` | Manager-authorized media collection |
| `POST /v1/profiles/{profileId}/media` | Attach a ready asset | `profile.edit`; idempotent |
| `PATCH /v1/profiles/{profileId}/media/{profileMediaId}` | Primary, visibility, caption, order |
| `DELETE /v1/profiles/{profileId}/media/{profileMediaId}` | Detach and possibly lifecycle asset |
| `POST /v1/profiles/{profileId}/biodata` | Generate versioned biodata | `202`; template/locale only from approved set; rendered by an async Lambda worker, not the API Lambda |
| `GET /v1/profiles/{profileId}/biodata/{documentId}` | Status/short-lived authorized download |

A profile cannot publish with required media still unscanned, rejected, or quarantined. All uploads and downloads use S3 presigned URLs to respect the API Gateway/Lambda payload limits in §1.

## 7. Discovery

| Method and path | Purpose | Notes |
|---|---|---|
| `POST /v1/discovery/search` | Search with validated structured filters | Acting profile required; policy filters always server-applied |
| `GET /v1/discovery/profiles/{profileId}` | Viewer-authorized public profile projection | Records safe view according to policy; no private preferences |
| `GET /v1/discovery/recommendations` | Current curated/rebuildable recommendations | MVP may use deterministic ranking; cursor pagination |
| `POST /v1/discovery/views` | Explicitly record a meaningful profile view if not automatic | Idempotent within dedupe window |
| `GET /v1/saved-searches` | List acting profile's saved searches | Owner only |
| `POST /v1/saved-searches` | Save validated filter/alert preference | Idempotent |
| `PATCH/DELETE /v1/saved-searches/{searchId}` | Update/delete saved search | Owner only |
| `GET /v1/shortlist` | List private shortlist | Acting profile only |
| `PUT /v1/shortlist/{targetProfileId}` | Add/replace note | Idempotent; blocked targets rejected |
| `DELETE /v1/shortlist/{targetProfileId}` | Remove | Idempotent |
| `PUT /v1/hidden-profiles/{targetProfileId}` | Hide from discovery | Idempotent |
| `DELETE /v1/hidden-profiles/{targetProfileId}` | Unhide | Cannot override a safety block |

Search request filters include a version. Unknown fields/operators are rejected, not ignored. Result cursors encode ranking version and expire. `POST /v1/discovery/search` must stay inside the ~20 second synchronous budget from §1; if ranking ever needs heavier computation, it moves to the async `Operation` pattern rather than growing past that budget.

## 8. Compatibility, interests, and matches

| Method and path | Purpose | Notes |
|---|---|---|
| `POST /v1/compatibility-analyses` | Calculate/refresh analysis for acting and target profiles | Returns cached result or `202`; idempotent; policy filtered |
| `GET /v1/compatibility-analyses/{analysisId}` | Score, visible factor summary, explanation state | Never reveals target's hidden preference/dealbreaker |
| `GET /v1/interests?direction=incoming|outgoing&status=` | List interests | Cursor pagination |
| `POST /v1/interests` | Send interest and optional approved introduction | Idempotent; entitlement/rate/block checks |
| `POST /v1/interests/{interestId}/accept` | Accept pending incoming interest | Atomic match/conversation creation |
| `POST /v1/interests/{interestId}/decline` | Decline | Idempotent; optional private reason |
| `POST /v1/interests/{interestId}/withdraw` | Withdraw pending outgoing interest | State-machine guarded |
| `GET /v1/matches` | List active/ended matches | Cursor pagination |
| `GET /v1/matches/{matchId}` | Match summary and conversation link | Participant manager only |
| `POST /v1/matches/{matchId}/end` | Unmatch/end | Immediate conversation policy transition |
| `POST /v1/matches/{matchId}/feedback` | Private feedback | Does not notify other side |
| `POST /v1/matches/{matchId}/outcomes` | Optional success/outcome report | Explicit consent fields; auditable |

## 9. Messaging and real-time

| Method and path | Purpose | Notes |
|---|---|---|
| `GET /v1/conversations` | Authorized conversation summaries/unread counts | Cursor pagination |
| `GET /v1/conversations/{conversationId}` | Conversation and current participants | Current manager permission required |
| `GET /v1/conversations/{conversationId}/messages` | Keyset-paginated authorized messages | Directional cursor; decrypt only after auth |
| `POST /v1/conversations/{conversationId}/messages` | Send text/attachment/system-supported message | Requires `clientMessageId` and idempotency; fast safety policy |
| `PATCH /v1/conversations/{conversationId}/messages/{messageId}` | Edit within policy window | Sender only; `If-Match`; revision recorded |
| `DELETE /v1/conversations/{conversationId}/messages/{messageId}` | User-visible delete according to retention policy | Sender/admin policy; never silent evidence destruction |
| `POST /v1/conversations/{conversationId}/read` | Advance last-read marker | Monotonic and idempotent |
| `POST /v1/conversations/{conversationId}/mute` | Change notification mute | Participant only |

### WebSocket (API Gateway WebSocket API)

This replaces the ALB-fronted, in-process WebSocket design from the monolithic catalog. API Gateway WebSocket connections are handled by stateless Lambda invocations — there is no long-lived socket process to hold connection or presence state in memory.

- **Token issuance:** `POST /v1/realtime-tokens` (REST API, unchanged) returns a short-lived connection token.
- **Connect route (`$connect`):** client connects to the WebSocket API with the token as a query parameter. The `$connect` Lambda validates the token, resolves account/profile/permission context, and upserts a row into `core.realtime_connections` (`connectionId`, `accountId`, `profileId`, `apiGatewayEndpoint`, `connectedAt`). Reject with the appropriate close code if validation fails.
- **Disconnect route (`$disconnect`):** best-effort deletion of the connection row. Network drops do not always fire `$disconnect`, so a scheduled cleanup job also sweeps rows older than the API Gateway idle/connection-duration limits.
- **Default route (`$default`):** handles the small set of client-originated events (`typing.start`, `typing.stop`, optional receipt hints) documented in the monolithic catalog. Every inbound frame is dispatched by an `action` field; durable writes still go through REST, never through this route.
- **Server → client push:** any Lambda (API or async worker) that needs to notify connected clients calls the API Gateway Management API `PostToConnection` using connection IDs looked up from `core.realtime_connections`. A `GoneException` (HTTP 410) means the connection is stale; delete the row and continue.
- **Server events:** identical set to the monolithic catalog — `message.created`, `message.updated`, `message.deleted`, `conversation.read`, `typing.changed`, `operation.updated`, `notification.created`, `match.updated`. Every event includes `eventId`, `type`, `occurredAt`, `resourceId`, and a safe payload.
- **Platform limits:** API Gateway WebSocket connections have a 10-minute idle timeout and a 2-hour maximum connection duration. Clients must send a lightweight heartbeat/ping more often than every 10 minutes and must implement reconnect-with-backoff; the client already needs this because WebSocket delivery is documented as non-durable.
- **Reconnect:** unchanged — clients catch up through the REST cursor endpoints; the WebSocket channel is never the durable source of truth.
- **Authorization re-checks:** connection rows are invalidated (row deleted, client forced to reconnect and re-resolve permissions) on relevant manager/block/sanction changes, same trigger conditions as the monolithic design.

## 10. AI-assisted domain endpoints

There is intentionally no generic public `/ai/chat` endpoint. Every one of these is already `202`-async in the source design, which maps directly onto SQS/EventBridge-triggered Lambda workers calling the OpenAI-compatible or Bedrock adapter — no contract changes needed for the serverless variant.

| Method and path | Capability | Required controls |
|---|---|---|
| `POST /v1/profiles/{profileId}/ai/extraction-drafts` | Parse user text into proposed structured fields | `202`; source text size/consent limits; no automatic apply |
| `POST /v1/profiles/{profileId}/ai/bio-drafts` | Draft approved bio variants | `202`; uses authorized profile facts only |
| `POST /v1/profiles/{profileId}/ai/quality-analyses` | Actionable profile quality review | `202`; deterministic completeness remains separate |
| `POST /v1/profiles/{profileId}/ai-artifacts/{artifactId}/apply` | Apply confirmed extraction/bio artifact | Expected profile/artifact version; field diff shown to caller |
| `POST /v1/discovery/search-drafts` | Convert natural language to editable structured filters | `202`; artifact never executes until client confirms/submits filters |
| `POST /v1/compatibility-analyses/{analysisId}/explanation` | Generate/refresh grounded explanation | `202`; score/factors immutable to LLM |
| `POST /v1/conversations/{conversationId}/assistant-drafts` | Introduction/reply/follow-up/rejection draft | `202`; explicit intent/tone/locale; preview only |
| `POST /v1/conversations/{conversationId}/translation-drafts` | Translate supplied or authorized message | `202`; never sends automatically |
| `POST /v1/conversations/{conversationId}/tone-checks` | Tone/safety feedback | `202`, or bounded synchronous mode only if it fits the ~20 second budget in §1 |
| `GET /v1/ai-artifacts/{artifactId}` | Read authorized structured artifact | Subject permission and expiry checks |
| `POST /v1/ai-artifacts/{artifactId}/feedback` | Rate/categorize output | Idempotent per account/artifact policy |

## 11. Blocks, reports, trust, and verification

| Method and path | Purpose | Notes |
|---|---|---|
| `GET /v1/blocks` | Acting profile's active blocks | Private |
| `PUT /v1/blocks/{targetProfileId}` | Block target immediately | Idempotent; suppresses both-way interaction without notifying target |
| `DELETE /v1/blocks/{targetProfileId}` | Remove block | Does not restore ended match automatically |
| `POST /v1/reports` | Report profile/message/conversation/media | `202` or created; supports existing evidence IDs |
| `GET /v1/reports/{reportId}` | Reporter-safe status | No internal notes/actions that create risk |
| `GET /v1/profiles/{profileId}/trust-summary` | Authorized public/internal trust view | Explainable labels only, no raw risk evidence |
| `GET /v1/profiles/{profileId}/verification-options` | Available checks by country/profile state | Manager only |
| `POST /v1/profiles/{profileId}/verification-requests` | Start check/provider session | Idempotent; `202` when external work begins |
| `GET /v1/verification-requests/{requestId}` | Request status and safe next action | Owner/verifier policy |
| `POST /v1/verification-requests/{requestId}/evidence` | Associate ready restricted asset | Never accepts direct bytes |
| `POST /v1/verification-requests/{requestId}/submit` | Submit complete evidence | `202`; locks submitted evidence |
| `GET /v1/profiles/{profileId}/verification-claims` | Safe claims/status | Visibility-filtered |
| `POST /v1/moderation-actions/{actionId}/appeals` | Appeal eligible action | Authenticated affected account; policy deadline |

## 12. Notifications

| Method and path | Purpose |
|---|---|
| `GET /v1/notifications` | Cursor-paginated in-app notifications |
| `POST /v1/notifications/{notificationId}/read` | Mark one read idempotently |
| `POST /v1/notifications/read-all` | Mark through supplied timestamp/cursor |
| `GET /v1/notification-preferences` | Effective categories/channels/consent |
| `PUT /v1/notification-preferences` | Replace validated preference set |
| `POST /v1/push-endpoints` | Register future web/native endpoint |
| `DELETE /v1/push-endpoints/{endpointId}` | Revoke endpoint |

Notification APIs do not reveal provider destination or delivery internals. Delivery itself happens in an SQS-triggered notification worker Lambda.

## 13. Billing and entitlements

| Method and path | Purpose | Notes |
|---|---|---|
| `POST /v1/billing/checkout-sessions` | Create hosted checkout | Idempotent; server chooses approved price; return provider URL/token only |
| `GET /v1/billing/subscription` | Effective subscription, renewal/cancel state | Account/profile scope policy |
| `POST /v1/billing/subscription/cancel` | Cancel now/end of period per terms | Idempotent |
| `POST /v1/billing/subscription/resume` | Undo scheduled cancellation if allowed | Idempotent |
| `GET /v1/billing/transactions` | Safe invoice/charge/refund history | No payment instrument data |
| `GET /v1/entitlements` | Effective capability/quota view | Server remains authoritative |
| `POST /v1/promo-redemptions` | Apply approved promo to checkout/account | Rate-limited and idempotent |

## 14. Provider webhooks

| Method and path | Purpose | Controls |
|---|---|---|
| `POST /v1/webhooks/billing/{provider}` | Capture payment events | Raw-body signature, timestamp/replay checks, unique external ID, fast `2xx` after durable capture |
| `POST /v1/webhooks/verification/{provider}` | Capture verification events | Provider allowlist/signature/mTLS where supported, durable encrypted capture |
| `POST /v1/webhooks/notifications/{provider}` | Capture delivery/bounce/complaint events | Signature validation and destination minimization |

Webhook endpoints never trust network/profile/account IDs from provider metadata without resolving server-created external references. The webhook Lambda invocation does only signature verification and durable capture (single RDS write / outbox row); all further processing happens asynchronously in worker Lambdas so the webhook response stays comfortably inside the §1 timeout budget.

## 15. Administrative API

All admin routes require strong authentication, scoped roles, reason capture for sensitive reads/actions, rate limits, and immutable audit. Serve them from the same API Gateway/Lambda with route-level authorization rather than a separate listener — there is no ALB/listener concept to split on in this variant; use a distinct API Gateway usage plan and, optionally, a separate custom domain/base path for the admin surface if operational isolation is desired later.

| Area | Baseline endpoints |
|---|---|
| Dashboard | `GET /v1/admin/dashboard`, `GET /v1/admin/health/queues` |
| Accounts/profiles | `GET /v1/admin/accounts`, `GET /v1/admin/accounts/{id}`, `GET /v1/admin/profiles`, `GET /v1/admin/profiles/{id}` |
| Moderation | `GET /v1/admin/moderation/cases`, `POST /v1/admin/moderation/cases/{id}/assign`, `POST /v1/admin/moderation/cases/{id}/actions`, `POST /v1/admin/moderation/cases/{id}/close` |
| Verification | `GET /v1/admin/verification/requests`, `POST /v1/admin/verification/requests/{id}/decisions` |
| Billing/support | `GET /v1/admin/subscriptions`, `GET /v1/admin/transactions`, `GET/POST/PATCH /v1/admin/support/tickets...` |
| Brands/config | `GET/PATCH /v1/admin/brands/{id}`, `GET/PATCH /v1/admin/experiences/{id}`, `GET/PATCH /v1/admin/feature-flags/{key}` |
| Reference data | Reviewed CRUD/deactivate endpoints under `/v1/admin/reference/...`; never hard-delete used options |
| AI operations | `GET /v1/admin/ai/jobs`, `GET /v1/admin/ai/jobs/{id}`, `POST /v1/admin/ai/jobs/{id}/retry`, `POST /v1/admin/ai/capabilities/{key}/disable` |
| Data rights/audit | `GET /v1/admin/data-requests`, state-transition endpoints, and scoped `GET /v1/admin/audit` |

Prompt/model route activation should initially deploy through reviewed configuration/CI. The admin API may expose status and emergency disable but must not become an unaudited arbitrary-prompt editor.

## 16. Status and error conventions

- `200`: successful read/update/action returning resource.
- `201`: resource created; include `Location`.
- `202`: durable async operation accepted.
- `204`: successful idempotent delete/action without body.
- `400`: malformed protocol/JSON.
- `401`: missing/invalid authentication.
- `403`: authenticated but policy denies; do not reveal hidden resource facts.
- `404`: missing or intentionally concealed unauthorized resource.
- `409`: state conflict, duplicate active relationship, or idempotency-body mismatch.
- `412`: stale `If-Match`.
- `422`: semantically invalid fields/state transition.
- `429`: rate/quota limit with safe `Retry-After` (from either API Gateway throttling or the RDS-backed domain limiter in §1).
- `503`: temporary critical dependency unavailable (for example RDS Proxy exhausted, or a Lambda-level timeout guard tripped before API Gateway's own 29-second cutoff); provider-only failures normally surface through async operation state.

Stable domain codes include `PROFILE_NOT_PUBLISHABLE`, `CANDIDATE_CONSENT_REQUIRED`, `PROFILE_VERSION_STALE`, `TARGET_NOT_DISCOVERABLE`, `INTEREST_ALREADY_PENDING`, `INTEREST_STATE_INVALID`, `MATCH_BLOCKED`, `CONVERSATION_ACCESS_DENIED`, `MESSAGE_POLICY_REJECTED`, `MEDIA_NOT_READY`, `ENTITLEMENT_REQUIRED`, `AI_CAPABILITY_DISABLED`, and `OPERATION_RETRYABLE`.

## 17. API release gate

- Generated OpenAPI validates and contains no undocumented route.
- Contract tests cover auth, scope, idempotency, concurrency, pagination, error shape, and field redaction.
- Object-level authorization tests attempt cross-account, cross-profile, cross-brand, and cross-network access.
- Rate limits and body/upload limits are tested, including the API Gateway usage-plan layer and the RDS-backed domain limiter.
- Serverless-specific checks: cold-start p95 latency budget, Lambda timeout guard fires before API Gateway's 29-second cutoff, RDS Proxy connection exhaustion under concurrent load, and WebSocket `$connect`/`$disconnect`/`$default` behavior including stale-connection cleanup.
- No response leaks contacts, hidden preferences, raw provider payloads, storage keys, secrets, private moderation evidence, or AI prompts.
- A backend-only E2E client can complete the full MVP journey before frontend work starts.
