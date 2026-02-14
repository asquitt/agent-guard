"""SIEM/SOAR event formatters for standard security event formats.

Transforms AgentGuard incidents into CEF, OCSF, Splunk HEC, ECS, and LEEF
formats so customers can pipe events into their existing security tooling.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

# CEF severity mapping: 0-3 Low, 4-6 Medium, 7-8 High, 9-10 Critical
_CEF_SEVERITY = {"info": 1, "low": 3, "medium": 5, "high": 8, "critical": 10}
_OCSF_SEVERITY = {"info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}
_ECS_SEVERITY = {"info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}


def _ts_epoch(dt: datetime | None) -> float:
    """Convert datetime to epoch float, or current time."""
    if dt:
        return dt.timestamp()
    return time.time()


def _ts_iso(dt: datetime | None) -> str:
    """Convert datetime to ISO 8601 string."""
    if dt:
        return dt.isoformat()
    return datetime.utcnow().isoformat() + "Z"


def _ts_epoch_ms(dt: datetime | None) -> int:
    """Convert datetime to epoch milliseconds."""
    return int(_ts_epoch(dt) * 1000)


def format_splunk_hec(incident: dict[str, Any]) -> dict[str, Any]:
    """Format incident as Splunk HEC JSON payload."""
    return {
        "time": _ts_epoch(incident.get("created_at")),
        "host": "agentguard",
        "source": "agentguard",
        "sourcetype": "agentguard:incident",
        "index": "security",
        "event": {
            "incident_id": str(incident.get("id", "")),
            "severity": incident.get("severity", "info"),
            "category": incident.get("category", "unknown"),
            "title": incident.get("title", ""),
            "description": incident.get("description", ""),
            "status": incident.get("status", "open"),
            "detection_action": incident.get("action_taken", ""),
            "model": incident.get("model", ""),
            "detected_at": _ts_iso(incident.get("created_at")),
        },
        "fields": {
            "org_id": str(incident.get("org_id", "")),
            "proxy_request_id": str(incident.get("proxy_request_id", "")),
            "detector_id": str(incident.get("detector_id", "")),
            "risk_score": incident.get("risk_score", 0),
        },
    }


def format_cef(incident: dict[str, Any]) -> str:
    """Format incident as CEF (Common Event Format) syslog string."""
    severity = _CEF_SEVERITY.get(incident.get("severity", "info"), 1)
    category = incident.get("category", "unknown")
    title = (incident.get("title", "") or "").replace("|", "\\|").replace("\\", "\\\\")
    incident_id = str(incident.get("id", ""))
    org_id = str(incident.get("org_id", ""))
    description = (incident.get("description", "") or "")[:200].replace("=", "\\=")

    extensions = (
        f"msg={description} "
        f"cs1={incident_id} cs1Label=IncidentID "
        f"cs2={org_id} cs2Label=OrganizationID "
        f"cs3={incident.get('model', '')} cs3Label=Model "
        f"act={incident.get('action_taken', 'monitor')} "
        f"cat={category}"
    )

    return (
        f"CEF:0|AgentGuard|AI Incident Response|1.0.0|"
        f"{category}|{title}|{severity}|{extensions}"
    )


def format_leef(incident: dict[str, Any]) -> str:
    """Format incident as LEEF (Log Event Extended Format) for IBM QRadar."""
    severity = _CEF_SEVERITY.get(incident.get("severity", "info"), 1)
    category = incident.get("category", "unknown")
    incident_id = str(incident.get("id", ""))
    org_id = str(incident.get("org_id", ""))
    description = (incident.get("description", "") or "")[:200]
    ts = _ts_iso(incident.get("created_at"))

    attrs = "\t".join([
        f"cat={category}",
        f"sev={severity}",
        f"msg={description}",
        f"devTime={ts}",
        f"incidentId={incident_id}",
        f"orgId={org_id}",
        f"model={incident.get('model', '')}",
        f"act={incident.get('action_taken', 'monitor')}",
    ])

    return f"LEEF:2.0|AgentGuard|AI Incident Response|1.0.0|{category}|\t{attrs}"


def format_ecs(incident: dict[str, Any]) -> dict[str, Any]:
    """Format incident as Elastic Common Schema (ECS) JSON."""
    severity = _ECS_SEVERITY.get(incident.get("severity", "info"), 1)
    category = incident.get("category", "unknown")

    return {
        "@timestamp": _ts_iso(incident.get("created_at")),
        "event": {
            "kind": "alert",
            "category": ["intrusion_detection"],
            "type": ["indicator"],
            "severity": severity,
            "action": incident.get("action_taken", "monitor"),
            "outcome": "success" if incident.get("action_taken") in ("block", "redact") else "unknown",
            "dataset": "agentguard.incident",
        },
        "observer": {
            "vendor": "AgentGuard",
            "product": "AI Incident Response",
            "type": "ai-security",
        },
        "threat": {
            "technique": {
                "name": category.replace("_", " ").title(),
            },
        },
        "organization": {
            "id": str(incident.get("org_id", "")),
        },
        "message": incident.get("title", ""),
        "agentguard": {
            "incident_id": str(incident.get("id", "")),
            "category": category,
            "risk_score": incident.get("risk_score", 0),
            "status": incident.get("status", "open"),
            "model": incident.get("model", ""),
            "proxy_request_id": str(incident.get("proxy_request_id", "")),
        },
    }


def format_ocsf(incident: dict[str, Any]) -> dict[str, Any]:
    """Format incident as OCSF Detection Finding (class_uid 2004)."""
    severity_id = _OCSF_SEVERITY.get(incident.get("severity", "info"), 1)
    sev_label = incident.get("severity", "info").capitalize()
    category = incident.get("category", "unknown")
    incident_id = str(incident.get("id", ""))

    return {
        "activity_id": 1,
        "activity_name": "Create",
        "category_uid": 2,
        "category_name": "Findings",
        "class_uid": 2004,
        "class_name": "Detection Finding",
        "severity_id": severity_id,
        "severity": sev_label,
        "time": _ts_epoch_ms(incident.get("created_at")),
        "finding_info": {
            "uid": incident_id,
            "title": incident.get("title", ""),
            "desc": incident.get("description", ""),
            "types": [category.replace("_", " ").title()],
            "created_time": _ts_epoch_ms(incident.get("created_at")),
        },
        "resources": [
            {
                "uid": str(incident.get("proxy_request_id", "")),
                "name": incident.get("model", "unknown"),
                "type": "LLM Model",
            }
        ],
        "attacks": [
            {
                "technique": {
                    "name": category.replace("_", " ").title(),
                    "uid": _mitre_atlas_uid(category),
                },
            }
        ],
        "remediation": {
            "desc": f"Action taken: {incident.get('action_taken', 'monitor')}",
        },
        "metadata": {
            "product": {
                "name": "AgentGuard",
                "vendor_name": "AgentGuard",
                "version": "1.0.0",
            },
            "version": "1.3.0",
        },
    }


def _mitre_atlas_uid(category: str) -> str:
    """Map detection category to MITRE ATLAS technique ID."""
    mapping = {
        "prompt_injection": "AML.T0051",
        "prompt_extraction": "AML.T0056",
        "pii_leak": "AML.T0024",
        "hallucination": "AML.T0048",
        "cost_anomaly": "AML.T0034",
        "compliance": "AML.T0043",
        "toxicity": "AML.T0048",
        "loop_detection": "AML.T0034",
    }
    return mapping.get(category, "AML.T0000")


# Format registry
FORMATTERS = {
    "splunk_hec": format_splunk_hec,
    "cef": format_cef,
    "leef": format_leef,
    "ecs": format_ecs,
    "ocsf": format_ocsf,
}


def format_incident(incident: dict[str, Any], fmt: str) -> str | dict[str, Any]:
    """Format an incident dict into the specified SIEM format.

    Raises ValueError if the format is not supported.
    """
    formatter = FORMATTERS.get(fmt)
    if not formatter:
        raise ValueError(f"Unsupported SIEM format: {fmt}. Supported: {list(FORMATTERS.keys())}")
    return formatter(incident)


def get_supported_formats() -> list[str]:
    """Return list of supported SIEM format names."""
    return list(FORMATTERS.keys())
