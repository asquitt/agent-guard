# pyright: reportGeneralTypeIssues=false, reportArgumentType=false
"""Self-hosted policy classifier for LLM interaction compliance.

Rule-based engine that evaluates LLM interactions against org-defined
policies without external API calls.  Designed for regulated firms that
cannot send data to third-party classifiers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PolicyViolation:
    """Single policy violation detected in an LLM interaction."""

    policy_name: str
    severity: str
    description: str
    matched_text: str
    action: str  # "block" | "warn" | "log"


@dataclass(frozen=True, slots=True)
class PolicyRule:
    """A single pattern / keyword check within a policy."""

    pattern: re.Pattern[str]
    description: str


@dataclass(frozen=True, slots=True)
class Policy:
    """Configurable compliance policy definition."""

    name: str
    description: str
    category: str
    rules: tuple[PolicyRule, ...]
    severity: str   # "critical" | "high" | "medium" | "low"
    action: str     # "block" | "warn" | "log"
    check_request: bool  # whether to scan the user prompt
    check_response: bool  # whether to scan the LLM output


# ---------------------------------------------------------------------------
# Built-in financial compliance policies
# ---------------------------------------------------------------------------

def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


_BUILTIN_POLICIES: tuple[Policy, ...] = (
    Policy(
        name="no_investment_advice",
        description="Block responses giving specific investment recommendations",
        category="investment_advisory",
        rules=(
            PolicyRule(
                _compile(
                    r"\b(?:you\s+should|i\s+recommend|i\s+suggest)\s+"
                    r"(?:buy|sell|invest\s+in|short|hold|trade)\b"
                ),
                "Direct investment recommendation detected",
            ),
            PolicyRule(
                _compile(
                    r"\b(?:buy|sell|go\s+long|go\s+short)\s+"
                    r"(?:shares?|stock|options?|bonds?|etfs?|crypto)\b"
                ),
                "Specific trade instruction detected",
            ),
            PolicyRule(
                _compile(
                    r"\b(?:strong\s+buy|undervalued|overvalued|"
                    r"price\s+target|fair\s+value\s+is)\b"
                ),
                "Analyst-style rating language detected",
            ),
        ),
        severity="critical",
        action="block",
        check_request=False,
        check_response=True,
    ),
    Policy(
        name="no_guarantees",
        description="Flag responses promising returns or guarantees",
        category="misleading_claims",
        rules=(
            PolicyRule(
                _compile(
                    r"\b(?:guarantee[ds]?\s+(?:return|profit|gain)|"
                    r"risk[\s-]*free\s+(?:return|investment|profit)|"
                    r"you\s+will\s+(?:earn|make|profit))\b"
                ),
                "Guaranteed return language detected",
            ),
            PolicyRule(
                _compile(
                    r"\b(?:cannot?\s+lose|no\s+risk|zero\s+risk|"
                    r"sure\s+thing|certain\s+to\s+(?:rise|increase|grow))\b"
                ),
                "Zero-risk claim detected",
            ),
        ),
        severity="high",
        action="warn",
        check_request=False,
        check_response=True,
    ),
    Policy(
        name="disclosure_required",
        description="Flag responses that should include regulatory disclaimers",
        category="regulatory_disclosure",
        rules=(
            PolicyRule(
                _compile(
                    r"\b(?:past\s+performance|historical\s+returns?|"
                    r"previous\s+results)\b"
                ),
                "Past performance reference without disclaimer",
            ),
            PolicyRule(
                _compile(
                    r"\b(?:projected\s+returns?|expected\s+(?:growth|returns?)|"
                    r"forecast(?:ed)?\s+(?:earnings?|revenue))\b"
                ),
                "Forward-looking statement without disclaimer",
            ),
        ),
        severity="medium",
        action="warn",
        check_request=False,
        check_response=True,
    ),
    Policy(
        name="no_insider_trading",
        description="Block responses referencing material non-public information",
        category="insider_trading",
        rules=(
            PolicyRule(
                _compile(
                    r"\b(?:material\s+non[\s-]*public|mnpi|"
                    r"inside\s+information|not\s+(?:yet\s+)?public)\b"
                ),
                "MNPI reference detected",
            ),
            PolicyRule(
                _compile(
                    r"\b(?:upcoming\s+(?:earnings|merger|acquisition)|"
                    r"unannounced\s+(?:deal|partnership|layoff)|"
                    r"before\s+(?:the\s+)?(?:announcement|disclosure))\b"
                ),
                "Pre-announcement information reference detected",
            ),
        ),
        severity="critical",
        action="block",
        check_request=True,
        check_response=True,
    ),
    Policy(
        name="client_data_separation",
        description="Flag when response mixes data from different clients",
        category="data_segregation",
        rules=(
            PolicyRule(
                _compile(
                    r"\b(?:other\s+client(?:'?s)?|another\s+(?:customer|account)|"
                    r"different\s+(?:client|customer|portfolio))\b"
                ),
                "Cross-client data reference detected",
            ),
            PolicyRule(
                _compile(
                    r"\b(?:compared?\s+(?:to|with)\s+(?:other|another)\s+"
                    r"(?:client|customer|account))\b"
                ),
                "Cross-client comparison detected",
            ),
        ),
        severity="high",
        action="warn",
        check_request=False,
        check_response=True,
    ),
    Policy(
        name="audit_trail_required",
        description="Flag high-risk decisions without proper logging",
        category="audit_compliance",
        rules=(
            PolicyRule(
                _compile(
                    r"\b(?:approv(?:e|ed|ing)\s+(?:the\s+)?(?:trade|transfer|"
                    r"transaction|withdrawal|wire)|"
                    r"execut(?:e|ed|ing)\s+(?:the\s+)?(?:order|trade|transfer))\b"
                ),
                "High-risk action without audit context detected",
            ),
            PolicyRule(
                _compile(
                    r"\b(?:overrid(?:e|ing)\s+(?:the\s+)?(?:limit|control|"
                    r"restriction|compliance\s+check))\b"
                ),
                "Control override language detected",
            ),
        ),
        severity="high",
        action="warn",
        check_request=True,
        check_response=True,
    ),
    Policy(
        name="model_risk_disclosure",
        description="Flag AI-generated content lacking model disclosure",
        category="model_transparency",
        rules=(
            PolicyRule(
                _compile(
                    r"\b(?:based\s+on\s+(?:my|our)\s+analysis|"
                    r"(?:my|our)\s+(?:research|assessment|evaluation)\s+"
                    r"(?:shows?|indicates?|suggests?))\b"
                ),
                "AI presenting as authoritative analyst without disclosure",
            ),
            PolicyRule(
                _compile(
                    r"\b(?:i(?:'ve|\s+have)\s+(?:reviewed|analyzed|assessed)|"
                    r"(?:my|our)\s+(?:recommendation|opinion|view)\s+is)\b"
                ),
                "AI opinion presented without model risk disclosure",
            ),
        ),
        severity="medium",
        action="log",
        check_request=False,
        check_response=True,
    ),
)


# ---------------------------------------------------------------------------
# Classification engine
# ---------------------------------------------------------------------------

def _scan_text(
    text: str,
    policy: Policy,
    source: str,
) -> list[PolicyViolation]:
    """Scan a single text block against a policy's rules."""
    violations: list[PolicyViolation] = []
    for rule in policy.rules:
        match = rule.pattern.search(text)
        if match:
            violations.append(
                PolicyViolation(
                    policy_name=policy.name,
                    severity=policy.severity,
                    description=f"{rule.description} (in {source})",
                    matched_text=match.group(0),
                    action=policy.action,
                )
            )
    return violations


def classify(
    request_text: str,
    response_text: str,
    policies: Sequence[Policy] | None = None,
) -> list[PolicyViolation]:
    """Classify an LLM interaction against policies.

    Args:
        request_text: The user prompt / request.
        response_text: The LLM response.
        policies: Policies to evaluate. Defaults to all built-in policies.

    Returns:
        List of policy violations found.
    """
    active_policies = policies if policies is not None else _BUILTIN_POLICIES
    violations: list[PolicyViolation] = []

    for policy in active_policies:
        if policy.check_request and request_text:
            violations.extend(_scan_text(request_text, policy, "request"))
        if policy.check_response and response_text:
            violations.extend(_scan_text(response_text, policy, "response"))

    return violations


def get_available_policies() -> list[dict[str, str | list[str]]]:
    """Return metadata for all built-in policies."""
    return [
        {
            "name": p.name,
            "description": p.description,
            "category": p.category,
            "severity": p.severity,
            "action": p.action,
            "rule_count": str(len(p.rules)),
        }
        for p in _BUILTIN_POLICIES
    ]


# ---------------------------------------------------------------------------
# Compliance statistics (DB-backed)
# ---------------------------------------------------------------------------

# Map policy categories to incident categories for compliance scoring
_POLICY_TO_INCIDENT_CATEGORIES: dict[str, list[str]] = {
    "investment_advisory": ["compliance"],
    "misleading_claims": ["compliance", "hallucination"],
    "regulatory_disclosure": ["compliance"],
    "insider_trading": ["compliance", "pii_leak"],
    "data_segregation": ["pii_leak"],
    "audit_compliance": ["compliance"],
    "model_transparency": ["compliance"],
}


async def evaluate_compliance(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> dict:
    """Return compliance stats for all policy categories over a period.

    Queries incident counts by mapped categories to estimate how the
    org is performing against each policy area.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            Incident.category,
            func.count(Incident.id).label("total"),
        )
        .where(
            Incident.org_id == org_id,
            Incident.created_at >= cutoff,
        )
        .group_by(Incident.category)
    )
    incident_counts: dict[str, int] = {
        str(row.category): row.total for row in result.all()
    }

    policy_stats: list[dict[str, str | int]] = []
    total_violations = 0

    for policy in _BUILTIN_POLICIES:
        mapped = _POLICY_TO_INCIDENT_CATEGORIES.get(policy.category, [])
        violation_count = sum(incident_counts.get(cat, 0) for cat in mapped)
        total_violations += violation_count
        policy_stats.append({
            "policy_name": policy.name,
            "category": policy.category,
            "severity": policy.severity,
            "violations": violation_count,
            "status": "clean" if violation_count == 0 else "violations_found",
        })

    clean_count = sum(1 for s in policy_stats if s["status"] == "clean")
    compliance_rate = round(clean_count / len(policy_stats) * 100, 1) if policy_stats else 100.0

    return {
        "policies": policy_stats,
        "total_policies": len(policy_stats),
        "clean_policies": clean_count,
        "total_violations": total_violations,
        "compliance_rate": compliance_rate,
        "period_days": days,
    }
