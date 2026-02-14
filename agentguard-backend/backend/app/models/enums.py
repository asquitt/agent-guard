"""Enum definitions for AgentGuard models."""

import enum


class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    SECURITY_ANALYST = "security_analyst"
    COMPLIANCE_OFFICER = "compliance_officer"
    DEVELOPER = "developer"
    MEMBER = "member"
    VIEWER = "viewer"


class Permission(str, enum.Enum):
    # Incidents
    INCIDENTS_READ = "incidents:read"
    INCIDENTS_WRITE = "incidents:write"
    # Detectors
    DETECTORS_READ = "detectors:read"
    DETECTORS_WRITE = "detectors:write"
    # Agents
    AGENTS_READ = "agents:read"
    AGENTS_WRITE = "agents:write"
    # Compliance
    COMPLIANCE_READ = "compliance:read"
    COMPLIANCE_WRITE = "compliance:write"
    # Alerts
    ALERTS_READ = "alerts:read"
    ALERTS_WRITE = "alerts:write"
    # API Keys
    API_KEYS_READ = "api_keys:read"
    API_KEYS_WRITE = "api_keys:write"
    # Settings / Org
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"
    # Billing
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    # Proxy endpoints
    PROXY_WRITE = "proxy:write"
    # Sandboxes
    SANDBOXES_READ = "sandboxes:read"
    SANDBOXES_WRITE = "sandboxes:write"


# Role → permissions mapping
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    UserRole.OWNER.value: frozenset(p.value for p in Permission),
    UserRole.ADMIN.value: frozenset(p.value for p in Permission),
    UserRole.SECURITY_ANALYST.value: frozenset([
        Permission.INCIDENTS_READ.value, Permission.INCIDENTS_WRITE.value,
        Permission.DETECTORS_READ.value, Permission.DETECTORS_WRITE.value,
        Permission.AGENTS_READ.value,
        Permission.COMPLIANCE_READ.value,
        Permission.ALERTS_READ.value, Permission.ALERTS_WRITE.value,
        Permission.SANDBOXES_READ.value, Permission.SANDBOXES_WRITE.value,
    ]),
    UserRole.COMPLIANCE_OFFICER.value: frozenset([
        Permission.INCIDENTS_READ.value,
        Permission.DETECTORS_READ.value,
        Permission.AGENTS_READ.value,
        Permission.COMPLIANCE_READ.value, Permission.COMPLIANCE_WRITE.value,
        Permission.ALERTS_READ.value,
        Permission.SETTINGS_READ.value,
    ]),
    UserRole.DEVELOPER.value: frozenset([
        Permission.INCIDENTS_READ.value,
        Permission.DETECTORS_READ.value, Permission.DETECTORS_WRITE.value,
        Permission.AGENTS_READ.value, Permission.AGENTS_WRITE.value,
        Permission.API_KEYS_READ.value, Permission.API_KEYS_WRITE.value,
        Permission.PROXY_WRITE.value,
        Permission.SANDBOXES_READ.value, Permission.SANDBOXES_WRITE.value,
    ]),
    UserRole.MEMBER.value: frozenset([
        Permission.INCIDENTS_READ.value, Permission.INCIDENTS_WRITE.value,
        Permission.DETECTORS_READ.value,
        Permission.AGENTS_READ.value,
        Permission.COMPLIANCE_READ.value,
        Permission.ALERTS_READ.value,
        Permission.API_KEYS_READ.value,
    ]),
    UserRole.VIEWER.value: frozenset([
        Permission.INCIDENTS_READ.value,
        Permission.DETECTORS_READ.value,
        Permission.AGENTS_READ.value,
        Permission.COMPLIANCE_READ.value,
        Permission.ALERTS_READ.value,
    ]),
}


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
    TOOL_CALL = "tool_call"
    MCP_SECURITY = "mcp_security"
    SCHEMA_INJECTION = "schema_injection"
    SEQUENTIAL_ACTION = "sequential_action"
    SCOPE_ENFORCEMENT = "scope_enforcement"
    SYCOPHANCY = "sycophancy"
    MEMORY_EXFILTRATION = "memory_exfiltration"
    CONFIDENCE_HALLUCINATION = "confidence_hallucination"


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


class AgentRiskTier(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentStatus(str, enum.Enum):
    DRAFT = "draft"
    TESTING = "testing"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"


class Environment(str, enum.Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"


class SandboxStatus(str, enum.Enum):
    PENDING = "pending"
    PROVISIONING = "provisioning"
    RUNNING = "running"
    PAUSED = "paused"
    TERMINATED = "terminated"
    FAILED = "failed"


class CapabilityType(str, enum.Enum):
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    NETWORK_HTTP = "network:http"
    NETWORK_DNS = "network:dns"
    API_CALL = "api:call"
    TOOL_EXECUTE = "tool:execute"
    SECRET_ACCESS = "secret:access"


class SandboxActionType(str, enum.Enum):
    API_CALL = "api_call"
    FILE_ACCESS = "file_access"
    NETWORK_REQUEST = "network_request"
    TOOL_INVOCATION = "tool_invocation"
    RESOURCE_EXCEEDED = "resource_exceeded"
    CAPABILITY_DENIED = "capability_denied"
    SANDBOX_LIFECYCLE = "sandbox_lifecycle"
