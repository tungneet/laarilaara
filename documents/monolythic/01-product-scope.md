# Product scope

## 1. Vision

LaaraLaari is an AI-assisted matchmaker for Punjabis worldwide. It should reduce an overwhelming directory of profiles into a smaller, safer, explainable set of compatible people and families while preserving user choice.

The product is not allowed to make marriage decisions, infer sensitive identities, promise outcomes, or present AI output as verified fact. AI assists; people decide.

## 2. Launch model

### One network, many entry experiences

- LaaraLaari is the initial public brand and shared user network.
- A domain resolves to a configurable brand.
- A brand can offer selectable experiences such as Amritdhari, NRI, Sikh, Jatt, Ramgarhia, professional, country-specific, divorcee, or widowed.
- An experience controls copy, theme tokens, onboarding hints, default filters, educational content, and featured success stories.
- Experiences do not silently assign identity labels or hide cross-experience matches. Users opt into profile visibility and matching preferences.
- One profile can participate in multiple brand experiences without duplicate accounts.
- A future truly independent white-label customer can be assigned a separate `network_id`; records must never cross a network boundary.

A separate database per flavor is intentionally rejected for the first 1,000 users because it fragments the network, duplicates operations, and lowers match quality.

## 3. Primary actors

| Actor | Purpose | Important constraints |
|---|---|---|
| Candidate | Person represented by a matchmaking profile | Must meet platform and jurisdictional age rules and control consent |
| Profile manager | Candidate, parent, guardian, or trusted relative who manages a profile | Relationship and actions are disclosed; permissions are revocable |
| Family collaborator | Helps review matches or conversations | Explicit invitation and least-privilege access |
| Member | Authenticated account browsing or managing allowed profiles | May manage more than one profile only when policy permits |
| Moderator | Reviews reports, risk signals, and content | Scoped queues; all actions audited |
| Verifier | Reviews identity/education/employment checks | Sees only the data needed for the check |
| Support agent | Resolves account and billing issues | Cannot read private chat by default |
| Administrator | Manages platform configuration and escalations | Strong authentication, just-in-time access where practical |
| Service principal | Internal worker or CI/CD identity | No interactive login; narrow machine permissions |

## 4. Core user journeys

### 4.1 Registration and consent

1. Account verifies email or phone.
2. Account accepts current terms, privacy notice, communication preferences, and AI-processing disclosure.
3. Account creates a candidate profile for self or invites/records the candidate whose profile it will manage.
4. Candidate consent is captured before publication; exceptional guardian flows require a separately approved policy.

### 4.2 Profile creation

1. User selects brand/experience and preferred language.
2. User enters structured profile, family, lifestyle, religious-practice, education, career, location, and future-plan information.
3. Optional AI profile builder extracts a draft from free text; the user confirms every field.
4. User uploads photos through presigned object-storage URLs.
5. System validates age, required fields, media safety, consent, and publication rules.
6. AI can propose bios and a quality score asynchronously.
7. User previews and publishes the profile.

### 4.3 Discovery and compatibility

1. User sets partner preferences and explicit dealbreakers.
2. User can use structured filters or natural-language search.
3. Policy filters remove blocked, hidden, ineligible, or unauthorized profiles.
4. Deterministic compatibility logic creates a score from declared facts and preferences.
5. AI explains the score and suggests respectful discussion topics; it does not invent facts.
6. User views, shortlists, hides, or sends an interest.

### 4.4 Interest to match

1. Sender sends an idempotent interest with an optional safe introduction.
2. Recipient accepts, declines, or leaves it pending.
3. Acceptance creates a match and conversation according to policy.
4. Either side can unmatch, block, or report at any time.

### 4.5 Secure communication

1. Only authorized participants can access a conversation.
2. Messages are encrypted in transit and at rest, rate-limited, scanned for malware, and checked against moderation policy.
3. AI may draft, translate, or tone-adjust text only on explicit request and must show a preview before sending.
4. Contact-detail sharing follows configurable safety policy and user consent.
5. Receipt, unread count, block, report, retention, and deletion behavior is consistent across REST and real-time delivery.

### 4.6 Verification and trust

1. User chooses an available verification check.
2. A provider or trained reviewer validates the minimum required evidence.
3. Public UI shows check status and date, not raw documents.
4. A transparent trust summary is based on completed checks and observed safety signals, with appeal paths.
5. AI risk signals never automatically ban a user; high-impact actions require policy and human review.

### 4.7 Subscription

1. User views plans and entitlements in its country/currency.
2. Hosted provider checkout handles payment details.
3. Signed webhook updates subscription and entitlement state idempotently.
4. Billing history, cancellation, renewal, refund, and support paths are available.

## 5. MVP capabilities

### Platform and brand

- Host-to-brand resolution, experience configuration, localization scaffolding, feature flags, and network isolation.
- Parent/candidate-friendly role model and explicit profile-management consent.

### Accounts and profiles

- Email and/or phone authentication, secure sessions, recovery, consent records, and account deletion/export requests.
- Structured candidate, family, education, employment, language, interest, lifestyle, religious-practice, location, and partner-preference data.
- Profile completeness, draft/review/published/paused states, preview, visibility, media, and generated biodata.

### Discovery and matchmaking

- Structured search, natural-language-to-filter draft, pagination, shortlist, hide, view history, explainable compatibility, interests, matches, and feedback.
- Deterministic hard filters before ranking: network, publication state, age eligibility, visibility, blocks, and dealbreakers.

### Communication and safety

- Authorized one-to-one/family-aware conversations, attachments, receipts, unread counts, WebSocket delivery with REST fallback, block/report, moderation, and audit.
- AI drafts, translation among initially supported languages, tone help, and safety warnings.

### Trust and operations

- Identity verification integration boundary, manual review fallback, trust summary, reports, moderation cases, sanctions, appeals, and admin queues.
- Email notifications at minimum; SMS/WhatsApp/push are provider-gated additions.
- Plans, subscriptions, entitlements, payment webhooks, refunds/support visibility, and immutable payment audit.
- Admin tools for profiles, reports, verification, subscriptions, brand configuration, reference data, and AI job inspection.

### Launch AI

- Profile field extraction with user confirmation.
- Bio drafts.
- Profile quality score with actionable missing items.
- Hybrid compatibility score and grounded explanation.
- Natural-language search converted to an editable filter draft.
- Communication drafts, translation, and tone assistance.

## 6. Explicitly later

- Behavioral personalized recommendations beyond simple feedback signals.
- Advanced fraud models, duplicate-face detection, social-presence checks, and automated document analysis.
- Family compatibility graph and family knowledge graph.
- Parent question-answering assistant with curated knowledge.
- Success prediction or relationship insights.
- Voice assistant, native mobile applications, and wedding-planning marketplace.
- OpenSearch, Kafka, independently deployed business microservices, or separate flavor databases without measured need.

## 7. Non-functional targets for the first release

These are planning targets to validate with load tests, not expected traffic claims.

| Area | Initial target |
|---|---|
| Registered accounts | 1,000 |
| Concurrent active users | 100 test target |
| API load | 20 requests/second sustained, 100 requests/second short burst |
| Availability | 99.5% monthly for the application, excluding planned maintenance |
| Non-AI API latency | p95 under 400 ms for ordinary reads/writes; search p95 under 700 ms |
| Interactive AI | acknowledge within 500 ms with a job ID; publish completion status asynchronously |
| Recovery point | 15 minutes or better for production database |
| Recovery time | 4 hours or better for the initial production service |
| Accessibility | WCAG 2.2 AA target for the later frontend |
| Browser support | Current and previous major versions of Chrome, Edge, Safari, and Firefox |

Production should run at least two API tasks across availability zones when budget permits. Worker counts scale independently from queue depth.

## 8. Product safety principles

- Use neutral, respectful wording. Theme variants may be selected by brand or user preference, but must not assume who operates a profile or enforce gender stereotypes.
- Treat religion, caste/community, health, marital history, identity documents, precise location, and private communications as sensitive.
- Collect only information that has a defined user benefit, retention period, and access policy.
- Make visibility and contact sharing explicit.
- Explain verification, trust, compatibility, and moderation outcomes with an appeal/correction path.
- Do not expose hidden dealbreakers or private scoring details to another profile.
- Do not use protected or sensitive characteristics for advertising optimization.
- Keep humans responsible for suspensions, verification disputes, and other high-impact outcomes.

## 9. Launch outcomes

The MVP is ready for controlled beta only when users can safely complete the full path:

`register → consent → create/publish profile → discover → understand compatibility → send/accept interest → communicate → block/report → subscribe/manage account`

Operational launch additionally requires moderation coverage, support ownership, privacy/terms approval, incident procedures, monitoring, backups, restore evidence, and a tested rollback.

## 10. Business metrics

- Onboarding completion and median time to publish.
- Percentage of publishable/verified profiles.
- Search-to-profile-view, view-to-interest, interest-acceptance, and match-to-conversation conversion.
- Meaningful reciprocal conversations, not raw message volume.
- Report rate, confirmed abuse rate, moderation time, and appeal reversals.
- Retention at 7/30/90 days, paid conversion, renewal, refund, and support burden.
- User-rated compatibility explanation usefulness.
- Successful outcomes reported with explicit consent; never pressure users to disclose marriage details.
