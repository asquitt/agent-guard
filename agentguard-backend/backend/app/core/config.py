"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "AgentGuard"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://agentguard:agentguard@localhost:5432/agentguard"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_KEY: str = ""  # 64-char hex string (32 bytes) for AES-256-GCM field encryption

    # Authentication hardening
    MAX_FAILED_LOGIN_ATTEMPTS: int = 10
    ACCOUNT_LOCKOUT_MINUTES: int = 30
    PASSWORD_MIN_LENGTH: int = 12

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    ALLOWED_HEADERS: List[str] = [
        "Authorization",
        "Content-Type",
        "X-AgentGuard-Endpoint-Id",
        "X-Request-ID",
    ]

    # LLM Providers (customer traffic proxy)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Internal LLM for detection (hallucination & compliance checks)
    DETECTION_LLM_PROVIDER: str = "openai"  # "openai" or "anthropic"
    DETECTION_LLM_MODEL: str = "gpt-4o-mini"
    DETECTION_LLM_RPM: int = 60  # rate limit: requests per minute

    # Alerting
    SLACK_WEBHOOK_URL: str = ""
    PAGERDUTY_API_KEY: str = ""

    # Stripe Billing
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_STARTER_PRICE_ID: str = ""
    STRIPE_PRO_PRICE_ID: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    # SSO
    SSO_SP_ENTITY_ID_BASE: str = ""  # e.g. https://agentguard.app/saml/sp
    SSO_ACS_URL_BASE: str = ""  # e.g. https://agentguard.app/api/v1/auth/saml/acs
    SSO_OIDC_REDIRECT_URI_BASE: str = ""  # e.g. https://agentguard.app/api/v1/auth/oidc/callback

    # Data Retention
    ARCHIVE_STORAGE_PATH: str = "/app/archives"
    RETENTION_BATCH_SIZE: int = 500
    RETENTION_DRY_RUN: bool = False

    # Sentry
    SENTRY_DSN: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
