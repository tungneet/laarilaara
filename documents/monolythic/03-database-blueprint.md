# Database blueprint

## 1. Database principles

- PostgreSQL is the authoritative store. Redis, search projections, analytics, and AI artifacts are rebuildable.
- Use one database and one LaaraLaari `network_id` initially. A brand or experience is not a separate tenant.
- Every network-owned row includes `network_id`; every unique key and lookup that could cross networks includes it.
- IDs are application-generated UUIDv7 values. External/public identifiers are opaque and never sequential.
- Store timestamps as UTC `timestamptz`; store user time zones as IANA names.
- Money is an integer in minor units plus ISO 4217 currency.
- Country and language use ISO/BCP-47 codes. Phone values are normalized to E.164 before hashing/encryption.
- Use `jsonb` for versioned provider payloads and genuinely variable metadata—not for searchable core facts.
- Use text plus `CHECK` constraints for business states unless a PostgreSQL enum has a clear migration benefit.
- Optimistic aggregates include `version integer`; updates require the expected version.
- Default to hard delete for accidental drafts with no legal/audit value and explicit lifecycle states for published/regulated records. Do not add `deleted_at` to every table blindly.
- Raw photos/documents/message bodies remain in object storage or encrypted columns as defined below; never log them.

### PostgreSQL extensions

- `citext` for normalized case-insensitive handles where useful.
- `pg_trgm` and `unaccent` for initial text search.
- `pgcrypto` for database utilities, not as a substitute for KMS/secrets management.
- `vector` only when the Phase 2 recommendation design and selected embedding dimensions are approved.

## 2. Schema ownership

| PostgreSQL schema | Owner module | Purpose |
|---|---|---|
| `core` | Network & Brand / Platform | Network configuration, idempotency, events, jobs, async operations |
| `identity` | Identity & Access | Accounts, auth identities, contacts, sessions, roles, invitations, consent |
| `reference` | Reference Data | Controlled vocabularies and localized labels |
| `profile` | Profile | Candidate, managers, facts, family, preferences, publication, revisions |
| `media` | Media | Uploads, assets, processing, profile media, generated documents |
| `discovery` | Discovery | Search projection, saved searches, views, shortlists, hides, recommendations |
| `matchmaking` | Matchmaking | Compatibility, interests, matches, feedback, outcomes |
| `chat` | Messaging | Conversations, participants, messages, receipts, attachments |
| `trust` | Trust & Safety | Blocks, reports, moderation, risk signals, sanctions, appeals |
| `verification` | Verification | Verification definitions, requests, claims, evidence references, provider events |
| `ai` | AI Orchestration | Routes, prompts, jobs, artifacts, feedback, and evaluations |
| `notification` | Notification | Preferences, notifications, templates, endpoint and delivery state |
| `billing` | Billing & Entitlements | Plans, prices, customers, subscriptions, transactions, entitlements, webhooks |
| `analytics` | Analytics | Minimized product events, projections, and experiments |
| `audit` | Audit & Compliance / Support | Immutable audit, support, export/deletion requests, legal holds |

Only a module's repositories write its schema. Database users for migrations, application runtime, read-only support, and analytics are separate.

## 3. Table catalog

Columns listed below are the required baseline, not every eventual audit timestamp. Unless stated otherwise, mutable tables include `created_at` and `updated_at`.

### 3.1 `core`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `core.networks` | `id`, `key`, `name`, `status`, `default_locale`, `default_timezone`, `settings_json` | Root data-sharing/isolation boundary; unique `key` |
| `core.brands` | `id`, `network_id`, `key`, `name`, `status`, `default_locale`, `theme_tokens_json`, `content_config_json` | Presentation/marketing brand; unique `(network_id,key)` |
| `core.brand_domains` | `id`, `network_id`, `brand_id`, `hostname`, `is_primary`, `redirect_to_domain_id`, `status` | Trusted host mapping; globally unique normalized `hostname`; prevent redirect cycles |
| `core.experiences` | `id`, `network_id`, `brand_id`, `key`, `name`, `status`, `theme_overrides_json`, `default_filter_json`, `content_config_json`, `sort_order` | User-selectable Amritdhari/NRI/etc. experience; unique `(brand_id,key)` |
| `core.feature_flags` | `id`, `network_id`, `key`, `enabled`, `rules_json`, `version` | Server-side release/capability controls; unique `(network_id,key)` |
| `core.idempotency_keys` | `id`, `network_id`, `account_id`, `scope`, `key_hash`, `request_hash`, `response_status`, `response_body_json`, `expires_at` | Replays mutating API results; unique `(network_id,account_id,scope,key_hash)` |
| `core.async_operations` | `id`, `network_id`, `kind`, `subject_type`, `subject_id`, `status`, `progress`, `error_code`, `requested_by_account_id`, `started_at`, `completed_at`, `expires_at` | Stable status resource returned by `202` APIs |
| `core.outbox_events` | `id`, `network_id`, `event_type`, `event_version`, `aggregate_type`, `aggregate_id`, `aggregate_version`, `correlation_id`, `causation_id`, `trace_id`, `payload_json`, `occurred_at`, `available_at`, `published_at`, `attempt_count`, `lease_owner`, `lease_expires_at`, `last_error_code` | Written in the business transaction; partial index where `published_at IS NULL` |
| `core.inbox_events` | `consumer_name`, `event_id`, `event_type`, `received_at`, `processed_at`, `result_status`, `last_error_code` | Consumer deduplication; primary key `(consumer_name,event_id)` |
| `core.scheduled_jobs` | `id`, `network_id`, `job_type`, `subject_type`, `subject_id`, `run_at`, `status`, `payload_json`, `attempt_count`, `lease_owner`, `lease_expires_at`, `dedupe_key` | Reminder/expiry/cleanup scheduler; unique active `dedupe_key` where present |

`payload_json` contains IDs and minimized operational fields. It must not contain contact details, raw documents, message bodies, or unnecessary profile facts.

### 3.2 `identity`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `identity.accounts` | `id`, `network_id`, `status`, `display_name`, `locale`, `timezone`, `last_login_at`, `version`, `suspended_at` | Login principal, separate from candidate; index `(network_id,status)` |
| `identity.account_contacts` | `id`, `network_id`, `account_id`, `kind`, `value_ciphertext`, `value_hash`, `is_primary`, `verified_at` | Email/phone encrypted; unique `(network_id,kind,value_hash)`; never return ciphertext |
| `identity.auth_identities` | `id`, `network_id`, `account_id`, `provider`, `provider_subject_hash`, `password_hash`, `metadata_json`, `last_used_at` | Password or external login identity; unique `(network_id,provider,provider_subject_hash)` |
| `identity.auth_challenges` | `id`, `network_id`, `purpose`, `contact_id`, `secret_hash`, `attempt_count`, `max_attempts`, `expires_at`, `consumed_at`, `request_ip_hash` | OTP/magic-link/recovery challenge; short retention and one-time use |
| `identity.sessions` | `id`, `network_id`, `account_id`, `family_id`, `refresh_token_hash`, `user_agent_hash`, `ip_prefix_hash`, `created_at`, `last_seen_at`, `expires_at`, `revoked_at`, `revoke_reason` | Refresh/session rotation and family-wide theft response; hashes only |
| `identity.roles` | `id`, `key`, `description`, `permissions_json` | Seeded platform role catalog; unique `key` |
| `identity.account_roles` | `network_id`, `account_id`, `role_id`, `scope_type`, `scope_id`, `granted_by_account_id`, `expires_at` | Scoped moderator/verifier/support/admin grants; composite primary key |
| `identity.invitations` | `id`, `network_id`, `kind`, `target_contact_hash`, `inviter_account_id`, `subject_type`, `subject_id`, `permission_json`, `token_hash`, `status`, `expires_at`, `accepted_by_account_id` | Profile-manager/family collaboration invitation; one-time token |
| `identity.consent_records` | `id`, `network_id`, `account_id`, `profile_id`, `consent_type`, `document_version`, `decision`, `source`, `recorded_at`, `withdrawn_at`, `evidence_json` | Append-oriented terms/privacy/AI/marketing/profile-management consent |
| `identity.account_devices` | `id`, `network_id`, `account_id`, `device_key_hash`, `label`, `first_seen_at`, `last_seen_at`, `trusted_at`, `revoked_at` | Device/session safety metadata; no invasive fingerprinting |

### 3.3 `reference`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `reference.countries` | `code`, `name`, `status`, `sort_order`, `metadata_json` | ISO 3166-1 country seed; primary key `code` |
| `reference.regions` | `id`, `country_code`, `code`, `name`, `status` | State/province; unique `(country_code,code)` |
| `reference.languages` | `code`, `name`, `native_name`, `status` | BCP-47 language codes |
| `reference.communities` | `id`, `network_id`, `parent_id`, `key`, `display_name`, `description`, `status`, `sort_order` | Reviewed self-identification taxonomy; hierarchical; never inferred |
| `reference.religious_practices` | `id`, `network_id`, `key`, `display_name`, `description`, `status` | Optional self-declared practices such as Amritdhari |
| `reference.education_levels` | `id`, `network_id`, `key`, `display_name`, `rank`, `status` | Searchable normalized education level |
| `reference.occupation_categories` | `id`, `network_id`, `parent_id`, `key`, `display_name`, `status` | Searchable occupation taxonomy |
| `reference.interests` | `id`, `network_id`, `key`, `display_name`, `status` | Reviewed interests/hobbies taxonomy |
| `reference.relationship_types` | `key`, `display_name`, `policy_json`, `status` | Self/parent/sibling/relative/guardian collaborator policy |
| `reference.localized_labels` | `id`, `network_id`, `entity_type`, `entity_id`, `locale`, `label`, `description` | Localized controlled-vocabulary labels; unique entity/locale |

Seeds are versioned migrations or reviewed seed packages. Removing an option deactivates it; it does not rewrite user history.

### 3.4 `profile`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `profile.profiles` | `id`, `network_id`, `candidate_account_id`, `created_by_account_id`, `public_handle`, `status`, `publication_status`, `preferred_locale`, `version`, `submitted_at`, `published_at`, `paused_at` | Candidate aggregate; unique `(network_id,public_handle)`; one active self-profile per policy |
| `profile.profile_managers` | `profile_id`, `network_id`, `account_id`, `relationship_type`, `permission_json`, `consent_status`, `is_primary`, `invited_at`, `accepted_at`, `revoked_at` | Who may view/edit/publish/communicate; unique active `(profile_id,account_id)` |
| `profile.profile_brand_memberships` | `network_id`, `profile_id`, `brand_id`, `discoverable`, `joined_at`, `left_at` | Brand visibility without duplicating profile; unique active pair |
| `profile.profile_experience_selections` | `network_id`, `profile_id`, `experience_id`, `selected_by_account_id`, `selected_at`, `removed_at` | Explicit opt-in to experiences; never model-inferred |
| `profile.personal_details` | `profile_id`, `network_id`, `legal_name_ciphertext`, `display_name`, `birth_date`, `gender_code`, `pronouns`, `marital_history_code`, `height_cm`, `current_country_code`, `current_region_id`, `current_city`, `citizenship_codes`, `residency_status`, `relocation_preference`, `contact_visibility`, `version` | Restricted candidate facts; birth date never public; validate policy ranges |
| `profile.profile_narratives` | `profile_id`, `network_id`, `headline`, `short_bio`, `long_bio`, `expectations_text`, `family_bio`, `source`, `moderation_status`, `version` | User-approved narrative text; AI drafts stay separate until accepted |
| `profile.lifestyle_details` | `profile_id`, `network_id`, `diet_code`, `smoking_code`, `alcohol_code`, `fitness_code`, `values_json`, `future_plans_json`, `children_preference_code`, `version` | Explicit fields with “prefer not to say”; review before adding sensitive facts |
| `profile.profile_communities` | `profile_id`, `network_id`, `community_id`, `visibility`, `is_primary`, `self_declared_at` | Optional self-declaration; unique `(profile_id,community_id)` |
| `profile.profile_religious_practices` | `profile_id`, `network_id`, `practice_id`, `level_code`, `visibility`, `self_declared_at` | Optional self-declaration; unique `(profile_id,practice_id)` |
| `profile.profile_languages` | `profile_id`, `network_id`, `language_code`, `proficiency_code`, `is_primary` | Unique `(profile_id,language_code)` |
| `profile.profile_interests` | `profile_id`, `network_id`, `interest_id`, `note`, `visibility` | Unique `(profile_id,interest_id)` |
| `profile.education_records` | `id`, `network_id`, `profile_id`, `level_id`, `field_of_study`, `institution_name`, `country_code`, `start_year`, `end_year`, `is_current`, `verification_claim_id`, `sort_order` | Validate year ordering; public visibility controlled separately |
| `profile.employment_records` | `id`, `network_id`, `profile_id`, `occupation_category_id`, `title`, `employer_name`, `country_code`, `start_date`, `end_date`, `is_current`, `income_band_code`, `verification_claim_id`, `sort_order` | Exact income optional and not required; validate dates |
| `profile.family_profiles` | `id`, `network_id`, `profile_id`, `summary`, `values_json`, `home_country_code`, `home_region_id`, `visibility`, `version` | Family-level context without collecting unnecessary identities |
| `profile.family_members` | `id`, `network_id`, `family_profile_id`, `relationship_type`, `display_label`, `occupation_summary`, `location_summary`, `visibility`, `sort_order` | Minimal optional data; do not collect minor/contact details |
| `profile.match_preferences` | `profile_id`, `network_id`, `min_age`, `max_age`, `min_height_cm`, `max_height_cm`, `marital_history_codes`, `relocation_codes`, `children_preference_codes`, `diet_codes`, `smoking_codes`, `alcohol_codes`, `priority_json`, `version` | Owner-visible preference root; validate ranges and supported values |
| `profile.preference_countries` | `profile_id`, `network_id`, `country_code`, `preference_level` | Allowed/preferred/dealbreaker country; composite key |
| `profile.preference_languages` | `profile_id`, `network_id`, `language_code`, `minimum_proficiency`, `preference_level` | Composite key |
| `profile.preference_communities` | `profile_id`, `network_id`, `community_id`, `preference_level` | Never publicize hidden preference; composite key |
| `profile.preference_religious_practices` | `profile_id`, `network_id`, `practice_id`, `minimum_level_code`, `preference_level` | Composite key |
| `profile.preference_education_levels` | `profile_id`, `network_id`, `education_level_id`, `preference_level` | Composite key |
| `profile.profile_visibility` | `profile_id`, `network_id`, `discoverability`, `photo_policy`, `name_policy`, `location_precision`, `contact_policy`, `hide_from_account_ids_json`, `version` | Central user visibility settings; large block lists stay in `trust.blocks` |
| `profile.profile_completion` | `profile_id`, `network_id`, `score`, `missing_items_json`, `policy_version`, `calculated_at` | Deterministic current projection, not an LLM truth |
| `profile.profile_revisions` | `id`, `network_id`, `profile_id`, `profile_version`, `changed_by_account_id`, `change_type`, `changed_fields_json`, `reason`, `created_at` | Append-only material change trail without storing secret values |

`gender_code`, `marital_history_code`, lifestyle values, and visibility semantics remain provisional until decision items OQ-007/OQ-009 are resolved.

### 3.5 `media`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `media.upload_sessions` | `id`, `network_id`, `account_id`, `purpose`, `object_key`, `expected_content_type`, `max_bytes`, `checksum`, `expires_at`, `completed_at` | One-use presigned upload contract; object key generated server-side |
| `media.assets` | `id`, `network_id`, `owner_account_id`, `object_key`, `bucket_class`, `content_type`, `byte_size`, `checksum`, `status`, `scan_status`, `moderation_status`, `metadata_json`, `created_at`, `ready_at`, `quarantined_at` | Private object metadata; unique `(network_id,object_key)` |
| `media.asset_variants` | `id`, `network_id`, `asset_id`, `variant_type`, `object_key`, `width`, `height`, `content_type`, `byte_size` | Thumbnail/display variants; unique `(asset_id,variant_type)` |
| `media.profile_media` | `id`, `network_id`, `profile_id`, `asset_id`, `media_type`, `is_primary`, `visibility`, `sort_order`, `caption`, `status` | Profile association; partial unique primary photo per profile |
| `media.generated_documents` | `id`, `network_id`, `profile_id`, `document_type`, `template_version`, `asset_id`, `status`, `requested_by_account_id`, `generated_at`, `expires_at` | Biodata/export object references |

Raw verification documents are referenced from `verification.evidence_items` and use a more restrictive bucket prefix, KMS key, access role, and lifecycle.

### 3.6 `discovery`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `discovery.profile_search_documents` | `network_id`, `profile_id`, `profile_version`, `publication_status`, `age_bucket`, `birth_year_month`, `country_code`, `region_id`, `community_ids`, `practice_ids`, `language_codes`, `education_rank`, `occupation_ids`, `lifestyle_json`, `search_text`, `visibility_json`, `updated_at` | Denormalized, rebuildable search projection; primary key `(network_id,profile_id)` |
| `discovery.saved_searches` | `id`, `network_id`, `profile_id`, `name`, `filter_json`, `alert_frequency`, `is_active`, `last_run_at` | Owner-defined filters; validate against versioned search schema |
| `discovery.search_history` | `id`, `network_id`, `profile_id`, `query_kind`, `normalized_filter_json`, `result_count`, `created_at`, `expires_at` | Short-retention product signal; raw natural text omitted or separately consented |
| `discovery.profile_views` | `id`, `network_id`, `viewer_profile_id`, `viewed_profile_id`, `source`, `viewed_at`, `dedupe_bucket` | Unique dedupe key per configured window; obey private-view policy |
| `discovery.shortlist_entries` | `network_id`, `profile_id`, `target_profile_id`, `note_ciphertext`, `created_at` | Private shortlist; primary key pair; cannot target blocked profile |
| `discovery.hidden_profiles` | `network_id`, `profile_id`, `target_profile_id`, `reason_code`, `created_at`, `expires_at` | Private discovery suppression; distinct from safety block |
| `discovery.recommendation_runs` | `id`, `network_id`, `profile_id`, `algorithm_version`, `input_version`, `status`, `started_at`, `completed_at` | Phase 2 reproducibility record |
| `discovery.recommendation_items` | `run_id`, `network_id`, `target_profile_id`, `rank`, `score`, `reason_codes_json` | Phase 2 ranked projection; unique `(run_id,target_profile_id)` |

The search projection exposes only facts allowed for discovery. It never contains legal names, exact birth dates, contacts, document data, hidden preferences, or private family-member identities.

### 3.7 `matchmaking`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `matchmaking.compatibility_policies` | `id`, `network_id`, `version`, `status`, `factor_config_json`, `explanation_policy_json`, `activated_at` | Immutable versioned scoring configuration |
| `matchmaking.compatibility_scores` | `id`, `network_id`, `profile_a_id`, `profile_b_id`, `profile_a_version`, `profile_b_version`, `policy_id`, `score`, `confidence`, `status`, `calculated_at`, `expires_at` | Canonical ordered pair; unique inputs/policy; score bounded 0–100 |
| `matchmaking.compatibility_factors` | `id`, `network_id`, `compatibility_score_id`, `factor_key`, `raw_value`, `weighted_value`, `reason_code`, `evidence_refs_json`, `visibility` | Deterministic explainability; never expose another profile's hidden preference |
| `matchmaking.interests` | `id`, `network_id`, `sender_profile_id`, `recipient_profile_id`, `sequence`, `status`, `intro_message_id`, `sent_by_account_id`, `sent_at`, `responded_by_account_id`, `responded_at`, `expires_at`, `version` | No self-interest; partial unique pending pair; state-machine checks |
| `matchmaking.matches` | `id`, `network_id`, `profile_low_id`, `profile_high_id`, `source_interest_id`, `status`, `matched_at`, `ended_at`, `ended_by_profile_id`, `end_reason`, `version` | Canonically ordered pair; one active match per pair |
| `matchmaking.match_feedback` | `id`, `network_id`, `match_id`, `profile_id`, `feedback_type`, `reason_codes_json`, `comment_ciphertext`, `created_at` | Private ranking/product feedback; one active response/type policy |
| `matchmaking.outcome_reports` | `id`, `network_id`, `match_id`, `reported_by_profile_id`, `outcome_type`, `occurred_on`, `consent_to_story`, `notes_ciphertext`, `verification_status`, `created_at` | Optional success/outcome learning with explicit consent |

Compatibility is directional where preferences differ. The stored canonical score may contain directional factor views or two score records; the policy implementation must document which approach it uses before task MAT-001.

### 3.8 `chat`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `chat.conversations` | `id`, `network_id`, `match_id`, `type`, `status`, `created_at`, `last_message_at`, `version` | One active match conversation unless policy enables additional rooms |
| `chat.conversation_profiles` | `conversation_id`, `network_id`, `profile_id`, `joined_at`, `left_at` | Candidate-side membership; unique active pair |
| `chat.conversation_participants` | `conversation_id`, `network_id`, `account_id`, `acting_for_profile_id`, `role`, `joined_at`, `left_at`, `last_read_message_id`, `muted_until` | Access derives from current profile-manager permissions; no implicit admin access |
| `chat.messages` | `id`, `network_id`, `conversation_id`, `sender_account_id`, `sender_profile_id`, `client_message_id`, `message_type`, `body_ciphertext`, `body_format`, `moderation_status`, `delivery_status`, `reply_to_message_id`, `sent_at`, `edited_at`, `deleted_at` | Unique `(conversation_id,sender_account_id,client_message_id)` for retries; body application-encrypted |
| `chat.message_revisions` | `id`, `network_id`, `message_id`, `revision_number`, `body_ciphertext`, `edited_by_account_id`, `edited_at`, `reason` | Policy-dependent encrypted edit history; unique message/revision |
| `chat.message_attachments` | `message_id`, `network_id`, `asset_id`, `attachment_type`, `sort_order` | Only `ready` scanned assets; composite key |
| `chat.message_receipts` | `network_id`, `message_id`, `account_id`, `delivered_at`, `read_at` | Unique message/account receipt |
| `chat.message_policy_results` | `id`, `network_id`, `message_id`, `policy_version`, `decision`, `reason_codes_json`, `provider_ref`, `evaluated_at` | Safety result without duplicating message body |

Presence, typing indicators, and transient connection maps live in Redis with short TTLs. They are not authoritative records.

### 3.9 `trust`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `trust.blocks` | `id`, `network_id`, `blocking_profile_id`, `blocked_profile_id`, `created_by_account_id`, `reason_code`, `created_at`, `revoked_at` | Immediately suppresses discovery/contact both directions; unique active pair |
| `trust.reports` | `id`, `network_id`, `reporter_profile_id`, `subject_type`, `subject_id`, `category`, `description_ciphertext`, `status`, `priority`, `created_at`, `resolved_at` | Report intake; reporter identity restricted |
| `trust.report_evidence` | `id`, `network_id`, `report_id`, `asset_id`, `message_id`, `evidence_type`, `created_at` | Authorized references only; no copying raw content into report rows |
| `trust.moderation_cases` | `id`, `network_id`, `case_type`, `subject_type`, `subject_id`, `source`, `priority`, `status`, `assigned_to_account_id`, `sla_due_at`, `created_at`, `closed_at` | Human review work item; one case may group reports/signals |
| `trust.case_links` | `case_id`, `network_id`, `linked_type`, `linked_id` | Connects reports, signals, verification, messages, payments |
| `trust.moderation_actions` | `id`, `network_id`, `case_id`, `action_type`, `subject_type`, `subject_id`, `reason_code`, `policy_version`, `effective_at`, `expires_at`, `performed_by_account_id` | Append-only action record; domain module enforces action |
| `trust.sanctions` | `id`, `network_id`, `subject_type`, `subject_id`, `sanction_type`, `status`, `source_action_id`, `starts_at`, `ends_at`, `revoked_at` | Current enforceable restriction projection |
| `trust.appeals` | `id`, `network_id`, `action_id`, `appellant_account_id`, `reason_ciphertext`, `status`, `reviewed_by_account_id`, `created_at`, `decided_at` | Separate reviewer where feasible; complete audit |
| `trust.risk_signals` | `id`, `network_id`, `subject_type`, `subject_id`, `signal_type`, `severity`, `confidence`, `source`, `model_version`, `evidence_refs_json`, `status`, `detected_at`, `expires_at` | Signals are not sanctions; minimize evidence and expire stale signals |
| `trust.trust_score_snapshots` | `id`, `network_id`, `profile_id`, `score`, `band`, `policy_version`, `factor_summary_json`, `calculated_at` | Internal/public views differ; based on explainable checks/signals |

### 3.10 `verification`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `verification.check_types` | `id`, `network_id`, `key`, `display_name`, `provider_key`, `country_codes`, `policy_json`, `status` | Configures identity/education/employment/etc. checks |
| `verification.requests` | `id`, `network_id`, `profile_id`, `check_type_id`, `status`, `provider`, `provider_reference`, `requested_by_account_id`, `submitted_at`, `completed_at`, `expires_at`, `failure_code` | One current request/check/profile policy; provider reference unique |
| `verification.evidence_items` | `id`, `network_id`, `request_id`, `asset_id`, `evidence_type`, `retention_until`, `review_status`, `created_at`, `purged_at` | Highly restricted objects with dedicated lifecycle |
| `verification.claims` | `id`, `network_id`, `profile_id`, `claim_type`, `claim_value_hash`, `status`, `source_request_id`, `verified_at`, `expires_at`, `revoked_at`, `public_label` | Public UI exposes only approved label/status/date |
| `verification.provider_events` | `id`, `network_id`, `provider`, `external_event_id`, `signature_valid`, `payload_ciphertext`, `received_at`, `processed_at`, `status` | Unique provider/event; encrypted short-retention payload |
| `verification.review_decisions` | `id`, `network_id`, `request_id`, `reviewer_account_id`, `decision`, `reason_code`, `notes_ciphertext`, `created_at` | Append-only manual review evidence |

### 3.11 `ai`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `ai.capability_configs` | `id`, `network_id`, `capability_key`, `enabled`, `mode`, `timeout_ms`, `max_attempts`, `budget_json`, `active_route_id`, `version` | Kill switch, limits, provider route; unique capability/network |
| `ai.model_routes` | `id`, `network_id`, `key`, `provider`, `model_alias`, `region`, `parameters_json`, `fallback_route_id`, `status` | No secret values; model alias decouples code from provider IDs |
| `ai.prompt_templates` | `id`, `network_id`, `capability_key`, `key`, `description`, `status` | Stable logical prompt identity |
| `ai.prompt_versions` | `id`, `template_id`, `version`, `system_template`, `user_template`, `input_schema_json`, `output_schema_json`, `safety_policy_version`, `checksum`, `created_by_account_id`, `activated_at`, `retired_at` | Immutable and reviewable; unique template/version |
| `ai.jobs` | `id`, `network_id`, `operation_id`, `capability_key`, `subject_type`, `subject_id`, `subject_version`, `status`, `priority`, `route_id`, `prompt_version_id`, `attempt_count`, `requested_by_account_id`, `queued_at`, `started_at`, `completed_at`, `error_code` | One durable AI unit; dedupe active subject/version/capability where applicable |
| `ai.request_records` | `id`, `network_id`, `job_id`, `provider_request_id`, `input_fingerprint`, `redaction_summary_json`, `token_count_in`, `token_count_out`, `latency_ms`, `cost_micros`, `status`, `created_at` | Operational metadata; prompts/responses not stored by default |
| `ai.artifacts` | `id`, `network_id`, `job_id`, `artifact_type`, `subject_type`, `subject_id`, `subject_version`, `content_json`, `grounding_refs_json`, `quality_status`, `user_status`, `created_at`, `accepted_at`, `rejected_at`, `expires_at` | Structured output; stale version cannot become current |
| `ai.feedback` | `id`, `network_id`, `artifact_id`, `account_id`, `rating`, `reason_codes_json`, `comment_ciphertext`, `created_at` | User quality signal with consent/retention |
| `ai.evaluation_cases` | `id`, `capability_key`, `dataset_version`, `input_json`, `expected_properties_json`, `safety_tags`, `status` | Synthetic/consented de-identified cases only |
| `ai.evaluation_runs` | `id`, `capability_key`, `route_id`, `prompt_version_id`, `dataset_version`, `code_version`, `status`, `started_at`, `completed_at`, `summary_json` | Reproducible release gate |
| `ai.evaluation_results` | `run_id`, `case_id`, `status`, `score_json`, `failure_codes_json`, `latency_ms`, `cost_micros` | Composite primary key; detailed eval result |

Profile extraction/bio/search/chat outputs are artifacts until the user explicitly applies or sends them. Compatibility explanations reference deterministic `matchmaking.compatibility_scores` and source factor IDs.

### 3.12 `notification`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `notification.preferences` | `network_id`, `account_id`, `category`, `channel`, `enabled`, `frequency`, `quiet_hours_json`, `consent_record_id`, `updated_at` | Composite key; transactional categories cannot be disabled if legally required |
| `notification.templates` | `id`, `network_id`, `brand_id`, `key`, `channel`, `locale`, `version`, `subject_template`, `body_template`, `allowed_variables_json`, `status` | Reviewed/versioned; no arbitrary template evaluation |
| `notification.notifications` | `id`, `network_id`, `account_id`, `category`, `event_type`, `subject_type`, `subject_id`, `title`, `body_preview`, `action_json`, `created_at`, `read_at`, `expires_at`, `dedupe_key` | In-app source; unique dedupe key where present |
| `notification.deliveries` | `id`, `network_id`, `notification_id`, `channel`, `destination_ref`, `template_id`, `status`, `attempt_count`, `provider_message_id`, `scheduled_at`, `sent_at`, `delivered_at`, `failed_at`, `failure_code` | Never store raw destination; unique provider reference |
| `notification.push_endpoints` | `id`, `network_id`, `account_id`, `platform`, `token_ciphertext`, `token_hash`, `status`, `last_used_at` | Future web/native push endpoint; unique token hash |

### 3.13 `billing`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `billing.plans` | `id`, `network_id`, `key`, `name`, `description`, `status`, `sort_order` | Logical product plan; unique key/network |
| `billing.prices` | `id`, `network_id`, `plan_id`, `provider`, `provider_price_ref`, `country_code`, `currency`, `amount_minor`, `billing_interval`, `tax_behavior`, `status` | Unique provider price ref; immutable active price amount |
| `billing.entitlement_definitions` | `id`, `network_id`, `key`, `description`, `value_type`, `default_value_json` | Capability/quota catalog |
| `billing.plan_entitlements` | `plan_id`, `entitlement_id`, `value_json` | Composite primary key |
| `billing.customer_refs` | `id`, `network_id`, `account_id`, `provider`, `provider_customer_ref`, `created_at` | Unique account/provider and provider ref; no card details |
| `billing.subscriptions` | `id`, `network_id`, `account_id`, `profile_id`, `plan_id`, `price_id`, `provider`, `provider_subscription_ref`, `status`, `current_period_start`, `current_period_end`, `cancel_at_period_end`, `canceled_at`, `version` | Provider state normalized; unique provider subscription ref |
| `billing.transactions` | `id`, `network_id`, `account_id`, `subscription_id`, `provider`, `provider_transaction_ref`, `type`, `status`, `amount_minor`, `currency`, `occurred_at`, `failure_code` | Append-oriented charges/refunds; unique provider transaction ref |
| `billing.webhook_events` | `id`, `network_id`, `provider`, `external_event_id`, `signature_valid`, `payload_ciphertext`, `received_at`, `processed_at`, `status`, `failure_code` | Unique provider/event; capture then process idempotently |
| `billing.entitlement_grants` | `id`, `network_id`, `account_id`, `profile_id`, `entitlement_id`, `source_type`, `source_id`, `value_json`, `starts_at`, `ends_at`, `revoked_at` | Materialized effective grant with source traceability |
| `billing.promo_codes` | `id`, `network_id`, `code_hash`, `display_code_masked`, `discount_json`, `starts_at`, `ends_at`, `max_redemptions`, `status` | Optional after core billing; never expose unrestricted admin listing |
| `billing.promo_redemptions` | `id`, `network_id`, `promo_code_id`, `account_id`, `transaction_id`, `redeemed_at` | Enforces per-account/global limits |

### 3.14 `analytics` and `audit`

| Table | Required columns and keys | Purpose / constraints |
|---|---|---|
| `analytics.product_events` | `id`, `network_id`, `event_name`, `anonymous_or_account_key`, `profile_key`, `properties_json`, `occurred_at`, `consent_class`, `expires_at` | Minimized analytics event; avoid message/profile text and direct contact data |
| `analytics.daily_metrics` | `network_id`, `metric_date`, `metric_key`, `dimension_json`, `value_numeric`, `calculated_at` | Aggregate projection; unique metric/date/dimension hash |
| `analytics.experiment_assignments` | `id`, `network_id`, `experiment_key`, `subject_key`, `variant`, `assigned_at`, `expires_at` | Only approved low-risk experiments; no discriminatory targeting |
| `audit.audit_entries` | `id`, `network_id`, `actor_type`, `actor_id`, `action`, `subject_type`, `subject_id`, `request_id`, `reason`, `metadata_json`, `occurred_at`, `integrity_hash` | Append-only security/admin audit; no secrets/raw private content |
| `audit.support_tickets` | `id`, `network_id`, `account_id`, `category`, `subject`, `status`, `priority`, `assigned_to_account_id`, `created_at`, `closed_at` | Support workflow |
| `audit.support_comments` | `id`, `network_id`, `ticket_id`, `author_account_id`, `visibility`, `body_ciphertext`, `created_at` | Encrypted; internal comments never exposed to user |
| `audit.data_subject_requests` | `id`, `network_id`, `account_id`, `request_type`, `status`, `identity_verified_at`, `due_at`, `requested_at`, `completed_at`, `result_asset_id`, `failure_code` | Export/correction/deletion request evidence |
| `audit.legal_holds` | `id`, `network_id`, `subject_type`, `subject_id`, `reason_ciphertext`, `starts_at`, `ends_at`, `created_by_account_id` | Restricted legal process; blocks conflicting purges |

## 4. Relationship rules

- Account and profile are separate. An account can manage allowed profiles; a profile can have multiple authorized managers.
- `candidate_account_id` is set when the represented candidate has an account. Publication requires approved consent state.
- Every foreign key that points to network-owned data must be validated as same-network. Use composite unique keys `(network_id,id)` and composite foreign keys where Prisma/custom SQL permits.
- Brand membership controls presentation/discoverability; it does not duplicate user data.
- A safety block overrides discovery, interests, matches, chat, notifications, and AI recommendations.
- Accepting an interest creates exactly one active match and authorized conversation in one transaction.
- Verification claims reference their source request; public profiles never join raw evidence.
- AI artifacts target a subject version. Only a non-stale, policy-passing, accepted artifact can update authoritative narrative/search state.
- Entitlements are checked by the billing module; modules do not infer them directly from subscription status.

## 5. Critical indexes

Create only after validating representative query plans, but plan for:

- `core.outbox_events (available_at, occurred_at) WHERE published_at IS NULL`.
- `core.scheduled_jobs (run_at) WHERE status = 'pending'`.
- `identity.account_contacts (network_id, kind, value_hash)` unique.
- `identity.sessions (account_id, expires_at) WHERE revoked_at IS NULL`.
- `profile.profiles (network_id, publication_status, published_at DESC)`.
- All profile child tables by `(network_id,profile_id)`.
- `discovery.profile_search_documents` B-tree indexes for common hard filters; GIN for arrays/JSONB and search vector; trigram only on approved public text.
- Keyset search order `(network_id, publication_status, updated_at DESC, profile_id DESC)` or ranking-specific equivalent.
- `discovery.profile_views (viewer_profile_id, viewed_at DESC)`.
- `matchmaking.interests (recipient_profile_id,status,sent_at DESC)` and `(sender_profile_id,status,sent_at DESC)`.
- Canonical pair indexes on compatibility and matches.
- `chat.messages (conversation_id,sent_at DESC,id DESC)` and unique client retry key.
- `chat.message_receipts (account_id,read_at)` where unread projection requires it.
- Active blocks both directions.
- Open moderation cases by `(network_id,status,priority,sla_due_at)`.
- AI jobs by `(capability_key,status,queued_at)` and subject/version.
- Notification deliveries by `(status,scheduled_at)`.
- Billing external references unique.
- Audit by `(network_id,subject_type,subject_id,occurred_at DESC)` with time partitioning only when volume warrants it.

Every list uses cursor/keyset pagination. Avoid deep `OFFSET` on messages, profiles, events, and audit records.

## 6. Concurrency and transaction boundaries

- Use expected `version` for profile, interest, match, subscription, and mutable config updates.
- Use a canonical ordered profile pair to avoid duplicate scores/matches.
- Interest acceptance transaction: lock/compare pending interest, set accepted, create match, participants/conversation, outbox events.
- Message send transaction: validate access/block state, insert idempotent message, update conversation pointer, write event.
- Outbox dispatcher uses `FOR UPDATE SKIP LOCKED`, short leases, bounded batches, and marks published only after broker acknowledgement.
- Inbox processing records the event before side effects in the same transaction where possible.
- Billing/verification webhooks first persist verified envelope uniquely, then process asynchronously.

## 7. Retention baseline

Final periods require legal approval and launch-country review.

| Data | Working baseline |
|---|---|
| Auth challenges | Purge shortly after expiry, normally within 24 hours |
| Revoked/expired sessions | 30–90 days for security investigation, then purge/hash-only aggregate |
| Raw verification evidence | Minimum provider/legal period; target purge within 30 days after completed check when allowed |
| Provider webhook payload | Encrypted, short retention after reconciliation; retain normalized transaction/claim |
| AI prompts/responses | Do not store raw by default; retain fingerprints, route, metrics, structured approved artifact |
| Search history | 30–90 days, user-controllable where required |
| Media quarantined/rejected | Purge after appeal window |
| Chat | Product/legal policy required before launch; deletion and legal-hold behavior must be explicit |
| Audit/security events | 1 year working baseline, longer only when justified |
| Payment transaction records | Required statutory/accounting period |
| Data exports | Short-lived signed object, target 7 days |
| Deleted account/profile | Immediate access revocation; queued purge/anonymization subject to fraud, billing, safety, and legal holds |

S3 lifecycle rules and database purge jobs must correspond to the same policy and emit audit evidence.

## 8. Migration and seed rules

1. Migrations are immutable after shared deployment.
2. Use expand/migrate/contract changes for zero-downtime schema evolution.
3. A deployment runs migrations as a one-off task before new containers receive traffic; destructive contraction occurs in a later release.
4. CI creates an empty database, applies all migrations, validates schema, then tests upgrade from the latest production-like snapshot.
5. Seed only reference/config/synthetic demo data. Never seed real profiles, contacts, documents, or conversations.
6. Backup before high-risk production migration and prove rollback/forward-fix behavior in staging.
7. Generated Prisma schema and reviewed SQL must agree; advanced constraints/indexes have migration tests.
8. Before adding a second isolated network, enable and test PostgreSQL row-level-security policies or an equivalent independently reviewed defense-in-depth layer.

## 9. Data-model release gate

The initial schema is ready when:

- every MVP use case maps to an owning aggregate/table;
- same-network constraints and authorization tests prevent cross-network access;
- query plans meet search/chat/list targets on a synthetic dataset larger than the first-year estimate;
- migration from empty and previous baseline succeeds;
- backup/restore preserves referential integrity;
- privacy review confirms fields, visibility, retention, encryption, and export/deletion mappings;
- no table stores raw card data, object bytes, plaintext contacts, secrets, or unnecessary AI payloads.
