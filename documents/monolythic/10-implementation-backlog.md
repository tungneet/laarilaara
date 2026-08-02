# End-to-end implementation backlog

## How to execute this list

- Work top to bottom unless dependencies explicitly permit parallel work.
- Each row is intended to be one focused pull request. Split it into suffixed child tasks (`PRO-004a`, `PRO-004b`) if the implementation exceeds a reviewable change; do not silently broaden scope.
- A task is complete only after the global definition of done in `README.md`: implementation, rejection paths, authorization, migrations/contracts/events, tests, observability, documentation, and rollback/compatibility.
- `Depends on` lists hard prerequisites, not every related task.
- Check a task only after its acceptance condition is evidenced in CI or the relevant environment.
- Backend work stops at `GATE-BE-001`; frontend tasks must not start before that gate unless explicitly limited to non-code research.
- Do not place real credentials or user data in code, fixtures, documentation, AI evaluations, tickets, or chat.

Status legend: `[ ]` not started, `[x]` completed, `[!]` blocked with reason recorded.

---

## Phase 0 — decisions and policy inputs

| Status | ID | Task | Depends on | Done when |
|---|---|---|---|---|
| [ ] | DEC-001 | Confirm backend technical defaults | — | TypeScript/Node LTS/NestJS/pnpm/Prisma/PostgreSQL/Redis/Terraform choices in the decision register are accepted or replaced with rationale before scaffolding. |
| [ ] | DEC-002 | Select launch countries, legal entity, minimum-age rules, and governing terms | — | Legal/product owner records supported countries, configurable eligibility rule, and public-beta restrictions; no claim of legal compliance is inferred by engineering. |
| [ ] | DEC-003 | Approve candidate/parent profile-management consent policy | DEC-002 | Self, parent, guardian, collaborator permissions, candidate verification, publication consent, revocation, and exceptional cases are unambiguous. |
| [ ] | DEC-004 | Approve initial identity/reference vocabulary | DEC-002 | Languages, countries, community/religious-practice wording, gender/match preferences, marital history, education, occupation, and “prefer not to say” behavior are reviewed and versionable. |
| [ ] | DEC-005 | Approve compatibility policy v1 | DEC-004 | Eligibility, directional factors, weights, dealbreakers, hidden-factor display, score/band wording, and human-review test cases are signed off. |
| [ ] | DEC-006 | Approve chat, contact-sharing, attachment, moderation, sanctions, appeals, and retention policy | DEC-002 | Every chat/report/moderation state has owner, retention, visibility, response target, and appeal behavior. |
| [ ] | DEC-007 | Select authentication and notification channels | DEC-002 | Launch login methods, transactional email provider, optional SMS/WhatsApp scope, consent, sender registration, and fallback are recorded. |
| [ ] | DEC-008 | Select payment/verification providers and commercial rules | DEC-002 | Countries/currencies/prices/tax/refund/renewal rules, hosted checkout, verification claims, provider sandboxes, and manual fallback are recorded. |
| [ ] | DEC-009 | Approve AI processing policy | DEC-002 | Allowed data/providers/regions, OpenAI local-only policy, Bedrock production policy, retention, opt-out, disclosures, capability limits, and fallback restrictions are recorded. |
| [ ] | DEC-010 | Select AWS region and availability/cost baseline | DEC-002 | Primary region, production two-task/Multi-AZ decisions, initial RPO/RTO, residency rationale, and calculator owner are recorded. |
| [ ] | DEC-011 | Approve brand/domain/experience model | — | LaaraLaari canonical domain, secondary-domain redirect/resolve behavior, Amritdhari/NRI/etc. experience names, SEO ownership, and self-identification rules are recorded. |
| [ ] | DEC-012 | Approve SLOs, retention schedule, analytics consent, and launch success metrics | DEC-002, DEC-006 | Product/security/legal owners accept initial performance/availability targets, per-data retention, analytics categories, and beta metrics. |

---

## Phase 1 — repository and development foundation

| Status | ID | Task | Depends on | Done when |
|---|---|---|---|---|
| [ ] | FND-001 | Initialize private Git repository and protected main branch | DEC-001 | Repository has initial commit, `.gitignore`, license/proprietary notice, branch protection plan, PR template, CODEOWNERS, and backlog ID convention. |
| [ ] | FND-002 | Scaffold pinned pnpm TypeScript workspace | FND-001 | Node/package-manager versions are pinned; `apps`, `packages`, `tests`, `scripts`, and `infra` layout builds on Windows/Linux with frozen lockfile. |
| [ ] | FND-003 | Add formatting, linting, strict types, commit checks, and architecture rules | FND-002 | One command fails on formatting/type/import-boundary/cycle violations; generated/vendor files are correctly excluded. |
| [ ] | FND-004 | Scaffold API and worker applications | FND-002 | NestJS API and worker boot independently, share contracts/platform packages, expose version/build metadata, and shut down cleanly. |
| [ ] | FND-005 | Implement typed configuration and secret-safe environment loading | FND-004 | Invalid config fails at startup; `.env.example` is safe; tests isolate env; production does not read local dotenv; logs redact configuration values. |
| [ ] | FND-006 | Add local Docker Compose dependencies | FND-002 | PostgreSQL, Redis, MinIO, Mailpit, and optional scanner start with health checks and localhost-only ports; setup/down/reset scripts are cross-platform. |
| [ ] | FND-007 | Add liveness, readiness, graceful shutdown, and build endpoint | FND-004, FND-005 | Health probes distinguish process and dependency readiness without leaking internals; shutdown drains HTTP/worker work. |
| [ ] | FND-008 | Implement request context and RFC 9457 errors | FND-004 | Request/correlation/trace IDs, actor/network/brand context slots, stable problem details, validation errors, and redacted exception handling are tested. |
| [ ] | FND-009 | Establish unit/integration/E2E test harness | FND-003, FND-006 | Deterministic unit tests, isolated PostgreSQL/Redis integration tests, API test client, factories, fake clock/IDs/providers, and coverage reports run locally/CI. |
| [ ] | FND-010 | Add OpenAPI and JSON Schema generation/checks | FND-004, FND-003 | OpenAPI 3.1 and event/output schemas are reproducibly generated; CI detects drift and invalid examples. |
| [ ] | FND-011 | Add baseline security/supply-chain checks | FND-002 | Secret, dependency/license, SAST, container, and IaC scan scripts exist with documented suppression/expiry process and fail on unaccepted critical/high issues. |
| [ ] | FND-012 | Create pull-request CI pipeline | FND-003, FND-009, FND-010, FND-011 | GitHub Actions uses least privileges, frozen install/cache, checks/tests/build/scans, cancellation, artifact retention, and never exposes secrets to forks. |
| [ ] | FND-013 | Add developer setup and contribution guide | FND-005, FND-006, FND-009 | A clean Windows/Linux machine can execute documented setup, verify, reset, and troubleshooting steps with synthetic data only. |

---

## Phase 2 — database, platform primitives, and asynchronous foundation

| Status | ID | Task | Depends on | Done when |
|---|---|---|---|---|
| [ ] | DAT-001 | Configure PostgreSQL/Prisma schemas and extensions | FND-006, DEC-001 | All logical schemas exist through migration; approved extensions are explicit; empty migration applies and rolls forward in integration test. |
| [ ] | DAT-002 | Implement migration runner and database roles | DAT-001 | Separate migration/application/read-only role contracts, advisory lock, timeouts, TLS configuration, and one-off runner are tested. |
| [ ] | DAT-003 | Implement UUIDv7, clock, money, locale, cursor, and version primitives | FND-009 | Shared value types validate/serialize consistently; cursors are signed/expiring; optimistic-version helpers have rejection tests. |
| [ ] | DAT-004 | Implement encryption, keyed lookup hashing, and token hashing adapters | FND-005, FND-009 | Local and AWS-KMS-facing interfaces exist; ciphertext binds context/version; hashes never expose values; rotation path and test vectors pass. |
| [ ] | DAT-005 | Establish transaction/repository conventions | DAT-001, DAT-003 | Transaction context, module-owned repositories, same-network checks, pagination, query logging redaction, and rollback tests are reusable. |
| [ ] | DAT-006 | Build versioned synthetic seed framework | DAT-001, DEC-004, DEC-011 | Idempotent reference/demo seed creates fictional actors/profiles/states and can reset without real data or external calls. |
| [ ] | EVT-001 | Create outbox, inbox, scheduled-job, idempotency, and async-operation tables | DAT-001 | Migrations match the database blueprint with unique/partial indexes, leases, retention fields, and constraint tests. |
| [ ] | EVT-002 | Implement versioned event/job envelope contracts | FND-010, EVT-001 | Envelope/schema registry validates samples, rejects unsupported versions, minimizes sensitive data, and preserves correlation/causation/version. |
| [ ] | EVT-003 | Implement transactional outbox writer | DAT-005, EVT-002 | Domain state and outbox append commit/rollback together; duplicate IDs and prohibited payload fields are tested. |
| [ ] | EVT-004 | Implement leased outbox dispatcher | EVT-003 | Batched `SKIP LOCKED` claiming, publish acknowledgement, lease expiry, retry classification, graceful shutdown, metrics, and crash/duplicate tests pass. |
| [ ] | EVT-005 | Implement local queue/event adapters | FND-006, EVT-002 | Redis/BullMQ adapters route named jobs, apply retry/timeout/concurrency, and satisfy transport contract tests without AWS. |
| [ ] | EVT-006 | Implement inbox/idempotent consumer framework | EVT-001, EVT-005 | Duplicate and out-of-order delivery causes one business effect; processing/failure state and transaction behavior are tested. |
| [ ] | EVT-007 | Implement PostgreSQL scheduler | EVT-001, EVT-005 | Due jobs are claimed with leases/dedupe, enqueued once at effect level, recover after crash, and expose lag metrics. |
| [ ] | EVT-008 | Implement async operations API and realtime-ready status publisher | EVT-001, FND-008 | `GET /v1/operations/{id}` authorization/state/expiry works; `202` helper sets `Location`; terminal/stale/cancel behavior is tested. |
| [ ] | EVT-009 | Implement retry, quarantine, and selective replay tooling | EVT-004, EVT-006 | Operators can inspect safe metadata and replay one/range with reason/audit; poison events do not block queues; no raw sensitive payload is printed. |
| [ ] | EVT-010 | Complete event reliability test suite | EVT-004, EVT-006, EVT-007, EVT-009 | Commit/crash/publish/consume/retry/DLQ/stale-version scenarios prove no lost committed event and no duplicate business effect. |

---

## Phase 3 — network, brands, reference data, identity, and consent

| Status | ID | Task | Depends on | Done when |
|---|---|---|---|---|
| [ ] | BRD-001 | Migrate networks, brands, domains, experiences, and feature flags | DAT-005, DEC-011 | Tables/constraints/seeds include one LaaraLaari network, host uniqueness, redirect-cycle prevention, and configurable experience defaults. |
| [ ] | BRD-002 | Implement trusted host/network/brand resolution | BRD-001, FND-008 | Allowed hosts resolve immutable request context; unknown/spoofed forwarded hosts fail safely; proxy trust is explicit and tested. |
| [ ] | BRD-003 | Implement public context endpoint and cache | BRD-002 | `GET /v1/context` returns locale/theme/content/experience/flag-safe data, supports ETag/brief cache, and invalidates after configuration events. |
| [ ] | BRD-004 | Implement server-side feature flag evaluator | BRD-001 | Network/account/percentage/allowlist rules are deterministic, auditable, fail-safe, and cannot be overridden by client claims. |
| [ ] | REF-001 | Migrate and seed controlled reference data | DAT-006, DEC-004 | Country/region/language/community/practice/education/occupation/interest/relationship tables and reviewed localized seed version are applied. |
| [ ] | REF-002 | Implement public reference endpoints | REF-001, BRD-002 | Locale-aware active lists support ETag/cache and never expose internal/deactivated/private metadata. |
| [ ] | IAM-001 | Migrate identity and consent tables | DAT-004, BRD-001 | Account/contact/auth/challenge/session/role/invitation/consent/device tables have network constraints, hashes, encrypted fields, and indexes. |
| [ ] | IAM-002 | Implement account/contact repository and masking | IAM-001 | Email/phone normalize, keyed-hash uniquely, encrypt, mask, and never enter logs/errors; duplicate/contact-enumeration tests pass. |
| [ ] | IAM-003 | Implement auth challenge service and fake/email adapters | IAM-002, EVT-003, DEC-007 | Purpose-bound expiring one-time challenge has attempt/cooldown/rate limits, generic response, delivery event, and deterministic fake adapter. |
| [ ] | IAM-004 | Implement registration and configured login methods | IAM-003 | Register/verify/login/recovery state machine follows approved methods, checks eligibility/terms, prevents enumeration, and emits audit/events. |
| [ ] | IAM-005 | Implement access/refresh sessions and token-family rotation | IAM-004 | Short access token, hashed rotating refresh token, secure-cookie contract, reuse detection, logout/current/all revocation, and clock-skew tests pass. |
| [ ] | IAM-006 | Implement authentication, network, and acting-profile guards | IAM-005, BRD-002 | Request actor derives only from verified token/session; host/network mismatch, suspended/revoked state, and forged acting profile are denied. |
| [ ] | IAM-007 | Implement roles, permissions, and scoped admin/service authorization | IAM-006 | Seeded role permissions and scope/expiry checks are centralized; no super-admin bypass; negative matrix and audit hooks pass. |
| [ ] | IAM-008 | Implement account, contact, and session APIs | IAM-005, IAM-006 | `/me`, masked contacts, verification, session list/revoke, profile access summary, concurrency and recent-auth checks conform to OpenAPI. |
| [ ] | IAM-009 | Implement versioned consent APIs and enforcement service | IAM-006, DEC-003, DEC-009 | Separate terms/privacy/profile/AI/marketing decisions are append-oriented, withdrawable where applicable, and checked by capabilities. |
| [ ] | IAM-010 | Implement invitation/token framework | IAM-003, IAM-009 | One-time expiring masked-target invitations accept only after verified auth, enforce permission payload, and resist replay/enumeration. |
| [ ] | IAM-011 | Add auth abuse controls and security audit | IAM-003, IAM-005, IAM-007 | Distributed fail-safe rate limits, suspicious reuse/role/contact events, generic errors, safe audit, and alert metrics are covered. |
| [ ] | IAM-012 | Require MFA/recent auth for privileged roles/actions | IAM-007, DEC-007 | Admin/moderator/verifier/support access cannot proceed without approved second factor; recovery and downgrade are audited/tested. |
| [ ] | IAM-013 | Complete identity authorization/E2E suite | IAM-008, IAM-009, IAM-010, IAM-012 | Registration through refresh/recovery/contact/session/consent/invite/MFA journeys and cross-network/abuse cases pass. |
| [ ] | BRD-005 | Implement audited brand/experience/flag admin APIs | BRD-003, IAM-007 | Scoped admin can validate/version/activate config; unsafe host/redirect/theme/rule input is rejected; every change emits event/audit. |
| [ ] | REF-003 | Implement audited reference admin lifecycle | REF-001, IAM-007 | Admin can add/localize/reorder/deactivate but cannot destroy used history; changes invalidate cache and are tested. |

---

## Phase 4 — profiles and media

| Status | ID | Task | Depends on | Done when |
|---|---|---|---|---|
| [ ] | PRO-001 | Migrate profile aggregate, sections, preferences, managers, and revisions | IAM-001, REF-001, DEC-003, DEC-004 | Profile tables/constraints/visibility/version fields match blueprint and enforce same-network references/range checks. |
| [ ] | PRO-002 | Implement profile root create/read/update | PRO-001, IAM-006 | Self/other relationship creates a draft idempotently; private view/update requires permission and ETag/`If-Match`. |
| [ ] | PRO-003 | Implement profile managers and candidate consent | PRO-002, IAM-010, DEC-003 | Invite/accept/change/revoke/primary/candidate-control flows cannot orphan or self-escalate; publication permission reacts immediately. |
| [ ] | PRO-004 | Implement personal details API | PRO-002 | Birth/name/location/residency/marital/gender fields validate approved policy, encrypt restricted values, version relevant changes, and return field-authorized views. |
| [ ] | PRO-005 | Implement narratives and lifestyle APIs | PRO-002 | Plain-text limits, moderation state, approved controlled values, versioning, and no-contact leakage validation pass. |
| [ ] | PRO-006 | Implement communities, practices, languages, and interests APIs | PRO-002, REF-002 | Replace-set semantics validate active references, explicit self-declaration/visibility, idempotency, and no inference. |
| [ ] | PRO-007 | Implement education and employment APIs | PRO-002, REF-002 | Collection CRUD validates date/order/current rules, verification references, visibility, pagination/order, and optimistic profile version. |
| [ ] | PRO-008 | Implement family profile/member APIs | PRO-002, DEC-003 | Minimal optional family data, visibility, ordering, no minor/contact collection, and manager permission checks pass. |
| [ ] | PRO-009 | Implement partner preference APIs | PRO-002, DEC-005 | Main/ranged and reference-set preferences validate private visibility/dealbreaker levels and increment compatibility input version. |
| [ ] | PRO-010 | Implement brand memberships and experience selections | PRO-002, BRD-001 | Profile can opt into multiple experiences/brands in same network without duplication; discovery flags and events are correct. |
| [ ] | PRO-011 | Implement profile visibility and authorized view mapper | PRO-004, PRO-005, PRO-006, PRO-007, PRO-008, PRO-009 | Owner/manager/discovery/matched/moderator views expose only allowed fields; hidden preferences/legal name/DOB/contact never leak. |
| [ ] | PRO-012 | Implement deterministic completion projector | PRO-004, PRO-005, PRO-006, PRO-007, PRO-008, EVT-006 | Profile events recalculate versioned score/missing items idempotently; synchronous fallback returns consistent result. |
| [ ] | MED-001 | Migrate media/upload/document tables and storage interfaces | DAT-004, PRO-001 | MinIO/S3-compatible adapter, object key policy, separate media/restricted classes, metadata tables, and fake scanner interfaces exist. |
| [ ] | MED-002 | Implement constrained presigned upload sessions | MED-001, IAM-006 | Purpose/type/size/checksum/expiry/quota are server-defined; complete verifies object; keys/buckets stay private; abuse tests pass. |
| [ ] | MED-003 | Implement quarantine and malware/type scan worker | MED-002, EVT-006 | Upload event queues scan; spoofed/unsafe/archive/malware files quarantine; retries/state/audit/user-safe operation status work. |
| [ ] | MED-004 | Implement image normalization, metadata removal, and variants | MED-003 | Pixel/decompression limits, orientation, re-encode, metadata removal, deterministic variants, and original isolation are tested. |
| [ ] | MED-005 | Implement media content moderation boundary | MED-003 | Fake/provider adapter produces versioned decision; uncertain/rejected items create review/quarantine and cannot publish. |
| [ ] | MED-006 | Implement profile media attach/order/visibility/primary APIs | MED-004, MED-005, PRO-011 | Only owned ready assets attach; one primary constraint, visibility-authorized signed access, detach/delete lifecycle, and events pass. |
| [ ] | MED-007 | Implement generated biodata worker and API | MED-006, EVT-008 | Approved template/locale renders only visibility-safe fields to private expiring asset; operation/version/authorization tests pass. |
| [ ] | MED-008 | Complete media security and lifecycle suite | MED-007 | MIME spoof/malware/bomb/metadata/key/signed-URL/quarantine/delete/retention and cross-profile/network cases pass. |
| [ ] | PRO-013 | Implement submit/publish/pause/resume lifecycle | PRO-003, PRO-011, PRO-012, MED-006 | State machine enforces age/candidate consent/completion/media/moderation; transitions emit minimized events and are idempotent. |
| [ ] | PRO-014 | Implement preview, revisions, and concurrency audit | PRO-011, PRO-013 | Preview matches public policy; safe changed-field revisions and ETags expose stale conflicts without storing secret values. |
| [ ] | PRO-015 | Complete profile E2E and authorization suite | PRO-014 | Self/parent/collaborator journeys, revocation, every section, visibility views, stale writes, lifecycle, brand/network isolation pass. |

---

## Phase 5 — blocking, discovery, compatibility, interests, matches, and messaging

| Status | ID | Task | Depends on | Done when |
|---|---|---|---|---|
| [ ] | TRU-001 | Migrate block/report/moderation/risk/sanction/appeal tables | PRO-001, IAM-007, DEC-006 | Trust tables, restricted encrypted notes, active-pair/case indexes, expiry/status constraints, and audit references exist. |
| [ ] | TRU-002 | Implement immediate block/unblock service and APIs | TRU-001, IAM-006 | Idempotent block hides both directions, denies interests/chat/recommendations, cancels relevant notifications, emits event, and never alerts target. |
| [ ] | DSC-001 | Migrate and implement profile search projection worker | PRO-013, EVT-006, TRU-002 | Version-aware projection contains only discoverable safe fields, removes paused/blocked state as designed, and rebuild command is idempotent. |
| [ ] | DSC-002 | Define versioned structured search specification | DEC-005, DSC-001 | Allowed filters/operators/sorts/ranges, privacy rules, validation schema, canonical normalization, and examples are contract-tested. |
| [ ] | DSC-003 | Implement indexed search with policy filters and keyset cursors | DSC-002, PRO-011 | Search always enforces network/publication/visibility/age/block/dealbreakers, has stable expiring cursors, and meets representative query plans. |
| [ ] | DSC-004 | Implement discovery profile view and view events | DSC-003 | Viewer-safe profile endpoint records deduped meaningful view only when permitted; private-view setting and blocked/hidden cases pass. |
| [ ] | DSC-005 | Implement shortlist and hidden-profile APIs | DSC-003 | Private idempotent add/remove/note/hide behavior is authorized, encrypted where needed, and block remains stronger than unhide. |
| [ ] | DSC-006 | Implement saved searches and alert schedule | DSC-002, EVT-007 | Validated versioned filters save/update/delete, schedule with dedupe, obey current visibility/preferences, and respect notification consent. |
| [ ] | MAT-001 | Implement versioned compatibility policy engine | DEC-005, PRO-009 | Hard eligibility and directional normalized factors/weights/reason codes are deterministic, bounded, transparent, and counterexample-tested. |
| [ ] | MAT-002 | Migrate/persist compatibility policies, scores, and factors | MAT-001, EVT-003 | Canonical pair/input versions/policy uniqueness, expiry/invalidation, visible factor view, and no hidden-preference leakage pass. |
| [ ] | MAT-003 | Implement compatibility analysis API/operation | MAT-002, EVT-008 | Cached current score returns immediately; refresh is idempotent async; viewer-safe factors and stale-input handling conform to contract. |
| [ ] | DSC-007 | Implement deterministic MVP recommendation list | DSC-003, MAT-002 | Reuses eligibility/compatibility, excludes viewed/hidden/blocked/active relationships per policy, version/rank is reproducible, and no behavioral AI is implied. |
| [ ] | DSC-008 | Complete discovery query/load/privacy suite | DSC-004, DSC-005, DSC-006, DSC-007 | 10k synthetic profiles meet p95 target; cursor/change, scrape limits, hidden fields, cross-network and block tests pass. |
| [ ] | MAT-004 | Migrate and implement interest state machine | PRO-013, TRU-002 | Send/accept/decline/withdraw/expire rules reject self/hidden/blocked/duplicate/invalid transitions and preserve canonical states under races. |
| [ ] | MAT-005 | Implement interest list/send/respond APIs | MAT-004, EVT-003 | Incoming/outgoing cursor lists, entitlements/rates, optional safe intro reference, idempotency, events, and private decline reason pass. |
| [ ] | MSG-001 | Migrate conversation/message/participant/receipt tables | MAT-004, DAT-004 | Chat schema has encrypted body, retry uniqueness, ordered indexes, attachment/policy/revision fields, and same-network constraints. |
| [ ] | MAT-006 | Implement atomic interest acceptance, match, and conversation creation | MAT-005, MSG-001 | One transaction accepts once, creates one canonical match/conversation/participants/outbox events; concurrent retries return same result. |
| [ ] | MAT-007 | Implement match list/detail/end/feedback/outcome APIs | MAT-006 | Participant authorization, block/sanction state, private feedback, consensual outcome data, events, and idempotent end behavior pass. |
| [ ] | MAT-008 | Complete matchmaking race/authorization suite | MAT-003, MAT-007 | Duplicate sends/accepts, crossed interests, blocks during acceptance, stale versions, hidden factors, and network boundaries pass. |
| [ ] | MSG-002 | Implement conversation participant authorization service | MSG-001, PRO-003, TRU-002 | Every read/send derives current manager permission, acting profile, match/block/sanction state; revocation takes effect immediately. |
| [ ] | MSG-003 | Implement encrypted text message send/list API | MSG-002, DAT-004 | Client message ID/idempotency, size/format/reply/state checks, durable event, keyset list/decrypt-after-auth, and safe errors pass. |
| [ ] | MSG-004 | Implement message edit/delete/revision policy | MSG-003, DEC-006 | Sender/time-window/state rules, encrypted revisions, evidence/legal-hold behavior, events, and viewer rendering status pass. |
| [ ] | MSG-005 | Implement receipts, unread counts, and mute state | MSG-003 | Monotonic read marker, authorized receipt visibility, efficient unread projection, idempotency, and notification suppression pass. |
| [ ] | MSG-006 | Implement WebSocket token, connection auth, and durable fan-out | MSG-003, IAM-005 | Short token, origin/connection limits, resource-safe events, reconnect REST catch-up, revoked/blocked disconnect, and multi-task adapter tests pass. |
| [ ] | MSG-007 | Implement ephemeral typing/presence | MSG-006, FND-006 | Redis TTL state is bounded/non-authoritative, permission-checked, rate-limited, and disappears safely on Redis/reconnect loss. |
| [ ] | MSG-008 | Implement safe message attachments | MSG-003, MED-006, DEC-006 | Only ready allowed assets attach; download reauthorizes; file policy/quota/evidence/deletion behavior and no raw URL leakage pass. |
| [ ] | MSG-009 | Implement deterministic fast chat safety checks | MSG-003, DEC-006 | Prohibited file/link/payment/contact/abuse patterns follow approved reject/warn/quarantine policy without logging body; false-positive fixtures pass. |
| [ ] | MSG-010 | Complete secure chat E2E/load suite | MSG-004, MSG-005, MSG-006, MSG-008, MSG-009 | Message/retry/edit/read/reconnect/block/revoke/sanction/attachment/evidence/encryption and concurrent fan-out meet targets. |

---

## Phase 6 — reports, moderation, verification, notifications, and billing

| Status | ID | Task | Depends on | Done when |
|---|---|---|---|---|
| [ ] | TRU-003 | Implement report intake/evidence/status APIs | TRU-001, MSG-003, MED-006 | Reporter can submit authorized profile/message/media evidence, gets safe status, cannot expose target/private moderator data, and duplicate abuse is controlled. |
| [ ] | TRU-004 | Implement moderation case queue and assignment | TRU-003, IAM-012 | Reports/signals group into prioritized SLA cases; scoped reviewers claim/assign with race protection and restricted evidence access audit. |
| [ ] | TRU-005 | Implement moderation actions and sanction enforcement | TRU-004 | Versioned reason/action creates current sanction and owning modules enforce it; high-impact action needs configured human approval and notification. |
| [ ] | TRU-006 | Implement appeals and reversal workflow | TRU-005 | Eligible account appeals within policy; separate reviewer where configured; reversal updates sanction, restores only allowed state, and audits decision. |
| [ ] | VER-001 | Migrate verification tables and define provider interface | TRU-001, DEC-008 | Check/request/evidence/claim/provider-event/review schema and fake/provider contracts model approved claims without public raw data. |
| [ ] | VER-002 | Implement verification options/start/status APIs | VER-001, PRO-011 | Country/profile/check eligibility, idempotent provider session, operation/status, authorization, expiry, and safe next-action response pass. |
| [ ] | VER-003 | Implement restricted evidence upload/retention | VER-002, MED-003 | Evidence uses dedicated storage/access role/KMS/lifecycle, associates only ready objects, locks on submit, and access is case-audited. |
| [ ] | VER-004 | Implement provider webhook/poll processing and manual review | VER-002, EVT-006 | Signature/replay/idempotency, normalized state, bounded polling, human fallback, encrypted short-retention payload, and reconciliation pass. |
| [ ] | VER-005 | Implement verification claims, expiry, revocation, and safe profile view | VER-004 | Claim source/date/expiry is traceable; public view shows only approved label/status/date; profile/trust updates are event-driven. |
| [ ] | VER-006 | Complete verification security/E2E suite | VER-003, VER-005 | Fake provider success/fail/duplicate/out-of-order/expiry/review/purge and unauthorized evidence access tests pass. |
| [ ] | TRU-007 | Implement explainable trust summary v1 | TRU-005, VER-005 | Deterministic versioned factors use verification/safety state; public/internal views differ; no opaque AI verdict or raw evidence leaks. |
| [ ] | TRU-008 | Complete moderation safety/privacy suite | TRU-006, TRU-007 | Reporter privacy, evidence access, SLA, sanction propagation, appeal, false signal, block precedence, audit and cross-scope tests pass. |
| [ ] | NOT-001 | Migrate notification tables and define channel interfaces | IAM-002, DEC-007 | Preferences/templates/in-app/delivery/endpoints schema and fake/email adapters use destination references, not raw logged contacts. |
| [ ] | NOT-002 | Implement notification preference APIs | NOT-001, IAM-009 | Category/channel/frequency/quiet hours validate legal transactional exceptions and marketing consent; replace-set is idempotent. |
| [ ] | NOT-003 | Implement versioned brand/locale template renderer | NOT-001, BRD-003 | Allowed variables only, escaped output, snapshot review, fallback locale, and no arbitrary template execution/private text pass. |
| [ ] | NOT-004 | Implement event-to-notification policy composer | NOT-002, NOT-003, EVT-006 | Domain events create deduped in-app/delivery intents only when preferences/block/mute/state allow; no business decision lives in provider adapter. |
| [ ] | NOT-005 | Implement in-app notification APIs and realtime fan-out | NOT-004, MSG-006 | List/read/read-all cursor semantics, expiry, authorization, operation/match/message-safe actions, and realtime hint pass. |
| [ ] | NOT-006 | Implement email delivery, retries, bounce/complaint suppression | NOT-004 | Mailpit/fake and provider adapter classify errors, respect retry/idempotency, store masked refs, suppress permanent failures, and emit metrics. |
| [ ] | NOT-007 | Complete notification preference/dedup/privacy suite | NOT-005, NOT-006 | Duplicate/out-of-order events, blocks/mutes/quiet hours/consent/bounce/provider outage and no-private-message-preview tests pass. |
| [ ] | BIL-001 | Migrate billing/entitlement tables and provider interface | DEC-008, IAM-001 | Plans/prices/customers/subscriptions/transactions/webhooks/grants schema uses minor currency units/external uniqueness and stores no card data. |
| [ ] | BIL-002 | Implement plan/price and entitlement evaluator APIs | BIL-001 | Public active plans localize safely; server computes effective quotas/capabilities from grants; cache invalidates on events. |
| [ ] | BIL-003 | Implement hosted checkout session API with fake provider | BIL-002, IAM-006 | Server selects approved price, idempotently creates safe hosted checkout reference, applies promo constraints, and never accepts arbitrary amount. |
| [ ] | BIL-004 | Implement signed webhook capture and async normalization | BIL-001, EVT-006 | Raw-body signature/timestamp/replay check, durable encrypted envelope, unique event, quick response, and duplicate/out-of-order processing pass. |
| [ ] | BIL-005 | Implement subscription/transaction/entitlement state projectors | BIL-004 | Provider states map deterministically; charges/refunds append; grants update atomically; reconciliation corrects drift without duplicate access. |
| [ ] | BIL-006 | Implement subscription/history/cancel/resume APIs | BIL-005 | Owner sees safe current/history state, terms determine transitions, recent auth/idempotency apply, and notifications/events are correct. |
| [ ] | BIL-007 | Implement billing reconciliation and support operations | BIL-005, IAM-012 | Scheduled reconciliation finds external/internal mismatch, queues audited remediation, and support can inspect/refund only through scoped provider flow. |
| [ ] | BIL-008 | Complete billing security/E2E suite | BIL-003, BIL-006, BIL-007 | Success/failure/refund/cancel/renew/duplicate/replay/out-of-order/tax-currency/promo/entitlement/provider-outage cases pass with no card data. |

---

## Phase 7 — AI capability layer

| Status | ID | Task | Depends on | Done when |
|---|---|---|---|---|
| [ ] | AIF-001 | Migrate AI config/prompt/job/artifact/feedback/evaluation tables | DAT-005, DEC-009 | Tables enforce immutable prompt versions, subject/version artifacts, no raw prompt default, route aliases, cost metadata, and network scope. |
| [ ] | AIF-002 | Define capability/provider/router/prompt contracts and fake adapter | AIF-001, FND-010 | Provider-neutral interfaces and deterministic fake satisfy structured-output/error/usage contracts; domain imports no provider SDK. |
| [ ] | AIF-003 | Implement capability authorization, consent, entitlement, and quota gate | AIF-002, IAM-009, BIL-002 | Every job checks actor/profile/network/consent/flag/entitlement/input size/concurrency/spend before durable enqueue; denial is safe/audited. |
| [ ] | AIF-004 | Implement prompt registry and model route activation | AIF-002, BRD-004 | Immutable prompt/schema/policy versions and model aliases activate atomically, support capability kill switch/fallback, and never store secrets. |
| [ ] | AIF-005 | Implement AI job/orchestrator/artifact/feedback APIs | AIF-003, AIF-004, EVT-008 | Idempotent version-bound jobs return operations; authorized artifact retrieval/feedback/apply hooks handle stale/expired/rejected states. |
| [ ] | AIF-006 | Implement input minimization, redaction, and injection-resistant builders | AIF-005 | Capability allowlists exclude contacts/documents/hidden facts/unrelated chat; untrusted text is delimited; inspection tests find no prohibited data. |
| [ ] | AIF-007 | Implement structured output, grounding, and safety validation | AIF-006 | Strict schemas reject unknown/prose/invalid refs; factual claims map to supplied evidence; unsafe/leaking output fails without replacing approved state. |
| [ ] | AIF-008 | Implement OpenAI-compatible development adapter | AIF-002, AIF-007 | Optional secret-safe adapter applies timeout/retry/usage/model alias/structured output and shared contracts using synthetic test data only. |
| [ ] | AIF-009 | Implement Bedrock adapter | AIF-002, AIF-007 | Task-role credentials, approved model alias/region, structured output, timeout/throttle/usage, and shared contracts work in AWS development. |
| [ ] | AIF-010 | Build versioned AI evaluation/red-team harness | AIF-007 | Synthetic datasets, metrics, blocking safety checks, provider comparison, cost/latency summary, and reproducible code/prompt/model/data version output exist. |
| [ ] | AI-PRO-001 | Implement profile extraction drafts | PRO-006, AIF-008 | Explicit text yields controlled field proposals with confidence/source spans, no sensitive inference, field-by-field apply, version/concurrency/audit tests. |
| [ ] | AI-PRO-002 | Implement bio generation drafts | PRO-011, AIF-008 | Factual visibility-safe variants meet length/tone/locale, contain no contact/embellishment, remain drafts until accepted, and preserve prior bio on failure. |
| [ ] | AI-PRO-003 | Implement AI quality suggestions | PRO-012, AIF-008 | Suggestions reference deterministic missing/clarity items, cannot change eligibility/trust, and are actionable/safe/versioned. |
| [ ] | AI-DSC-001 | Implement natural-language search drafts | DSC-002, AIF-008 | Query returns only allowed editable filters/warnings; unknowns do not invent values; search executes only after ordinary confirmed request. |
| [ ] | AI-MAT-001 | Implement grounded compatibility explanations | MAT-003, AIF-008 | LLM receives viewer-safe factors/score, cannot alter number, exposes no hidden preference, uses neutral discussion points/questions, and has template fallback. |
| [ ] | AI-MSG-001 | Implement communication draft modes | MSG-003, AIF-008 | Introduction/reply/follow-up/meeting/rejection/thanks use explicit context/tone, preview only, no auto-send/contact invention, and safety checks pass. |
| [ ] | AI-MSG-002 | Implement translation drafts | MSG-003, AIF-008 | Explicit selected text translates supported language pair, preserves original, flags uncertainty, never expands conversation context or sends automatically. |
| [ ] | AI-MSG-003 | Implement tone/safety suggestions | MSG-009, AIF-008 | Unsent text receives advisory respectful/clarity warnings; policy rejection remains deterministic; body is absent from logs/events. |
| [ ] | AIF-011 | Implement AI observability, budgets, dedupe, and fallbacks | AIF-005, AIF-009 | Per-capability metrics/cost/latency/errors, quotas/concurrency/spend alarms, stale suppression, approved fallback, and emergency disable are tested. |
| [ ] | AIF-012 | Run launch-capability evaluation and approval | AIF-010, AI-PRO-001, AI-PRO-002, AI-PRO-003, AI-DSC-001, AI-MAT-001, AI-MSG-001, AI-MSG-002, AI-MSG-003, AIF-011 | Fake/OpenAI local and Bedrock development results meet approved grounding/safety/quality/cost thresholds with no blocking leakage/inference/auto-action failure. |

---

## Phase 8 — administration, analytics, compliance, observability, and backend hardening

| Status | ID | Task | Depends on | Done when |
|---|---|---|---|---|
| [ ] | ADM-001 | Protect separate administrative API surface | IAM-012, FND-008 | Admin listener/host policy, strong auth, scoped permissions, reason capture, rate limits, redacted errors, and immutable audit wrap every route. |
| [ ] | ADM-002 | Implement account/profile search and safe support views | ADM-001, PRO-011 | Authorized staff can locate by safe identifiers, see field-minimized view, cannot access chat/evidence by default, and bulk access alerts. |
| [ ] | ADM-003 | Implement moderation case/action/appeal endpoints | ADM-001, TRU-006 | Queue filters/claim/assign/evidence/action/close/appeal decisions enforce role separation, policy version, SLA, concurrency, and audit. |
| [ ] | ADM-004 | Implement verification/billing/support admin endpoints | ADM-001, VER-005, BIL-007 | Scoped reviewers/support perform approved operations only through domain services; private provider data and notes remain restricted. |
| [ ] | ADM-005 | Implement brand/reference/feature configuration endpoints | ADM-001, BRD-005, REF-003 | Reviewed config activation/deactivation is validated, versioned, evented, auditable, and reversible. |
| [ ] | ADM-006 | Implement AI operations and emergency controls | ADM-001, AIF-011 | Staff can inspect safe job metadata/retry transient jobs/disable capability; cannot view raw prompts or arbitrarily edit production prompts. |
| [ ] | ADM-007 | Implement support ticket/comment workflow | ADM-001, DAT-004 | User/internal comments, assignment/status, encrypted body, visibility separation, notification, retention, and audit pass. |
| [ ] | ANL-001 | Define minimized analytics event taxonomy and consent classes | DEC-012, EVT-002 | Versioned events/allowed properties exclude profile/message/contact text, sensitive ad targeting, and unbounded IDs; owner/retention documented. |
| [ ] | ANL-002 | Implement product-event projector and daily aggregates | ANL-001, EVT-006 | Idempotent funnel/safety/billing/AI aggregates honor consent/expiry, tolerate replay, and expose lag/quality metrics. |
| [ ] | ANL-003 | Implement safe admin metrics APIs | ANL-002, ADM-001 | Authorized aggregate endpoints support date/brand/experience dimensions with minimum-cell/privacy rules and no individual inference. |
| [ ] | CMP-001 | Complete field-level data inventory and processing map | DEC-012, PRO-011, MSG-010, VER-005, BIL-005, AIF-006 | Every field/object/event/log/provider flow has purpose, class, visibility, retention, export, deletion, AI eligibility, and owner reviewed. |
| [ ] | CMP-002 | Implement immutable audit service and integrity checks | ADM-001, CMP-001 | Security/admin/sensitive access audit is append-only, redacted, searchable by scope, integrity-checkable, retained, and excluded from ordinary mutation. |
| [ ] | CMP-003 | Implement data export workflow | CMP-001, MED-007, EVT-007 | Recent-auth request gathers authorized portable data, excludes others/secrets/internal risk, produces short-lived encrypted/signed asset, notifies, and audits. |
| [ ] | CMP-004 | Implement account/profile deletion and anonymization workflow | CMP-001, TRU-006, BIL-005 | Access/discovery stop immediately; checkpointed purge/anonymize handles blocks, billing/safety/legal constraints, object cleanup, idempotency, and evidence. |
| [ ] | CMP-005 | Implement retention purge jobs and legal holds | CMP-001, EVT-007 | Per-class due records/objects purge safely, hold recheck prevents conflict, dry-run/report/metrics/audit work, and tests use accelerated clocks. |
| [ ] | CMP-006 | Publish approved legal/policy version records and consent mapping | DEC-002, DEC-003, DEC-006, DEC-009, DEC-012, IAM-009 | Terms/privacy/community/AI/cookie/moderation/verification/refund document versions map to enforced consent and no placeholder reaches beta. |
| [ ] | OBS-001 | Implement OpenTelemetry, structured redacted logs, and correlation | FND-008, CMP-001 | API/worker/DB/provider traces and logs preserve request/event flow, use allowlisted fields, and inspection finds no prohibited data. |
| [ ] | OBS-002 | Implement application/queue/provider/AI/billing metrics | OBS-001, AIF-011, BIL-005 | Bounded metrics cover latency/errors/capacity/outbox/queue/DLQ/provider/AI cost/business invariants without user IDs/text labels. |
| [ ] | OBS-003 | Create dashboards, alerts, and runbook links | OBS-002 | Local/staging dashboard definitions and actionable thresholds cover SLOs, database, queues, providers, security, billing, AI spend, and moderation SLA. |
| [ ] | SEC-001 | Maintain release threat model and abuse-case matrix | CMP-001 | Assets/trust boundaries/threats/mitigations/owners map to automated/manual tests for all MVP flows and AI/providers. |
| [ ] | SEC-002 | Harden API, headers, CORS/CSRF, SSRF, payloads, rate limits, and errors | SEC-001, IAM-011 | Security config is environment-tested, fail-safe, has no wildcard credential origins/arbitrary fetch, and abuse suite passes. |
| [ ] | SEC-003 | Harden containers, dependencies, secrets, and build provenance | FND-011 | Non-root/minimal/read-only image where possible, pinned digest, SBOM/provenance, patch policy, secret rotation contract, and scans pass. |
| [ ] | SEC-004 | Complete object-level authorization matrix | ADM-007, AIF-012, CMP-004 | Automated suite attacks every public/member/admin endpoint across account/profile/manager/brand/network/block/sanction/entitlement states with no unauthorized disclosure. |
| [ ] | SEC-005 | Complete API/media/chat/webhook/AI security test suite | SEC-002, SEC-003, SEC-004 | Injection/XSS/SSRF/upload/webhook/replay/scrape/message/prompt-injection/leakage tests have no unaccepted critical/high finding. |

---

## Phase 9 — backend system validation and release gate

| Status | ID | Task | Depends on | Done when |
|---|---|---|---|---|
| [ ] | TST-001 | Build canonical backend E2E journey | IAM-013, PRO-015, MED-008, DSC-008, MAT-008, MSG-010, TRU-008, VER-006, NOT-007, BIL-008, AIF-012, CMP-005 | One repeatable client executes register-to-delete journey and major failure branches with fake providers. |
| [ ] | TST-002 | Generate 10k-profile performance dataset and query-plan checks | DAT-006, DSC-003 | Deterministic safe dataset creates realistic cardinality; critical search/chat/admin plans avoid sequential/deep-offset pathologies and regressions fail CI. |
| [ ] | TST-003 | Run API/search/chat initial-capacity load tests | TST-002, MSG-010 | 100 concurrent users, 20 RPS sustained/100 burst, WebSocket/message scenarios meet p95/error/connection budgets without lost effects. |
| [ ] | TST-004 | Run queue/provider/Redis/worker resilience tests | EVT-010, AIF-011, NOT-006, BIL-007 | Burst/backlog/crash/retry/timeout/throttle/Redis restart/stale job/DLQ recovery preserves correctness and exposes useful status/alerts. |
| [ ] | TST-005 | Validate OpenAPI client and contract freeze v1 | FND-010, TST-001 | Generated TypeScript client compiles, covers MVP endpoints/error/idempotency/operations/realtime contracts, and incompatible drift requires explicit version decision. |
| [ ] | TST-006 | Execute backend privacy/security evidence review | SEC-005, CMP-005, OBS-003 | Logs/events/traces/errors/exports/objects/backups/test artifacts contain no prohibited data; legal/security checklist and findings are closed/accepted. |
| [ ] | TST-007 | Publish backend release candidate artifact | TST-003, TST-004, TST-005, TST-006 | Reproducible signed/scanned image digest, SBOM, migrations, OpenAPI/events, AI evaluation, test reports, changelog, and rollback notes are retained. |
| [ ] | GATE-BE-001 | Approve backend MVP and unlock frontend | TST-007, ADM-007, ANL-003, CMP-006 | Product/engineering/security confirm complete backend path, stable contracts, synthetic demo, zero blocking defects, and document the approved release candidate. |

---

## Phase 10 — AWS infrastructure and CI/CD

| Status | ID | Task | Depends on | Done when |
|---|---|---|---|---|
| [ ] | CLD-001 | Create AWS account/environment and SSO access baseline | DEC-010, GATE-BE-001 | Dev/staging/prod isolation decision, IAM Identity Center permission sets, root MFA, audit owner, and no shared/long-lived developer keys are verified. |
| [ ] | CLD-002 | Configure GitHub OIDC and least-privilege environment roles | CLD-001, FND-001 | Exact repo/branch/environment claims assume separate plan/apply/publish/deploy/migration roles; fork/unprotected refs fail; CloudTrail records use. |
| [ ] | CLD-003 | Bootstrap secure Terraform state and module standards | CLD-001 | Encrypted/versioned/locked restricted state, tagging, validation/policy scans, drift process, and environment composition exist without secret values. |
| [ ] | CLD-004 | Provision VPC, subnets, routing, endpoints, and security groups | CLD-003 | Two-AZ private compute/data topology, explicit NAT/endpoints, SG-to-SG least privilege, flow logging policy, and no public DB/cache pass plan/test. |
| [ ] | CLD-005 | Provision KMS keys and Secrets Manager contracts | CLD-003 | Environment/application/restricted-data key and secret policies grant only approved roles, rotation/access alerts exist, and Terraform state contains no secret values. |
| [ ] | CLD-006 | Provision RDS PostgreSQL and role initialization | CLD-004, CLD-005 | Private encrypted TLS RDS, production Multi-AZ/PITR/deletion protection, alarms, application/migration roles, connection budget, and restore access are tested. |
| [ ] | CLD-007 | Provision ElastiCache Redis | CLD-004, CLD-005 | Private encrypted/authenticated cache has approved failover/capacity/eviction alarms and application degrades safely during restart. |
| [ ] | CLD-008 | Provision S3 media/evidence/export buckets | CLD-005 | Public block/OAC/encryption/lifecycle/incomplete cleanup/versioning/access audit and narrow task-role policies differ correctly by data class. |
| [ ] | CLD-009 | Provision EventBridge, SQS queues, DLQs, and policies | CLD-005 | Versioned routes, encryption, visibility/retention/redrive, least-privilege producers/consumers, alarms, and selective replay role exist. |
| [ ] | CLD-010 | Provision ECR, ECS cluster, task definitions, and services | CLD-004, CLD-005, CLD-006, CLD-007, CLD-008, CLD-009 | API/outbox/scheduler/worker services use immutable digest, narrow task roles, private tasks, health/drain/autoscale/circuit breaker and connection/concurrency limits. |
| [ ] | CLD-011 | Provision ALB, CloudFront, WAF, Route 53, and ACM | CLD-010, DEC-011 | TLS/host routing/WebSocket, exact origins, private-response no-cache, WAF/rate rules, canonical redirects, health path, and safe logs pass. |
| [ ] | CLD-012 | Configure SES and approved external provider sandboxes | CLD-011, DEC-007, DEC-008 | Domain authentication, bounce/complaint webhooks, environment secrets, payment/verification callback URLs/signatures, and sandbox contracts pass. |
| [ ] | CLD-013 | Enable Bedrock routes, quotas, and AI task permissions | CLD-010, DEC-009 | Approved region/model aliases, task-role-only invoke, quotas, logging/privacy choice, budget alarms, kill switch, and adapter evaluation pass. |
| [ ] | CLD-014 | Provision CloudWatch/OTel dashboards, alarms, audit/security services, and budgets | CLD-010, OBS-003 | Logs/metrics/traces/alarms/runbooks, CloudTrail/restricted access alerts, GuardDuty/Security Hub/Config choices, budgets/anomaly detection are tested. |
| [ ] | CICD-001 | Implement immutable image build, scan, SBOM, sign/attest, and ECR publish | CLD-002, CLD-010, TST-007 | Main pipeline builds once, blocks scan failures, publishes digest/provenance/SBOM, and later environments consume exact digest. |
| [ ] | CICD-002 | Implement Terraform plan/approval/apply pipelines | CLD-002, CLD-003 | PR plan is reviewable; protected environment applies with narrow role/concurrency/locks; drift and destructive changes require explicit approval. |
| [ ] | CICD-003 | Implement one-off migration and expand/backfill/contract workflow | CICD-001, CLD-006 | Advisory-locked task uses migration role/image digest, timeouts/backups, compatible schema order, staging scale test, and forward-fix plan. |
| [ ] | CICD-004 | Implement automatic development deployment and smoke tests | CICD-001, CICD-002, CICD-003 | Main deploys infrastructure/migration/services, runs health/contracts/event adapters/E2E/changed Bedrock eval, and marks failure visibly. |
| [ ] | CICD-005 | Implement immutable staging promotion and full gates | CICD-004 | Approved digest/config promotes without rebuild; E2E/DAST/load smoke/provider/DLQ/migration/rollback/restore/AI evaluation pass. |
| [ ] | CICD-006 | Implement protected production canary/rolling deployment | CICD-005 | Approval shows release evidence; health/alarm/business checks govern gradual rollout; audit and heightened monitoring record outcome. |
| [ ] | CICD-007 | Implement application rollback and queue/provider recovery runbooks | CICD-006 | Prior image/config rollback works against expanded schema; feature/AI kill switches, selective DLQ replay, billing reconcile, and failure drill pass. |
| [ ] | CICD-008 | Implement backup restore and disaster-recovery exercise | CLD-006, CLD-008, CICD-005 | Isolated restore of DB/objects/config plus pinned deploy passes integrity/E2E and measures accepted RPO/RTO; evidence and gaps are recorded. |
| [ ] | CICD-009 | Execute AWS security and cost review | CLD-014, CICD-008 | IAM/network/encryption/public-access/state/secrets/logging/backup findings close; pricing estimate and actual budget thresholds are approved. |
| [ ] | GATE-CLD-001 | Approve cloud backend readiness | CICD-007, CICD-008, CICD-009 | Staging backend release candidate is deployable/observable/recoverable, provider/AI sandboxes pass, and no production credential is shared through chat/Git. |

---

## Phase 11 — frontend (blocked until backend approval)

Recommended default for decision: Next.js/React/TypeScript web application, generated OpenAPI client, accessible component system, TanStack Query or equivalent server-state layer, and Playwright. Confirm rather than assume before code.

| Status | ID | Task | Depends on | Done when |
|---|---|---|---|---|
| [ ] | FE-DEC-001 | Complete UX research, information architecture, and frontend stack decision | GATE-BE-001 | Candidate/parent workflows, mobile web constraints, accessibility/locales, framework/state/forms/testing, browser support, and measurable UX goals are recorded. |
| [ ] | FE-FND-001 | Scaffold frontend app and CI checks | FE-DEC-001 | Pinned app builds/tests/lints/types, environment config validates, CSP/security headers plan exists, and no handwritten API types duplicate OpenAPI. |
| [ ] | FE-FND-002 | Integrate generated API client, auth/session, errors, operations, and realtime shell | FE-FND-001, TST-005 | Cookie/token/CSRF flow, refresh/logout, acting profile, RFC errors, ETag/idempotency, operation polling, WebSocket reconnect/catch-up are centralized/tested. |
| [ ] | FE-DSN-001 | Build accessible token-based brand/experience design system | FE-FND-001, DEC-011 | Responsive tokens/components support brand/experience/user preference, WCAG contrast, reduced motion, large targets, and avoid gender assumptions. |
| [ ] | FE-DSN-002 | Build form, loading, empty, error, confirmation, privacy, and safety patterns | FE-DSN-001 | Keyboard/screen-reader behavior, autosave conflict, retry, destructive/recent-auth, AI disclosure, report/block, and slow-operation patterns are consistent. |
| [ ] | FE-PUB-001 | Build public landing, brand/experience routing, plans, legal, and SEO shell | FE-DSN-001, BRD-003 | Canonical/secondary domain behavior, metadata/schema, locale, experience selection, pricing/legal links, performance, and no private caching pass. |
| [ ] | FE-AUTH-001 | Build register/login/challenge/recovery/session UI | FE-FND-002, FE-DSN-002 | Generic auth responses, cooldown/attempt UX, secure refresh/logout/all sessions, contact verification, MFA/recent auth, and accessibility E2E pass. |
| [ ] | FE-ONB-001 | Build self/parent onboarding and candidate consent UI | FE-AUTH-001, PRO-003 | Relationship/permissions/disclosure/invite/consent states are explicit; candidate can review/control profile; interrupted flow resumes safely. |
| [ ] | FE-PRO-001 | Build structured profile editor and autosave/conflict UI | FE-ONB-001, FE-DSN-002 | All profile/family/education/employment/reference sections, visibility, completion, ETag conflicts, drafts, validation, and parent attribution work. |
| [ ] | FE-MED-001 | Build media upload, processing, crop/order/visibility, and biodata UI | FE-PRO-001 | Direct upload progress/retry/cancel, quarantine/rejection, processed preview, primary/order/access, delete, and biodata operation/download pass. |
| [ ] | FE-PRO-002 | Build preferences, brand/experience, preview, submit/publish/pause UI | FE-PRO-001, FE-MED-001 | Private preference/dealbreaker explanation, authorized preview, candidate consent/missing-item gates, lifecycle confirmations and statuses pass. |
| [ ] | FE-DSC-001 | Build structured and natural-language discovery UI | FE-PRO-002, AI-DSC-001 | Editable filter draft, accessible filters/results/cursors, privacy-safe cards/views, loading/empty/blocked/entitlement states, and mobile performance pass. |
| [ ] | FE-DSC-002 | Build shortlist, hide, saved searches, and recommendation UI | FE-DSC-001 | Private notes/hide/unhide/alerts/reasons operate idempotently, never override block, and explain recommendation limits. |
| [ ] | FE-MAT-001 | Build compatibility, interest, and match UI | FE-DSC-001, AI-MAT-001 | Score/band/factors/discussion explanation is grounded/non-deterministic claims avoided; send/respond/withdraw/end races and safe statuses pass. |
| [ ] | FE-MSG-001 | Build secure realtime conversation UI | FE-MAT-001, MSG-010 | Keyset history, optimistic idempotent send, edit/delete/read/unread/reconnect/mute/typing/attachments/manager attribution and accessible mobile behavior pass. |
| [ ] | FE-AI-001 | Build AI profile/communication draft, translation, tone, and feedback UI | FE-PRO-001, FE-MSG-001, AIF-012 | AI is clearly disclosed; source/diff/preview/edit/apply/send confirmation, stale/failure/fallback/disable, and feedback states prevent auto-action. |
| [ ] | FE-TRU-001 | Build block, report, trust, moderation-status, and appeal UI | FE-MSG-001, TRU-008 | Immediate safe block, evidence report, reporter-safe status, explainable trust/verification, sanctions/appeals, and crisis/help copy pass. |
| [ ] | FE-VER-001 | Build verification request/evidence/status UI | FE-TRU-001, VER-006 | Available checks, restricted upload, provider/manual steps, status/expiry/retry, minimal public claim, and privacy disclosure pass. |
| [ ] | FE-BIL-001 | Build plans, hosted checkout return, subscription, history, and cancellation UI | FE-AUTH-001, BIL-008 | Approved price/currency, provider redirects/status polling, entitlement refresh, renewal/refund terms, failure/recovery, recent auth, and accessibility pass. |
| [ ] | FE-NOT-001 | Build notification center and preferences UI | FE-FND-002, NOT-007 | Realtime/infinite list/read states, category/channel/quiet hours/marketing consent, mute/bounce-safe messaging, and no private lock-screen preview assumption pass. |
| [ ] | FE-SET-001 | Build account, contacts, managers, sessions, consents, export, and deletion settings | FE-PRO-002, CMP-005 | Sensitive actions require recent auth; role/consent consequences, request progress/download expiry, legal hold/status, and confirmations are clear. |
| [ ] | FE-ADM-001 | Build protected operations console | FE-FND-002, ADM-007, ANL-003 | Separate admin access supports queues/cases/verification/billing/support/config/AI status/metrics with scoped data, reason capture, no chat/evidence default, and audit. |
| [ ] | FE-L10N-001 | Implement localization and bidirectional content readiness | FE-DSN-002, DEC-004 | UI strings/reference labels/date/number pluralization, user content language, translation labeling, fallback, and Punjabi/English review pass. |
| [ ] | FE-A11Y-001 | Complete WCAG 2.2 AA audit and remediation | FE-SET-001, FE-ADM-001, FE-L10N-001 | Automated/manual keyboard/screen reader/zoom/contrast/focus/error/live-region/motion tests pass documented supported workflows. |
| [ ] | FE-PERF-001 | Meet web performance and resilient-network budgets | FE-A11Y-001 | Bundle/image/font/cache/SSR behavior, Core Web Vitals target, slow/offline retry, chat/discovery responsiveness, and no private cache leakage pass. |
| [ ] | FE-ANL-001 | Add consent-aware product analytics and UX metrics | FE-L10N-001, ANL-001 | Only approved minimized events fire after applicable consent, sensitive fields/URLs/text are excluded, and opt-out verification passes. |
| [ ] | FE-E2E-001 | Complete cross-browser responsive E2E/security suite | FE-PERF-001, FE-ANL-001 | Full journey passes current/previous supported browsers and mobile breakpoints; CSP/XSS/CSRF/auth/realtime/upload/payment/AI/block/error cases pass. |
| [ ] | FE-DEP-001 | Deploy frontend/edge configuration through CI/CD | FE-E2E-001, GATE-CLD-001 | Immutable artifact deploys to staging, uses approved API origins/secrets-free config, cache invalidation/rollback/smoke/monitoring work. |
| [ ] | GATE-FE-001 | Approve world-class frontend release candidate | FE-DEP-001 | Product/design/accessibility/security validate end-to-end candidate/parent experience, measured usability/performance, no blocking defects, and rollback. |

---

## Phase 12 — production launch and operations

| Status | ID | Task | Depends on | Done when |
|---|---|---|---|---|
| [ ] | OPS-001 | Finalize production legal, privacy, consent, community, verification, billing, and AI copy | CMP-006, GATE-FE-001 | Counsel/product approve exact published versions/contacts/processes; consent IDs match backend; no placeholder or unsupported claim remains. |
| [ ] | OPS-002 | Staff and rehearse moderation/support/verification/billing operations | ADM-007, GATE-FE-001 | Named coverage, SLA/escalation, least-privilege accounts/MFA, queues/templates, quality review, and after-hours safety path are tested. |
| [ ] | OPS-003 | Complete production provider/domain approvals | CLD-012, CLD-013, OPS-001 | DNS/certificates, SES production, payment/verification, optional SMS/WhatsApp, Bedrock quotas, webhooks, sender/merchant/business approvals pass live-safe checks. |
| [ ] | OPS-004 | Perform independent security review and remediate | GATE-FE-001, CICD-009 | External/internal penetration/API/cloud/AI review findings are closed or risk-accepted by owner with expiry; no unaccepted critical/high remains. |
| [ ] | OPS-005 | Run production-like incident, rollback, credential, DLQ, billing, and restore tabletop | CICD-007, CICD-008, OPS-002 | Owners execute runbooks, communication/legal decision tree, containment/recovery, RPO/RTO evidence, and action items close. |
| [ ] | OPS-006 | Validate production observability, privacy, costs, and capacity | OPS-003, OPS-005 | Synthetic canary/alerts/on-call, redacted telemetry, budgets/anomaly detection, load headroom, queue/provider quotas, and launch dashboard pass. |
| [ ] | OPS-007 | Run invite-only beta | OPS-001, OPS-002, OPS-004, OPS-006 | Approved cohort uses production with consent; support/moderation/metrics/AI feedback operate; severity thresholds and stop/rollback criteria are enforced. |
| [ ] | OPS-008 | Review beta and close launch blockers | OPS-007 | Security/safety/UX/reliability/performance/cost/conversion findings are prioritized; all launch blockers close and decisions/backlog/docs update. |
| [ ] | OPS-009 | Launch LaaraLaari production | OPS-008 | Protected deployment succeeds, domains/canaries/journey/provider payments work, heightened monitoring/support active, and release/audit record is complete. |
| [ ] | OPS-010 | Conduct post-launch review and prioritize growth backlog | OPS-009 | 24-hour/7-day/30-day reviews compare SLO/safety/cost/product metrics, capture incidents/lessons, and approve only evidence-driven Phase 2 AI/search/scaling work. |

---

## Definition of backend completion

The backend is not “done” merely because endpoints exist. `GATE-BE-001` requires:

- all MVP domain paths work with AI/providers unavailable;
- authorization is enforced at account, managed-profile, resource, brand, and network levels;
- blocks/manager revocation/sanctions immediately affect discovery and chat;
- database/event/API contracts are versioned and idempotent under retries/races;
- real media, billing, verification, and AI providers remain behind tested adapters;
- synthetic E2E, security, privacy, load, resilience, migration, and AI evaluation evidence passes;
- OpenAPI is stable enough to generate the frontend client;
- observability, support/admin, export/deletion/retention, and fallback behavior are implemented—not deferred to frontend.

## Deferred growth backlog trigger list

Create detailed tasks only after MVP evidence justifies them:

- behavioral recommendation engine and embeddings;
- advanced fraud/duplicate image/document signals;
- family compatibility and family knowledge graph;
- intelligent notification timing;
- parent knowledge assistant;
- OpenSearch;
- native mobile/push;
- voice assistant;
- wedding assistant/marketplace;
- module extraction into independently deployed services;
- additional isolated networks/white-label customers.

Each growth proposal must include measured problem, expected user benefit, data/consent impact, fairness/safety risks, cost, operational burden, experiment/reversal plan, and a decision record.
