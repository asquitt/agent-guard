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

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

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
