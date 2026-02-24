"""Incident listing and filtering functional tests."""

import uuid

from .conftest import S, section, check


def test_incidents():
    section("Incidents")
    t = S.get("t1")
    check("List incidents", "GET", "/api/v1/incidents/", 200, token=t)
    check("Incident stats", "GET", "/api/v1/incidents/stats", 200, token=t)
    check("Filter by severity", "GET", "/api/v1/incidents/?severity=critical", 200, token=t)
    fake_id = str(uuid.uuid4())
    check("Nonexistent incident", "GET", f"/api/v1/incidents/{fake_id}", 404, token=t)
