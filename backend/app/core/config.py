"""Typed application settings with a two-layer source model.

Configuration comes from two places, by design:

1. ``config.yaml`` (committed to git) — non-secret, structural configuration:
   model names, timeouts, bucket/table names, feature toggles, limits, batch
   cadences, and third-party *endpoints*. NEVER put secrets here.
2. Environment variables / ``.env`` (never committed) — secrets (API keys,
   credentials) and per-environment overrides.

Precedence (highest first): init args > environment variables > ``.env`` >
``config.yaml`` > field defaults. So any value in ``config.yaml`` can be
overridden at deploy time by an environment variable without a code change.

Nested values use the ``__`` delimiter, e.g. ``LAARA_AI__PROVIDER=openai``
overrides ``ai.provider`` from the YAML file.

Select an alternate YAML file with ``LAARA_CONFIG_FILE`` (defaults to
``config.yaml`` resolved from the current working directory / Lambda task root).
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

_CONFIG_FILE = os.getenv("LAARA_CONFIG_FILE", "config.yaml")


class AIConfig(BaseModel):
    """Non-secret AI configuration. API keys are NOT here (see secrets below)."""

    provider: Literal["fake", "openai", "bedrock"] = "fake"
    # Native embedding model preferred; falls back to a cheap GPT model when the
    # native provider/model is unavailable.
    embedding_model: str = "amazon.titan-embed-text-v2:0"
    embedding_fallback_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1024
    chat_model: str = "anthropic.claude-3-5-haiku"
    # Practical synchronous budget below the API Gateway 29s hard limit.
    request_timeout_seconds: int = 20
    # Base URL for an OpenAI-compatible endpoint used in local development.
    openai_base_url: str | None = None
    # Chat model used specifically when provider == "openai" (the Bedrock
    # `chat_model` above is not a valid OpenAI model id).
    openai_chat_model: str = "gpt-4o-mini"
    # Content-moderation channel is independent of the generation `provider`
    # so moderation can run on OpenAI's omni-moderation model even while
    # generation stays on the free `fake` provider (per product decision).
    moderation_provider: Literal["fake", "openai"] = "fake"
    # Block synchronously (422) when the highest flagged category score is at
    # or above this threshold; otherwise a flag is logged but not enforced.
    moderation_block_threshold: float = 0.5


class StorageConfig(BaseModel):
    dynamodb_table_name: str = "laarilaara-local"
    dynamodb_endpoint_url: str | None = None  # e.g. http://localhost:8000 local
    s3_endpoint_url: str | None = None
    media_bucket_name: str = "laarilaara-local-media"
    artifacts_bucket_name: str = "laarilaara-local-artifacts"
    embeddings_bucket_name: str = "laarilaara-local-embeddings"


class LimitsConfig(BaseModel):
    default_page_size: int = 20
    max_page_size: int = 100
    # Coarse per-account write budget enforced by the Dynamo-backed limiter.
    auth_challenges_per_hour: int = 10
    ai_jobs_per_day: int = 50


class RecommendationsConfig(BaseModel):
    # Daily batch cadence for the pairwise recommendation rebuild.
    rebuild_cron: str = "cron(0 3 * * ? *)"
    candidates_per_profile: int = 100


class AuthConfig(BaseModel):
    """Structural (non-secret) auth settings. The signing secret is not here."""

    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    max_challenge_attempts: int = 5
    challenge_ttl_minutes: int = 15


_INSECURE_DEFAULT_JWT_SECRET = "insecure-local-dev-secret-change-me"
_INSECURE_DEFAULT_WEBHOOK_SECRET = "insecure-local-dev-webhook-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LAARA_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file=_CONFIG_FILE,
        yaml_file_encoding="utf-8",
        extra="ignore",
    )

    # Runtime (typically overridden per environment via env vars)
    environment: Literal["local", "development", "staging", "production"] = "local"
    service_name: str = "laarilaara-api"
    api_version: str = "v1"
    log_level: str = "INFO"
    aws_region: str = "us-east-1"

    # When true, readiness probes actually call dependencies; off by default so
    # local dev and unit tests do not require AWS to be reachable.
    check_dependencies_on_ready: bool = False

    # Browser origins allowed to call the API (the Next.js frontend). Override
    # per environment (e.g. the CloudFront/custom domain in production).
    cors_allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Structural config groups (populated from config.yaml, overridable by env)
    ai: AIConfig = AIConfig()
    storage: StorageConfig = StorageConfig()
    limits: LimitsConfig = LimitsConfig()
    recommendations: RecommendationsConfig = RecommendationsConfig()
    auth: AuthConfig = AuthConfig()

    # Secrets: environment-only. Never add these to config.yaml.
    openai_api_key: str | None = None
    jwt_secret: str = _INSECURE_DEFAULT_JWT_SECRET
    # Single shared HMAC secret for all §14 webhook providers. A real deployment
    # would hold one secret per provider (from that provider's dashboard) in
    # Secrets Manager — deferred until a real provider is actually wired up;
    # documented simplification, same class as the entitlements/AI seams.
    webhook_signing_secret: str = _INSECURE_DEFAULT_WEBHOOK_SECRET

    @model_validator(mode="after")
    def _require_real_jwt_secret_outside_local(self) -> "Settings":
        if (
            self.environment in ("staging", "production")
            and self.jwt_secret == _INSECURE_DEFAULT_JWT_SECRET
        ):
            raise ValueError(
                "LAARA_JWT_SECRET must be set to a real secret outside local/development"
            )
        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Earlier sources win. Env/.env override config.yaml.
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
