"""SQLAlchemy models for AgentGuard.

CRITICAL: All models with __tablename__ MUST be imported here.
Alembic uses these imports to detect models for migrations.
Missing imports will cause tables to be marked for DROP.

Run `python scripts/check_model_imports.py` after any model changes.
"""

from app.models.agent import Agent
from app.models.agent_policy import AgentPolicy
from app.models.alert import Alert, AlertDestination
from app.models.audit import AuditLog
from app.models.compliance_report import ComplianceReport
from app.models.conversation import Conversation, ConversationTurn
from app.models.data_archive import DataArchive
from app.models.detector import Detector, DetectorRule
from app.models.incident import Incident, IncidentAction
from app.models.proxy import ProxyEndpoint, ProxyRequest
from app.models.red_team import RedTeamFinding, RedTeamRun
from app.models.retention_policy import RetentionPolicy
from app.models.review_queue import ReviewItem
from app.models.shadow_ai import ShadowAIDiscovery
from app.models.sso_config import SSOConfig
from app.models.threat_intel import ThreatIndicator
from app.models.stripe_event import StripeEvent
from app.models.sandbox import Sandbox
from app.models.sandbox_audit_log import SandboxAuditLog
from app.models.sandbox_execution import SandboxExecution
from app.models.user import ApiKey, Organization, User

__all__ = [
    "Agent",
    "AgentPolicy",
    "Alert",
    "AlertDestination",
    "ApiKey",
    "AuditLog",
    "ComplianceReport",
    "Conversation",
    "ConversationTurn",
    "DataArchive",
    "Detector",
    "DetectorRule",
    "Incident",
    "IncidentAction",
    "Organization",
    "ProxyEndpoint",
    "ProxyRequest",
    "RedTeamFinding",
    "RedTeamRun",
    "RetentionPolicy",
    "ReviewItem",
    "Sandbox",
    "SandboxAuditLog",
    "SandboxExecution",
    "ShadowAIDiscovery",
    "SSOConfig",
    "StripeEvent",
    "ThreatIndicator",
    "User",
]
