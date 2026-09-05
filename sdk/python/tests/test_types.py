"""Tests for agentguard.types."""

from agentguard.types import Detector, Incident, IncidentList, ProxyResponse


# ── Incident ─────────────────────────────────────────────────────

def test_incident_from_dict_snake_case():
    data = {
        "id": "inc-1",
        "severity": "high",
        "category": "pii_leak",
        "title": "PII Detected",
        "status": "open",
        "description": "SSN found",
        "action_taken": "redacted",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T01:00:00Z",
        "proxy_request_id": "req-1",
        "detector_id": "det-1",
    }
    inc = Incident.from_dict(data)
    assert inc.id == "inc-1"
    assert inc.severity == "high"
    assert inc.action_taken == "redacted"
    assert inc.created_at == "2024-01-01T00:00:00Z"
    assert inc.proxy_request_id == "req-1"


def test_incident_from_dict_camel_case():
    data = {
        "id": "inc-2",
        "severity": "critical",
        "category": "compliance",
        "title": "SOX Violation",
        "status": "acknowledged",
        "actionTaken": "blocked",
        "createdAt": "2024-06-01",
        "updatedAt": "2024-06-02",
        "proxyRequestId": "req-2",
        "detectorId": "det-2",
    }
    inc = Incident.from_dict(data)
    assert inc.action_taken == "blocked"
    assert inc.created_at == "2024-06-01"
    assert inc.proxy_request_id == "req-2"
    assert inc.detector_id == "det-2"


def test_incident_from_dict_defaults():
    data = {"id": "inc-3", "severity": "info", "category": "test", "title": "T", "status": "open"}
    inc = Incident.from_dict(data)
    assert inc.description is None
    assert inc.action_taken is None


def test_incident_from_dict_does_not_stringify_nullable_backend_fields():
    data = {
        "id": "inc-4",
        "severity": "low",
        "category": "pii_leak",
        "title": "Nullable evidence",
        "status": "open",
        "description": None,
        "actionTaken": None,
        "proxyRequestId": None,
        "detectorId": None,
        "sandboxExecutionId": None,
        "resolvedAt": None,
        "createdAt": "2026-09-05T00:00:00Z",
        "updatedAt": "2026-09-05T00:00:00Z",
    }

    incident = Incident.from_dict(data)

    assert incident.description is None
    assert incident.action_taken is None
    assert incident.proxy_request_id is None
    assert incident.detector_id is None
    assert incident.sandbox_execution_id is None
    assert incident.resolved_at is None


def test_incident_frozen():
    inc = Incident.from_dict({"id": "x", "severity": "low", "category": "c", "title": "t", "status": "open"})
    try:
        inc.id = "y"  # type: ignore[misc]
        assert False, "Should be frozen"
    except AttributeError:
        pass


# ── IncidentList ─────────────────────────────────────────────────

def test_incident_list_from_dict():
    data = {
        "items": [
            {"id": "1", "severity": "high", "category": "pii", "title": "A", "status": "open"},
            {"id": "2", "severity": "low", "category": "cost", "title": "B", "status": "resolved"},
        ],
        "total": 42,
    }
    result = IncidentList.from_dict(data)
    assert len(result.items) == 2
    assert result.total == 42
    assert result.items[0].id == "1"


def test_incident_list_empty():
    result = IncidentList.from_dict({"items": [], "total": 0})
    assert len(result.items) == 0
    assert result.total == 0


def test_incident_list_total_defaults_to_len():
    data = {"items": [{"id": "1", "severity": "h", "category": "c", "title": "t", "status": "o"}]}
    result = IncidentList.from_dict(data)
    assert result.total == 1


# ── ProxyResponse ────────────────────────────────────────────────

def test_proxy_response_ok():
    resp = ProxyResponse.from_dict({"choices": [{"text": "hello"}]}, status_code=200)
    assert resp.status_code == 200
    assert resp.blocked is False
    assert resp.data["choices"][0]["text"] == "hello"


def test_proxy_response_blocked():
    resp = ProxyResponse.from_dict({"error": "blocked"}, status_code=403)
    assert resp.blocked is True
    assert resp.status_code == 403


def test_proxy_response_default_status():
    resp = ProxyResponse.from_dict({"data": "ok"})
    assert resp.status_code == 200
    assert resp.redacted is False


# ── Detector ─────────────────────────────────────────────────────

def test_detector_from_dict_snake_case():
    data = {
        "id": "det-1",
        "name": "PII Detector",
        "category": "pii_leak",
        "is_active": True,
        "action_mode": "block",
        "config": {"threshold": 0.8},
    }
    det = Detector.from_dict(data)
    assert det.id == "det-1"
    assert det.is_active is True
    assert det.action_mode == "block"
    assert det.config["threshold"] == 0.8


def test_detector_from_dict_camel_case():
    data = {
        "id": "det-2",
        "name": "Loop Detector",
        "category": "loop",
        "isActive": False,
        "actionMode": "monitor",
    }
    det = Detector.from_dict(data)
    assert det.is_active is False
    assert det.action_mode == "monitor"


def test_detector_defaults():
    data = {"id": "det-3", "name": "Test", "category": "test"}
    det = Detector.from_dict(data)
    assert det.is_active is True
    assert det.action_mode == "monitor"
    assert det.config == {}
