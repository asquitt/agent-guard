"""Response types for the AgentGuard SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Incident:
    """An AI security incident."""

    id: str
    severity: str
    category: str
    title: str
    status: str
    description: str = ""
    action_taken: str = ""
    model: str = ""
    created_at: str = ""
    updated_at: str = ""
    proxy_request_id: str = ""
    detector_id: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Incident:
        return cls(
            id=str(data.get("id", "")),
            severity=str(data.get("severity", "")),
            category=str(data.get("category", "")),
            title=str(data.get("title", "")),
            status=str(data.get("status", "")),
            description=str(data.get("description", "")),
            action_taken=str(data.get("actionTaken", data.get("action_taken", ""))),
            model=str(data.get("model", "")),
            created_at=str(data.get("createdAt", data.get("created_at", ""))),
            updated_at=str(data.get("updatedAt", data.get("updated_at", ""))),
            proxy_request_id=str(data.get("proxyRequestId", data.get("proxy_request_id", ""))),
            detector_id=str(data.get("detectorId", data.get("detector_id", ""))),
        )


@dataclass(frozen=True)
class IncidentList:
    """Paginated list of incidents."""

    items: list[Incident]
    total: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IncidentList:
        items = [Incident.from_dict(i) for i in data.get("items", [])]
        return cls(items=items, total=data.get("total", len(items)))


@dataclass(frozen=True)
class ProxyResponse:
    """Response from the LLM proxy."""

    data: dict[str, Any]
    status_code: int = 200
    blocked: bool = False
    redacted: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any], status_code: int = 200) -> ProxyResponse:
        return cls(
            data=data,
            status_code=status_code,
            blocked=status_code == 403,
        )


@dataclass(frozen=True)
class Detector:
    """A configured detection rule."""

    id: str
    name: str
    category: str
    is_active: bool
    action_mode: str = "monitor"
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Detector:
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            category=str(data.get("category", "")),
            is_active=bool(data.get("isActive", data.get("is_active", True))),
            action_mode=str(data.get("actionMode", data.get("action_mode", "monitor"))),
            config=data.get("config", {}),
        )
