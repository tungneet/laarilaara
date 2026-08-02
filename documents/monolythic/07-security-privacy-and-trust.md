# Security, privacy, and trust

## 1. Security objectives

LaaraLaari will process identity, relationship, religious/community, family, location, financial, document, photo, and private communication data. Trust is a core product feature, not an infrastructure add-on.

Objectives:

- only the right account, acting for the right profile, can perform each action;
- a brand never becomes an accidental tenant boundary, while an isolated `network_id` always is one;
- private profile fields, hidden preferences, documents, contacts, messages, and moderation evidence are not exposed;
- compromised clients, duplicate requests, provider failures, or malicious model output cannot corrupt authoritative state;
- abuse is quickly blockable/reportable, high-impact moderation is reviewable, and every privileged action is audited;
- deletion, export, retention, consent withdrawal, and legal holds are implemented as workflows rather than promises in static text.

## 2. Data classification

| Class | Examples | Baseline handling |
|---|---|---|
| Public | Brand copy, active reference labels, public plan summaries | Cacheable after content review |
| Member-visible | Visibility-filtered profiles, compatibility explanation | Authentication/policy, no public indexing unless explicitly approved |
| Confidential | Account data, preferences, family facts, billing/subscription metadata, search/view history | Least privilege, encrypted transport/storage, redacted logs |
| Highly sensitive | Contacts, date of birth, religion/community, marital history, precise location, messages, reports | Field/object access policy, minimization, application encryption where designed, strict audit/retention |
| Restricted evidence | Identity documents, verification payloads, moderation evidence, legal holds, support private notes | Dedicated storage prefix/KMS key/role, case-based access, short retention, access alerts |
| Secret | Password/token hashes, provider keys, signing keys, KMS material | Secrets Manager/local ignored secret store; never database/event/log/browser/Git |

A field inventory maps every collected value to purpose, owner, visibility, retention, export, deletion, and AI eligibility before beta.

## 3. Threat model baseline

Protect against:

- account enumeration, credential stuffing, OTP abuse, session theft, refresh-token replay, and account takeover;
- broken object-level authorization across accounts, managed profiles, brands, and networks;
- a parent/manager acting after permission or candidate consent is revoked;
- profile scraping, mass discovery, photo/document URL sharing, and contact harvesting;
- fake/duplicate profiles, romance/payment scams, coercion, harassment, hate, impersonation, and unsafe attachments;
- SQL/NoSQL/command/template injection, XSS, CSRF, SSRF, malicious files, decompression bombs, and supply-chain compromise;
- webhook spoofing/replay, duplicate billing, provider callback confusion, and idempotency bypass;
- event replay/out-of-order delivery, stale AI results, prompt injection, hidden-data leakage, and over-trusted model output;
- admin/support abuse, excessive cloud permissions, secrets leakage, backup exposure, and untracked production access;
- denial of service, expensive AI abuse, queue flooding, and database connection exhaustion.

Maintain abuse cases alongside feature acceptance tests. Update the threat model before each beta/production gate and major AI/provider feature.

## 4. Identity and session security

- Normalize contacts, encrypt values, and use keyed hashes for equality lookup. Responses show only masked contacts.
- Passwords, if supported, use a current memory-hard password hash with centrally reviewed parameters and breached-password checks. Never invent custom crypto.
- OTP/magic links use cryptographically random one-time secrets, short expiry, bounded attempts, hashed storage, and purpose binding.
- Login and recovery return generic responses to prevent account enumeration.
- Access tokens are short lived. Refresh tokens rotate; reuse revokes the token family and creates a security event.
- Web refresh cookies use `HttpOnly`, `Secure`, appropriate `SameSite`, exact domain/path, and CSRF protection for cookie-authenticated mutations.
- Reauthentication is required for contact changes, manager/candidate-control changes, data export/deletion, billing changes, and sensitive admin actions.
- MFA is mandatory for admin/moderator/verifier/support roles before production. Candidate MFA is offered and may be risk-triggered later.
- Sessions can be listed and revoked; suspension, block policy, password reset, and manager revocation invalidate relevant sessions/realtime connections.
- Store token hashes, not bearer tokens. Do not log authorization/cookie headers.

## 5. Authorization model

Authorization is capability-based, not just role-based.

Inputs:

- authenticated account and session assurance;
- trusted network/brand context;
- acting profile and current manager permission;
- resource ownership/participation;
- candidate consent and profile lifecycle;
- blocks, sanctions, moderation state;
- entitlement/quota;
- requested field/action and reason when privileged.

### Profile permissions

Suggested permission keys:

- `profile.read_private`
- `profile.edit`
- `profile.manage_media`
- `profile.manage_preferences`
- `profile.manage_managers`
- `profile.submit`
- `profile.publish`
- `discovery.act`
- `interest.act`
- `conversation.read`
- `conversation.send`
- `billing.manage`
- `data_rights.manage`

The candidate/primary controller can revoke managers according to approved policy. A manager cannot silently expand its own permissions. Every change creates a revision, audit entry, and realtime access refresh.

### Service/admin permissions

- ECS task roles are queue/provider/schema-purpose specific.
- Admin reads use separate permissions for profile, message/evidence, verification, billing, and audit data.
- Support agents do not read chat or verification documents by default.
- Moderator case access is scoped to assigned/authorized cases; restricted evidence views require a reason and audit.
- No “super-admin bypass” in ordinary application code. Emergency access is time-bound, approved, logged, and reviewed.

Every resource endpoint has negative tests for another account, another managed profile, revoked manager, hidden resource, blocked pair, suspended account, another brand, and another network.

## 6. Candidate and family consent

- Clearly disclose whether a profile is self-managed or family-managed and who sends a communication, without exposing private account details.
- A profile for another adult cannot publish until the candidate verifies identity/contact and accepts the current management/publication terms.
- Candidate consent withdrawal immediately pauses discovery and manager communication pending approved workflow.
- Manager invitations are one-time, expiring, permission-scoped, and accepted only after account verification.
- Avoid collecting data about family members beyond a defined matchmaking purpose. Do not collect minor contact details.
- AI processing, marketing communications, public success stories, and optional sensitive fields have separate consent where required.
- Consent evidence is versioned; silence or continued use is not substituted where affirmative consent is required.

## 7. API and application security

- Validate request content type, size, shape, controlled values, and state transition before business execution.
- Parameterized ORM/query APIs only; reviewed raw SQL contains no string-concatenated user values.
- Use output encoding and a strict Content Security Policy in the later frontend. Sanitize approved rich text; prefer plain text.
- CORS uses exact approved origins. Never combine credentials with wildcard origins.
- Set HSTS, `X-Content-Type-Options`, `Referrer-Policy`, frame restrictions, and modern TLS at CloudFront/ALB.
- Do not place sensitive filters/text in URLs, referrers, analytics, or error details.
- SSRF defenses apply to every server-side fetch: allowlisted providers, HTTPS, DNS/IP checks, response/time/size bounds, and no arbitrary user URL fetch at MVP.
- Idempotency, optimistic concurrency, unique constraints, and state machines protect duplicate/replayed mutations.
- WAF handles broad malicious patterns/bots; application authorization and rate limits remain authoritative.
- Production error responses never expose stack traces, SQL, provider payloads, secret/config values, storage keys, or existence of hidden profiles.

## 8. Rate limits and abuse controls

Initial values are configurable defaults and must be tuned with beta data.

| Action | Starting policy |
|---|---|
| Registration/challenge | Per IP/device/contact hash; e.g. 3 challenges/hour/contact and progressive cooldown |
| Login/OTP verify | Bounded attempts per challenge plus IP/account backoff |
| Contact/recovery changes | Recent auth and low daily limit |
| Discovery search/profile view | Per account/profile minute and day limits; detect scraping patterns |
| Interests | Entitlement plus daily cap; duplicate pair/state protection |
| Messages | Per conversation/account burst and sustained limits; spam similarity/link/payment heuristics |
| Uploads | Per account/day storage quota, per-file size/type, checksum and incomplete-upload expiry |
| AI | Capability-specific account/profile quotas, concurrency 1 where appropriate, spend/token limits |
| Reports | Prevent spam while never blocking emergency safety reporting; deduplicate repeated report targets |
| Webhooks | Provider signature/replay validation and infrastructure limits, not user auth |
| Admin | Low limits, strong auth, alert on bulk access/export |

Use Redis for distributed counters with fail-safe policy by action. A Redis outage must not make high-risk actions unlimited.

## 9. Media and document security

- Browser uploads directly to private object storage using one-time, short-lived presigned URLs with server-generated object keys and exact constraints.
- Confirm checksum/content length/type server-side; never trust filename or client MIME.
- Quarantine new objects. Scan malware, detect actual file type, reject polyglots/archives where not needed, remove image metadata, normalize/re-encode images, and generate safe variants.
- Enforce pixel/decompression limits to prevent image bombs.
- Serve only processed variants to profile viewers. Original photos and all verification documents remain private.
- Short-lived access URLs are minted only after current authorization/visibility checks. Avoid putting user identifiers or names in keys.
- Verification evidence uses separate prefixes/buckets, KMS keys, task roles, lifecycle, and audited access.
- S3 public access block, ownership enforcement, encryption, versioning where needed, access logging/data events for restricted buckets, and lifecycle policies are mandatory.
- Deletion removes associations immediately and queues all variants/originals subject to appeal/legal hold.

## 10. Secure and sanitized chat

“Secure” means authenticated, authorized, encrypted, minimized, abuse-resistant, and auditable. Do not claim end-to-end encryption while the server performs moderation, translation, drafts, reports, or multi-manager access.

- TLS in transit; RDS/S3 encryption at rest; message bodies application-encrypted with versioned envelope encryption where approved.
- Decrypt only inside authorized API/worker paths. Never place body text in events, normal logs, metrics, traces, search indexes, analytics, or notification previews beyond approved minimal text.
- Verify active participant/manager permission, match/conversation state, block/sanction, rate, size, and attachment readiness on every send/read—not only connection time.
- Deterministic fast checks can reject known dangerous files, oversized content, prohibited links/payment solicitation patterns, and obvious abuse before commit.
- Deeper model/provider moderation is asynchronous when latency is uncertain; policy defines quarantine/removal and human review.
- AI draft/translate/tone features use only explicitly selected/authorized text, produce a preview, and never send automatically.
- Contact sharing policy is explicit and user-controlled; warn about payment requests, off-platform movement, and sensitive information.
- Reports reference immutable message IDs/evidence under case-based access. User deletion must not destroy evidence under an active lawful safety hold.
- Typing/presence is ephemeral. WebSocket authorization is re-evaluated after manager, block, match, or sanction changes.
- Notification content defaults to “You have a new message,” not raw private text on lock screens/email.

## 11. Trust, moderation, and verification

- Publish community guidelines, report categories, sanctions, appeal eligibility, and expected response times before beta.
- Block is immediate, private, and stronger than hide. It suppresses discovery, interests, chat, recommendation, and related notifications both ways.
- Reports create acknowledged cases without exposing reporter identity to the subject.
- Risk/AI signals are confidence-tagged and expire; they do not directly ban or publicly lower a user.
- Human moderators use evidence and policy version, record reason codes, and can apply time-bound/reversible actions.
- High-impact action and appeal should use separate reviewers where staffing permits.
- Verification confirms only a named claim at a time. A “verified” badge never implies overall safety or compatibility.
- Raw documents and provider payloads are not public and are purged as soon as policy/legal obligations permit.
- Trust summary factors and dates are explainable; provide correction/appeal for errors.
- Monitor false-positive, appeal reversal, demographic disparity, report abuse, reviewer consistency, and case SLA metrics.

## 12. AI security and privacy

- Treat every user/profile/message/retrieved text as prompt-injection-capable data.
- Models have no arbitrary network, SQL, object storage, shell, admin, or external URL tools at launch.
- Input builders select minimal authorized facts and redact contacts, precise addresses, secrets, and unrelated context.
- Output uses strict schemas, allowlisted reference IDs, grounding checks, safety checks, and subject versions.
- Do not send restricted evidence or raw identity documents to general LLMs.
- Do not infer religion/community, health, wealth, immigration status, or other sensitive facts.
- Do not route production data to a fallback provider unless approved disclosure/contract/config permits it.
- Provider logging/training/retention controls and regional processing are reviewed and documented.
- Model/prompt changes pass evaluation and red-team gates; feature/model kill switches are tested.

## 13. Cryptography and secrets

- Use managed TLS and established libraries. No custom cryptographic algorithms.
- AWS KMS keys are separated at least for application data, restricted verification evidence, and secrets/backups where justified.
- Envelope-encrypted fields store ciphertext, key/version metadata, and authenticated context binding network/table/record/field.
- Contact lookup uses a rotated keyed hash; rotation plan supports dual-read/write migration.
- Password/token/OTP values are one-way hashes with appropriate algorithms; encryption keys never derive from passwords.
- Secrets live in AWS Secrets Manager or an ignored local secret store and are injected at runtime. GitHub uses OIDC; ECS uses task roles.
- Rotate signing/provider/database secrets, rehearse revocation, and alert on secret access anomalies.
- Never paste AWS/OpenAI/payment/verification credentials into chat, tickets, docs, source, CI variables visible to forks, or Terraform state.

## 14. Logging, audit, and privacy

- Structured logs allowlist fields. Redact authorization, cookies, contacts, birth date, precise location, message/profile text, document paths, provider payloads, AI prompts/responses, payment details, and secrets.
- Hash/prefix IP and user agent only where justified for security; set retention.
- Metrics labels use bounded codes, never account/profile IDs or user text.
- Traces record operation names/status and safe IDs; database statements/binds are disabled or scrubbed for sensitive paths.
- Security/admin audit is append-only and includes actor, action, subject, request, reason, time, and safe metadata/integrity evidence.
- Alert on bulk profile reads, restricted evidence views, admin role changes, repeated failed auth, webhook signature failures, mass exports, DLQ growth, and abnormal AI spend.

## 15. Privacy/compliance workstream

Legal counsel must map launch countries. Engineering should be ready for, without claiming automatic compliance with:

- India's Digital Personal Data Protection framework and related rules;
- UK/EU GDPR where offering to residents;
- communications/anti-spam rules for email/SMS/WhatsApp by country;
- payment/tax/accounting obligations; hosted checkout keeps card data outside LaaraLaari's PCI scope as far as provider integration permits;
- biometric/document-specific laws if face matching or document AI is later considered.

Required artifacts before beta:

- data inventory and processing-purpose map;
- privacy notice, terms, community guidelines, cookie/analytics choices, AI disclosure, and consent versions;
- processor/subprocessor and international transfer review;
- retention/deletion schedule and legal-hold process;
- data subject export/correction/deletion runbooks;
- breach/incident notification decision tree;
- child/age eligibility and parent-managed-profile policy;
- moderation, verification, refunds, and appeals policy.

## 16. Cloud and supply-chain security

- Separate AWS environments/accounts where practical; no production credentials or data in development.
- Private subnets for ECS/RDS/Redis, narrowly scoped security groups, no public RDS/Redis, VPC endpoints where cost/benefit supports them.
- IAM least privilege, permission boundaries for deploy roles, task role per worker class, CloudTrail, Config/Security Hub/GuardDuty as approved.
- ECR image scanning, dependency/license/secret/IaC scans, lockfile pinning, signed build provenance, and immutable image digests.
- Base images are minimal/non-root/read-only filesystem where possible; containers drop Linux capabilities and receive explicit CPU/memory.
- RDS automated backups/PITR, encrypted snapshots, deletion protection, controlled parameter groups, and restore tests.
- WAF, Shield Standard, CloudFront/ALB logs with privacy retention, and DNS/ACM controls.
- Production console/database access uses SSO, approved role, ticket/reason, time limit, and audit; no shared accounts.

## 17. Incident response

Severity definitions and owners must exist before production.

Minimum runbooks:

- leaked credential/signing key;
- suspected account takeover/session replay;
- profile/message/document data exposure;
- malicious upload/malware;
- mass scraping or messaging abuse;
- payment/webhook inconsistency;
- AI unsafe output/data leakage or runaway spend;
- RDS/Redis/S3/provider outage;
- EventBridge/SQS backlog/DLQ;
- faulty migration/deployment rollback;
- data export/deletion failure.

Each runbook covers detection, containment, evidence preservation, user/legal communication owner, recovery, credential rotation, validation, and retrospective actions. Conduct tabletop exercises before beta and production.

## 18. Security release gate

- Threat model and data inventory are reviewed for the release.
- SAST, dependency, secret, container, IaC, and DAST/API scans have no unaccepted critical/high issue.
- Object-level authorization and network isolation suites pass.
- Auth/session/CSRF/CORS/rate-limit/idempotency/webhook-replay tests pass.
- Media malware/type/metadata/bomb/quarantine tests pass.
- Chat leakage, block, manager revocation, evidence access, and moderation workflow tests pass.
- AI prompt-injection, hidden-data, contact/secret leakage, and auto-action tests pass.
- Logs/traces/events/errors/backups contain no prohibited fields in a test inspection.
- Backup restore, key/secret rotation path, incident tabletop, and rollback are evidenced.
- Legal/product owners approve consent, age, privacy, retention, moderation, verification, notification, and payment decisions.
