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
    ENVIRONMENT: str = "development"  # development, staging, production
    GIT_COMMIT_SHA: str = ""  # populated by CI/CD or docker-compose

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

    # Database connection pooling
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # 30 minutes

    # Authentication hardening
    MAX_FAILED_LOGIN_ATTEMPTS: int = 10
    ACCOUNT_LOCKOUT_MINUTES: int = 30
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15

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
    GOOGLE_GEMINI_API_KEY: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""  # e.g. https://<resource>.openai.azure.com
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"

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

    # Rate Limiting (per-org sliding window, 0 = disabled)
    RATE_LIMIT_RPM: int = 120  # requests per minute
    RATE_LIMIT_RPH: int = 5000  # requests per hour
    RATE_LIMIT_RPD: int = 100000  # requests per day

    # Proxy HA / Degraded Mode
    SYNC_DETECTION_TIMEOUT_MS: int = 500  # max time for sync detectors before fallback to async
    DEGRADED_MODE_ENABLED: bool = True  # enable automatic degraded mode on detection timeout

    # Sentry
    SENTRY_DSN: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    s = Settings()
    # Block startup with insecure defaults in production
    if not s.DEBUG:
        if s.SECRET_KEY == "dev-secret-key-change-in-production":
            raise RuntimeError(
                "FATAL: SECRET_KEY is set to the default dev value. "
                "Set a strong, unique SECRET_KEY environment variable for production."
            )
        if not s.ENCRYPTION_KEY:
            raise RuntimeError(
                "FATAL: ENCRYPTION_KEY is empty. "
                "Set a 64-char hex string (32 bytes) for AES-256-GCM field encryption."
            )
    return s


settings = get_settings()
