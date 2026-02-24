"""Integration test stubs for untested endpoints.

These stubs document the expected behavior of endpoints that don't yet
have full functional test coverage. They serve as a starting point for
future test development when these features are connected to the live
Docker environment.

Each stub records: HTTP method, path, expected status, and a brief note.
"""

import uuid

from .conftest import S, section, check


def test_sandbox():
    """Sandbox environment endpoints — isolated LLM testing."""
    section("Sandbox (stubs)")
    t = S.get("t1")
    if not t:
        return

    # List sandbox environments
    check("List sandbox envs", "GET", "/api/v1/sandbox/environments", 200, token=t)

    # Create sandbox environment
    check(
        "Create sandbox env",
        "POST",
        "/api/v1/sandbox/environments",
        201,
        json={"name": "test-sandbox", "config": {"provider": "openai", "model": "gpt-4"}},
        token=t,
    )


def test_governance():
    """AI governance policy endpoints — model risk management."""
    section("Governance (stubs)")
    t = S.get("t1")
    if not t:
        return

    check("List governance policies", "GET", "/api/v1/governance/policies", 200, token=t)
    check(
        "Create governance policy",
        "POST",
        "/api/v1/governance/policies",
        201,
        json={"name": "Model Risk Policy", "type": "model_risk", "rules": []},
        token=t,
    )


def test_red_team_advanced():
    """Extended red team endpoints beyond basic CRUD."""
    section("Red Team Advanced (stubs)")
    t = S.get("t1")
    if not t:
        return

    check("List attack templates", "GET", "/api/v1/red-team/templates", 200, token=t)

    if S.get("rt_id"):
        check(
            "Get run results",
            "GET",
            f"/api/v1/red-team/{S['rt_id']}/results",
            200,
            token=t,
        )


def test_sso():
    """SSO / SAML endpoints — enterprise authentication."""
    section("SSO (stubs)")
    t = S.get("t1")
    if not t:
        return

    check("Get SSO config", "GET", "/api/v1/auth/sso/config", 200, token=t)
    check(
        "Update SSO config",
        "PUT",
        "/api/v1/auth/sso/config",
        200,
        json={"provider": "okta", "enabled": False, "metadata_url": ""},
        token=t,
    )


def test_siem():
    """SIEM integration endpoints — security event forwarding."""
    section("SIEM (stubs)")
    t = S.get("t1")
    if not t:
        return

    check("List SIEM integrations", "GET", "/api/v1/siem/integrations", 200, token=t)
    check(
        "Create SIEM integration",
        "POST",
        "/api/v1/siem/integrations",
        201,
        json={"name": "Splunk", "type": "splunk", "config": {"endpoint": "https://splunk.example.com"}},
        token=t,
    )


def test_organizations_advanced():
    """Extended organization endpoints beyond basic CRUD."""
    section("Organizations Advanced (stubs)")
    t = S.get("t1")
    if not t:
        return

    check("Get org settings", "GET", "/api/v1/organizations/current/settings", 200, token=t)
    check(
        "Update org settings",
        "PATCH",
        "/api/v1/organizations/current/settings",
        200,
        json={"retention_days": 90, "mfa_required": False},
        token=t,
    )
    check("Get usage stats", "GET", "/api/v1/organizations/current/usage", 200, token=t)

    # Invite member
    check(
        "Invite member",
        "POST",
        "/api/v1/organizations/current/invites",
        201,
        json={"email": f"invite-{uuid.uuid4().hex[:8]}@test.dev", "role": "viewer"},
        token=t,
    )
