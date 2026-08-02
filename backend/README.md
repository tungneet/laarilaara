# LaariLaara backend (serverless, FastAPI on Lambda)

Implementation of the serverless variant described in [../documents/lambda-based/README.md](../documents/lambda-based/README.md).

- **Runtime:** one FastAPI app served by AWS Lambda via Mangum, behind API Gateway HTTP API (`ANY /{proxy+}`).
- **Storage (decided):** DynamoDB for hot-path transactional state; S3 for media, AI artifacts, and embedding vectors; Glue/Athena for analytics. RDS deferred.
- **Contract:** [../documents/lambda-based/04-api-catalog.md](../documents/lambda-based/04-api-catalog.md).

## Layout

```text
backend/
  app/
    main.py            # FastAPI app factory + middleware wiring
    lambda_handler.py  # Mangum adapter (Lambda entrypoint)
    core/
      config.py        # typed settings (pydantic-settings)
      logging.py       # structured JSON logging
      errors.py        # RFC 9457 problem+json handlers
      context.py       # request-id / correlation middleware
      security.py      # password hashing, tokens, JWT access tokens + short-lived realtime WebSocket connect tokens
      dynamodb.py       # single-table DynamoDB access
      s3.py              # presigned PUT/GET URL generation + head-object check (media bytes never pass through Lambda)
      pagination.py      # shared base64-offset cursor encode/decode helper (§7 discovery, §8 interests/matches)
      realtime_manager.py # §9 in-process WebSocket connection manager (dev/pytest only — not a substitute for API Gateway's PostToConnection in a real multi-instance deployment)
    domain/
      accounts.py       # pure account model
      reference_data.py # static seed data for public reference/plans endpoints
      media.py           # MediaAssetStatus / BiodataStatus enums
    services/
      auth.py           # register/verify/login/refresh/logout/password-reset logic
      accounts.py       # /v1/me profile read/update logic
      sessions.py       # /v1/me/sessions listing/revocation logic
      consents.py       # /v1/me/consents recording/summary logic
      contacts.py       # /v1/me/contacts add/verify/remove logic (masking, dedup, last-verified-contact rule)
      data_requests.py  # /v1/me/data-requests create/read logic
      profiles.py       # /v1/profiles aggregate + lifecycle logic (create/patch/preview/completion/submit/publish/pause/resume/delete)
      profile_managers.py # managers list, invite/accept, patch/revoke, candidate-consent logic
      profile_sections.py # personal-details/narratives/lifestyle/visibility single-resource sections
      profile_sets.py   # communities/religious-practices/languages/interests replace-set sections
      profile_records.py # education/employment list/CRUD-record sections
      profile_family.py # family summary (PUT full-replace) + family/members list/CRUD-record sections
      profile_preferences.py # main preferences summary + 5 preference-set sub-collections
      profile_brands.py # brand/experience replace-set sections (no controlled list yet)
      media.py           # raw upload/media-asset create/complete/get/delete logic (checksum idempotency, ownership masking)
      profile_media.py  # profile media attach/list/patch/detach (reuses profile_records repo, kind=MEDIA; primary-exclusivity)
      profile_biodata.py # profile biodata generate/get (reuses profile_records repo, kind=BIODATA; "queued", no worker yet)
      discovery.py       # search/recommendations/get-public-profile/record-view (table-scan search; no ranking index yet)
      saved_searches.py  # saved-search CRUD (reuses profile_records repo, kind=SAVEDSEARCH; idempotent-by-name create)
      shortlist.py       # shortlist CRUD (reuses profile_target_links repo, kind=SHORTLIST)
      hidden_profiles.py # hide/unhide (reuses profile_target_links repo, kind=HIDDEN; no block/safety system yet)
      compatibility.py   # compatibility analysis create/refresh/get (deterministic placeholder score; no embeddings pipeline yet)
      interests.py       # interest send/list/accept/decline/withdraw state machine; accept creates a match
      matches.py         # match list/get/end/feedback/outcomes (conversation_id always None; no messaging yet)
      entitlements.py   # freemium/premium seam (+ effective_view for GET /v1/entitlements)
      notifications.py  # outbound verification code stub (unrelated dev-stub — NOT the §12 in-app notifications domain)
      notification_center.py # §12 in-app notifications/preferences/push-endpoints logic (account-scoped, not profile-scoped); named to avoid colliding with notifications.py above
      billing.py        # §13 checkout-sessions/subscription/transactions logic; no payment provider, always free tier
      promo_redemptions.py # §13 promo code validation + idempotent redemption
      realtime.py       # §9 WebSocket half: realtime-token issuance, $connect/$disconnect bookkeeping, typing dispatch, message/read event push
      admin_dashboard.py # §15 aggregate dashboard counts + synthesized queue-health view
      admin_directory.py # §15 admin bypass account/profile listing+lookup
      admin_moderation.py # §15 moderation case list/assign/act/close (creates real ModerationAction rows)
      admin_verification.py # §15 verification-request approve/reject decision (first real approve/reject transition)
      admin_billing.py  # §15 subscriptions/transactions read-only lists + support-ticket CRUD
      admin_config.py   # §15 brand/experience/feature-flag config get/update
      admin_reference.py # §15 generic reference-data list/create/update/deactivate
    repositories/
      accounts.py       # account persistence
      challenges.py     # verification challenge persistence (purpose- and subject-aware)
      sessions.py       # refresh-token session persistence + listing
      consents.py       # append-only versioned consent decisions
      contacts.py       # contact persistence (masking done in service layer)
      data_requests.py  # export/correction/deletion request persistence
      profiles.py       # profile aggregate persistence (root fields only; sections are later batches)
      profile_managers.py # profile manager rows + owner permission checks + self-profile idempotency lookup
      profile_manager_invitations.py # invite tokens (hashed) + GSI1 lookup by token + accept state transition
      profile_candidate_consents.py  # append-only candidate publication/management consent decisions
      profile_sections.py # generic single-resource section item storage (PK=PROFILE#id/SK=SECTION#name)
      profile_sets.py   # generic replace-set item storage (PK=PROFILE#id/SK=SET#name)
      profile_records.py # generic list/CRUD record storage (PK=PROFILE#id/SK={KIND}#recordId)
      media_assets.py   # raw media asset persistence (PK=MEDIAASSET#id/SK=MEDIAASSET) + GSI1 checksum idempotency lookup
      profile_target_links.py # generic keyed target-profile link storage (PK=PROFILE#id/SK={KIND}#targetProfileId) — shortlist + hidden-profiles
      profile_views.py  # idempotent-within-a-day profile-view event storage (PK=PROFILE#viewerId/SK=VIEW#targetId#date)
      compatibility_analyses.py # analysis storage (PK=ANALYSIS#id/SK=ANALYSIS) + GSI1 pair-key lookup for idempotent refresh
      interests.py       # interest storage (PK=INTEREST#id/SK=INTEREST); list/idempotency via table scan (no per-profile GSI yet)
      matches.py         # match/feedback/outcome storage (PK=MATCH#id/SK=MATCH|FEEDBACK#author|OUTCOME#author); list via table scan
      conversations.py   # conversation storage (PK=CONVERSATION#id/SK=CONVERSATION), per-profile read_markers/muted maps
      messages.py        # message storage (PK=CONVERSATION#id/SK=MESSAGE#sortKey#id) + GSI1 lookup-by-id for edit/delete
      ai_artifacts.py    # AI artifact/operation storage (PK=ARTIFACT#id/SK=ARTIFACT) + per-profile feedback rows; always status=queued, no worker yet
      reports.py         # report storage (PK=REPORT#id/SK=REPORT); always status=queued, no moderation worker yet
      verification_requests.py # verification request storage (PK=VERIFICATIONREQUEST#id/SK=VERIFICATIONREQUEST); draft->submitted, never approved/rejected (no admin surface yet)
      moderation_actions.py # moderation action + appeal storage (PK=MODERATIONACTION#id/SK=MODERATIONACTION|APPEAL#accountId); no action-creation endpoint exists yet (§15 admin, unbuilt)
      notification_center.py # notification storage (PK=ACCOUNT#accountId/SK=NOTIFICATION#sortKey#id) + GSI1 lookup-by-id; newest-first list; no worker creates rows yet
      notification_preferences.py # single preference item per account (PK=ACCOUNT#accountId/SK=NOTIFICATIONPREFERENCES); full-replace on PUT
      push_endpoints.py # push endpoint storage (PK=ACCOUNT#accountId/SK=PUSHENDPOINT#id) + GSI1 lookup-by-id for delete; raw token never returned
      billing.py        # checkout-session/subscription/transaction storage (all PK=ACCOUNT#accountId); no payment provider, checkout sessions stay pending forever
      promo_redemptions.py # promo redemption storage (PK=ACCOUNT#accountId/SK=PROMOREDEMPTION#code); idempotent upsert
      webhook_events.py # §14 durable capture of inbound provider webhook events (PK=WEBHOOKEVENT#kind#provider#externalId); conditional put for exactly-once idempotency; no worker reads these yet
      realtime_connections.py # §9 WebSocket connection registry (PK=PROFILE#profileId/SK=CONNECTION#id) + GSI1 lookup-by-connectionId for $disconnect
      admin_audit.py    # §15 append-only admin action audit log (PK=ADMINAUDIT#adminAccountId/SK=EVENT#sortKey#id); no read endpoint
      moderation_cases.py # §15 moderation case storage (PK=MODERATIONCASE#id/SK=MODERATIONCASE); no creation endpoint, white-box only
      support_tickets.py # §15 support ticket storage (PK=SUPPORTTICKET#id/SK=SUPPORTTICKET); first admin resource with a real create endpoint
      brand_configs.py  # §15 brand config storage (GET/PATCH only, must be seeded out-of-band)
      experience_configs.py # §15 experience config storage (GET/PATCH only, mirrors brand_configs.py)
      feature_flags.py  # §15 feature flag storage (GET/PATCH only)
      reference_data_admin.py # §15 generic reference-data item storage keyed by listName; never hard-deletes (deactivate only)
    routers/
      health.py         # GET /health/live, GET /health/ready
      reference.py      # GET /v1/context, /v1/reference/*, /v1/plans
      auth.py           # POST /v1/auth/... (register, verify, login, refresh, logout(-all), password reset)
      me.py             # GET/PATCH /v1/me, sessions, consents, contacts, data-requests
      profiles.py       # POST/GET/PATCH/DELETE /v1/profiles/{id}, preview, completion, submit/publish/pause/resume; managers/invitations/candidate-consent
      profile_sections.py # GET/PATCH personal-details, narratives, lifestyle, visibility
      profile_family.py # GET/PUT family, GET/POST family/members, PATCH/DELETE family/members/{id}
      profile_preferences.py # GET/PUT preferences + 5 preference-set sub-collections
      profile_brands.py # GET/PUT brands, GET/PUT experiences
      media.py           # POST /v1/uploads, POST /v1/uploads/{id}/complete, GET/DELETE /v1/media/{id}
      profile_media.py  # GET/POST /v1/profiles/{id}/media, PATCH/DELETE /v1/profiles/{id}/media/{mediaId}
      profile_biodata.py # POST /v1/profiles/{id}/biodata, GET /v1/profiles/{id}/biodata/{documentId}
      discovery.py       # POST /v1/discovery/search, GET /v1/discovery/recommendations, GET /v1/discovery/profiles/{id}, POST /v1/discovery/views
      saved_searches.py  # GET/POST /v1/saved-searches, PATCH/DELETE /v1/saved-searches/{id}
      shortlist.py       # GET /v1/shortlist, PUT/DELETE /v1/shortlist/{targetProfileId}
      hidden_profiles.py # PUT/DELETE /v1/hidden-profiles/{targetProfileId}
      compatibility.py   # POST /v1/compatibility-analyses, GET /v1/compatibility-analyses/{analysisId}
      interests.py       # GET/POST /v1/interests, POST /v1/interests/{id}/accept|decline|withdraw
      matches.py         # GET /v1/matches, GET/POST /v1/matches/{id}, end, feedback, outcomes
      conversations.py   # GET /v1/conversations, GET/POST .../messages, PATCH/DELETE .../messages/{id}, read, mute
      realtime.py         # POST /v1/realtime-tokens, plus a local-dev @router.websocket("/v1/realtime") standing in for API Gateway's $connect/$disconnect/$default
      ai.py              # 5 small routers: profile ai/ai-artifacts, discovery search-drafts, compatibility explanation, conversation assistant/translation/tone, generic ai-artifacts
      blocks.py          # GET /v1/blocks, PUT/DELETE /v1/blocks/{targetProfileId}
      reports.py         # POST/GET /v1/reports
      verification.py    # 2 small routers: profile trust-summary/verification-options/requests/claims, generic verification-requests
      moderation.py      # POST /v1/moderation-actions/{actionId}/appeals
      notifications.py   # 3 small routers: /v1/notifications, /v1/notification-preferences, /v1/push-endpoints
      billing.py         # 3 small routers: /v1/billing/{checkout-sessions,subscription,transactions}, /v1/entitlements, /v1/promo-redemptions
      webhooks.py         # POST /v1/webhooks/{billing,verification,notifications}/{provider} — HMAC-signed, unauthenticated-by-session
      admin.py            # §15 admin surface: 8 routers, 28 endpoints, all gated by get_current_admin_session
    schemas/
      auth.py           # auth request/response models
      account.py        # /v1/me request/response models
      session.py        # /v1/me/sessions response models
      consent.py        # /v1/me/consents request/response models
      contact.py        # /v1/me/contacts request/response models
      data_request.py   # /v1/me/data-requests request/response models
      profile.py        # /v1/profiles request/response models
      profile_manager.py # managers/invitations/candidate-consent request/response models
      profile_sections.py # personal-details/narratives/lifestyle/visibility request/response models
      profile_sets.py   # communities/religious-practices/languages/interests request/response models
      profile_records.py # education/employment request/response models
      profile_family.py # family/family-members request/response models
      profile_preferences.py # main preferences summary request/response models
      media.py           # upload/media-asset request/response models
      profile_media.py  # profile media attachment request/response models
      profile_biodata.py # biodata generation/document request/response models
      discovery.py       # search/recommendations/public-profile/view request/response models
      saved_search.py    # saved-search request/response models (reuses DiscoverySearchFilters)
      shortlist.py       # shortlist request/response models
      hidden_profile.py  # hidden-profile response models
      compatibility.py   # compatibility analysis request/response models
      interest.py        # interest request/response models
      match.py           # match/feedback/outcome request/response models
      conversation.py    # conversation/message request/response models
      realtime.py         # realtime-token request/response models
      ai.py              # AI artifact/operation request/response models (extraction/bio drafts, quality analyses, search/translation/assistant drafts, tone checks, explanation, feedback)
      block.py           # block request/response models
      report.py          # report request/response models
      verification.py    # trust-summary/verification-options/requests/evidence/claims request/response models
      moderation.py      # moderation-action appeal request/response models
      notification.py    # notification/preferences/push-endpoint request/response models
      billing.py         # checkout-session/subscription/transaction/entitlements/promo-redemption request/response models
      webhook.py         # webhook acknowledgement response model
      admin.py           # §15 admin request/response models (~35, covering all 7 sub-areas; shared reason field on every mutating request)
      reference.py      # reference/context/plans response models
  tests/
    test_health.py
    test_auth.py
    test_me.py
    test_reference.py
    test_contacts_and_data_requests.py
    test_profiles.py
    test_profile_managers.py
    test_profile_sections.py
    test_profile_sets.py
    test_profile_records.py
    test_profile_family.py
    test_profile_preferences.py
    test_profile_brands.py
    test_media.py
    test_profile_media.py
    test_profile_biodata.py
    test_discovery.py
    test_saved_searches.py
    test_shortlist.py
    test_hidden_profiles.py
    test_compatibility.py
    test_interests.py
    test_matches.py
    test_conversations.py
    test_ai.py
    test_trust_and_safety.py
    test_notifications.py
    test_billing.py
    test_webhooks.py
    test_admin.py
    test_realtime.py
  requirements.txt
  requirements-dev.txt
```

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
Copy-Item config.yaml.example config.yaml
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

`config.yaml` and `.env` are both gitignored local files; only their
`.example` templates are committed.

Then open http://127.0.0.1:8000/health/live and http://127.0.0.1:8000/docs.

## Tests

```powershell
pytest
```

## Build status

Implemented endpoints are tracked as they are added:

- [x] `GET /health/live`
- [x] `GET /health/ready`
- [x] `POST /v1/auth/register`
- [x] `POST /v1/auth/challenges/{challengeId}/verify`
- [x] `POST /v1/auth/login`
- [x] `POST /v1/auth/refresh`
- [x] `POST /v1/auth/logout`
- [x] `POST /v1/auth/logout-all`
- [x] `POST /v1/auth/password/forgot`
- [x] `POST /v1/auth/password/reset`
- [x] `GET /v1/me`
- [x] `PATCH /v1/me`
- [x] `GET /v1/me/sessions`
- [x] `DELETE /v1/me/sessions/{sessionId}`
- [x] `GET /v1/me/consents`
- [x] `POST /v1/me/consents`
- [x] `GET /v1/context`
- [x] `GET /v1/reference/countries`
- [x] `GET /v1/reference/regions`
- [x] `GET /v1/reference/languages`
- [x] `GET /v1/reference/communities`
- [x] `GET /v1/reference/religious-practices`
- [x] `GET /v1/reference/education-levels`
- [x] `GET /v1/reference/occupation-categories`
- [x] `GET /v1/reference/interests`
- [x] `GET /v1/plans`
- [x] `GET /v1/me/contacts`
- [x] `POST /v1/me/contacts`
- [x] `POST /v1/me/contacts/{contactId}/verify`
- [x] `DELETE /v1/me/contacts/{contactId}`
- [x] `POST /v1/me/data-requests`
- [x] `GET /v1/me/data-requests/{requestId}` (catalog §4 complete; next: §5 profiles/managers/family/preferences)
- [x] `POST /v1/profiles` (idempotent for relationship=self)
- [x] `GET /v1/profiles/{profileId}`
- [x] `PATCH /v1/profiles/{profileId}`
- [x] `GET /v1/profiles/{profileId}/preview` (stub pending sections)
- [x] `GET /v1/profiles/{profileId}/completion` (stub pending sections)
- [x] `POST /v1/profiles/{profileId}/submit`
- [x] `POST /v1/profiles/{profileId}/publish`
- [x] `POST /v1/profiles/{profileId}/pause`
- [x] `POST /v1/profiles/{profileId}/resume`
- [x] `DELETE /v1/profiles/{profileId}` (catalog §5 aggregate+lifecycle block complete; managers/consent block complete; next: §5 sections)
- [x] `GET /v1/profiles/{profileId}/managers`
- [x] `POST /v1/profiles/{profileId}/manager-invitations`
- [x] `POST /v1/profile-manager-invitations/{token}/accept`
- [x] `PATCH /v1/profiles/{profileId}/managers/{accountId}`
- [x] `DELETE /v1/profiles/{profileId}/managers/{accountId}`
- [x] `POST /v1/profiles/{profileId}/candidate-consent` (catalog §5 fully complete except sections; next: §5 sections, then §6 media, §7 discovery)
- [x] `GET/PATCH /v1/profiles/{profileId}/personal-details`
- [x] `GET/PATCH /v1/profiles/{profileId}/narratives`
- [x] `GET/PATCH /v1/profiles/{profileId}/lifestyle`
- [x] `GET/PATCH /v1/profiles/{profileId}/visibility`
- [x] `GET/PUT /v1/profiles/{profileId}/communities`
- [x] `GET/PUT /v1/profiles/{profileId}/religious-practices`
- [x] `GET/PUT /v1/profiles/{profileId}/languages`
- [x] `GET/PUT /v1/profiles/{profileId}/interests`
- [x] `GET/POST /v1/profiles/{profileId}/education`
- [x] `GET/PATCH/DELETE /v1/profiles/{profileId}/education/{recordId}`
- [x] `GET/POST /v1/profiles/{profileId}/employment`
- [x] `GET/PATCH/DELETE /v1/profiles/{profileId}/employment/{recordId}`
- [x] `GET/PUT /v1/profiles/{profileId}/family`
- [x] `GET/POST /v1/profiles/{profileId}/family/members`
- [x] `PATCH/DELETE /v1/profiles/{profileId}/family/members/{memberId}`
- [x] `GET/PUT /v1/profiles/{profileId}/preferences`
- [x] `GET/PUT /v1/profiles/{profileId}/preferences/countries`
- [x] `GET/PUT /v1/profiles/{profileId}/preferences/languages`
- [x] `GET/PUT /v1/profiles/{profileId}/preferences/communities`
- [x] `GET/PUT /v1/profiles/{profileId}/preferences/religious-practices`
- [x] `GET/PUT /v1/profiles/{profileId}/preferences/education-levels`
- [x] `GET/PUT /v1/profiles/{profileId}/brands`
- [x] `GET/PUT /v1/profiles/{profileId}/experiences` (catalog §5 fully complete — all Sections batches A-F done)
- [x] `POST /v1/uploads`, `POST /v1/uploads/{uploadId}/complete`, `GET/DELETE /v1/media/{assetId}` — raw media asset lifecycle
- [x] `GET/POST /v1/profiles/{profileId}/media`, `PATCH/DELETE /v1/profiles/{profileId}/media/{profileMediaId}` — profile media attachment
- [x] `POST /v1/profiles/{profileId}/biodata`, `GET /v1/profiles/{profileId}/biodata/{documentId}` (catalog §6 fully complete — 10/10 endpoints)
- [x] `POST /v1/discovery/search`, `GET /v1/discovery/recommendations`, `GET /v1/discovery/profiles/{profileId}`, `POST /v1/discovery/views`
- [x] `GET/POST /v1/saved-searches`, `PATCH/DELETE /v1/saved-searches/{searchId}`
- [x] `GET /v1/shortlist`, `PUT/DELETE /v1/shortlist/{targetProfileId}`
- [x] `PUT/DELETE /v1/hidden-profiles/{targetProfileId}` (catalog §7 fully complete — 13/13 endpoints)
- [x] `POST /v1/compatibility-analyses`, `GET /v1/compatibility-analyses/{analysisId}`
- [x] `GET/POST /v1/interests`, `POST /v1/interests/{interestId}/accept|decline|withdraw`
- [x] `GET /v1/matches`, `GET/POST /v1/matches/{matchId}`, `POST .../end`, `POST .../feedback`, `POST .../outcomes` (catalog §8 fully complete — 12/12 endpoints)
- [x] `GET /v1/conversations`, `GET /v1/conversations/{conversationId}`, `GET/POST .../messages`, `PATCH/DELETE .../messages/{messageId}`, `POST .../read`, `POST .../mute` (catalog §9 REST fully complete — 8/8 endpoints)
- [x] `POST /v1/realtime-tokens`, WebSocket `$connect`/`$disconnect`/`$default` (catalog §9 WebSocket half complete; short-lived `type=realtime` JWT issued by the REST endpoint, validated on connect; `app/repositories/realtime_connections.py` is the DynamoDB `core.realtime_connections` equivalent; server push wired into message send/edit/delete and read-marker updates (`message.created`/`message.updated`/`message.deleted`/`conversation.read`), plus client-originated `typing.start`/`typing.stop` dispatched as `typing.changed`; `operation.updated`/`notification.created`/`match.updated` are NOT wired up yet — no code path constructs those events currently, documented gap in `app/services/realtime.py`; locally this is a native FastAPI `@router.websocket` route with an in-process connection manager (`app/core/realtime_manager.py`) since Starlette TestClient/uvicorn have no equivalent to API Gateway's WebSocket API — on AWS, `$connect`/`$disconnect`/`$default` are separate Lambda integrations, not reachable through the Mangum ASGI adapter, and push goes through `apigatewaymanagementapi.PostToConnection` instead of the in-process manager; catalog §9 fully complete — 9/9 endpoints)
- [x] `POST /v1/profiles/{profileId}/ai/extraction-drafts`, `POST .../ai/bio-drafts`, `POST .../ai/quality-analyses`, `POST .../ai-artifacts/{artifactId}/apply`, `POST /v1/discovery/search-drafts`, `POST /v1/compatibility-analyses/{analysisId}/explanation`, `POST /v1/conversations/{conversationId}/assistant-drafts`, `POST .../translation-drafts`, `POST .../tone-checks`, `GET /v1/ai-artifacts/{artifactId}`, `POST .../feedback` (catalog §10 fully complete — 11/11 endpoints; every artifact stays `status=queued` forever — no async AI worker/adapter exists yet, so `apply` always returns 409)
- [x] `GET /v1/blocks`, `PUT/DELETE /v1/blocks/{targetProfileId}`, `POST/GET /v1/reports`, `GET /v1/profiles/{profileId}/trust-summary`, `GET .../verification-options`, `POST .../verification-requests`, `GET /v1/verification-requests/{requestId}`, `POST .../evidence`, `POST .../submit`, `GET /v1/profiles/{profileId}/verification-claims`, `POST /v1/moderation-actions/{actionId}/appeals` (catalog §11 fully complete — 13/13 endpoints; verification requests only reach `submitted`, never `approved`/`rejected` — no admin verification-decision endpoint exists yet (§15, unbuilt), so trust-summary/verification-claims always report unverified; block resource exists but is not yet enforced against discovery/interests/conversations (cross-cutting pass still needed); moderation-action appeals seed actions via a white-box repo call in tests since no admin action-creation endpoint exists either)
- [x] `GET /v1/notifications`, `POST /v1/notifications/{notificationId}/read`, `POST /v1/notifications/read-all`, `GET/PUT /v1/notification-preferences`, `POST /v1/push-endpoints`, `DELETE /v1/push-endpoints/{endpointId}` (catalog §12 fully complete — 7/7 endpoints; all resources are account-scoped, not profile-scoped; no SQS-triggered notification worker exists yet so nothing creates notifications in the running API — tests seed rows via a white-box repo call; push-endpoint tokens are stored but never returned in any response; next: §13, or circle back to §9's WebSocket half)
- [x] `POST /v1/billing/checkout-sessions`, `GET /v1/billing/subscription`, `POST /v1/billing/subscription/cancel`, `POST /v1/billing/subscription/resume`, `GET /v1/billing/transactions`, `GET /v1/entitlements`, `POST /v1/promo-redemptions` (catalog §13 fully complete — 7/7 endpoints; no real payment provider or webhook worker (§14, unbuilt) is wired up — checkout sessions never leave `status=pending`, and the subscription always mirrors the account's own free tier since nothing ever upgrades it; transactions have no creation endpoint anywhere so tests seed rows via a white-box repo call; entitlements view reuses the existing `app/services/entitlements.py` seam (currently grants every action); promo redemption is idempotent-by-code against a small static approved-code list; next: §14 webhooks, or circle back to §9's WebSocket half)
- [x] `POST /v1/webhooks/billing/{provider}`, `POST /v1/webhooks/verification/{provider}`, `POST /v1/webhooks/notifications/{provider}` (catalog §14 fully complete — 3/3 endpoints; unauthenticated-by-session — HMAC-SHA256 signature over `timestamp.rawBody` with a single shared `settings.webhook_signing_secret` (our own convention; no real provider is wired up yet so there's no provider-mandated format to match), plus a 5-minute replay window and a per-kind provider allowlist (`app/domain/webhooks.py`); durable capture is idempotent-by-external-id via a conditional DynamoDB put; no async worker processes captured events further — same "queued forever, no worker" gap as reports/notifications/billing-transactions; next: §15 admin surface (large, likely multi-batch), or circle back to §9's WebSocket half)
- [x] `GET /v1/admin/dashboard`, `GET /v1/admin/queue-health`, `GET/PATCH /v1/admin/accounts`, `GET/PATCH /v1/admin/profiles`, `GET/PATCH/POST /v1/admin/moderation-cases` (+assign/act/close), `GET/POST /v1/admin/verification-requests` (+decide), `GET /v1/admin/subscriptions`, `GET /v1/admin/transactions`, `GET/POST/PATCH /v1/admin/support-tickets`, `GET/PATCH /v1/admin/brands/{id}`, `GET/PATCH /v1/admin/experiences/{id}`, `GET/PATCH /v1/admin/feature-flags/{id}`, `GET/POST/PATCH/DELETE /v1/admin/reference-data/{listName}` (catalog §15 fully complete — 28/28 endpoints; new admin-role foundation: `Account.role` (`member`/`admin`) baked into the JWT at login/refresh, `get_current_admin_session` dependency 403s non-admins with `ADMIN_REQUIRED` (not masked as 404, unlike the rest of the API); no self-serve admin-creation endpoint exists — promotion is white-box only (`accounts_repo.set_role`), re-login required for a fresh token; every mutating admin call is captured in an append-only audit log (`app/repositories/admin_audit.py`, no read endpoint) and requires a `reason` field; brand/experience/feature-flag configs are GET/PATCH only — must be seeded out-of-band; reference-data is one generic CRUD trio keyed by `listName`, not yet wired into the existing static lists in `reference_data.py`/`billing.py`; this batch also closed two previously-documented gaps: `admin_verification.decide()` is the first-ever approve/reject transition, now read live by `_approved_check_types` so trust-summary/verification-claims can finally report real verified status, and `admin_moderation.act_on_case` is the first real moderation-action creator; support tickets are the first admin resource with a genuine create endpoint; dashboard/queue-health are synthesized aggregate views, not their own stored entities; next: §9's WebSocket half)
