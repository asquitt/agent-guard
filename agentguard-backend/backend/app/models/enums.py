"""Enum definitions for AgentGuard models."""

import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class PlanTier(str, enum.Enum):
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Provider(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE_GEMINI = "google_gemini"
    AZURE_OPENAI = "azure_openai"
    BEDROCK = "bedrock"
    CUSTOM = "custom"


class IncidentSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class DetectorCategory(str, enum.Enum):
    HALLUCINATION = "hallucination"
    PII_LEAK = "pii_leak"
    COMPLIANCE = "compliance"
    COST_ANOMALY = "cost_anomaly"
    LOOP = "loop"
    PROMPT_INJECTION = "prompt_injection"
    PROMPT_EXTRACTION = "prompt_extraction"
    TOXICITY = "toxicity"


class ActionMode(str, enum.Enum):
    MONITOR = "monitor"
    WARN = "warn"
    REDACT = "redact"
    BLOCK = "block"


class AlertDestinationType(str, enum.Enum):
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    EMAIL = "email"
    WEBHOOK = "webhook"


class AlertStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
