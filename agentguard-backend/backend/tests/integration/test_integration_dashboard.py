"""Integration tests for dashboard.py router.

Endpoints:
  GET /api/v1/dashboard/metrics
  GET /api/v1/dashboard/cost-analytics
  GET /api/v1/dashboard/sla-metrics
  GET /api/v1/dashboard/detection-efficacy
  GET /api/v1/dashboard/provider-comparison
  GET /api/v1/dashboard/time-series
  GET /api/v1/dashboard/risk-score

Note: Some endpoints use PostgreSQL-specific functions (percentile_cont,
date_trunc, FILTER). Tests that require these are marked with
`pytest.mark.skip` for SQLite and tested for auth only.
"""

import pytest
from httpx import AsyncClient

from app.models.user import Organization, User

PREFIX = "/api/v1/dashboard"

# Marker for tests that use PostgreSQL-specific SQL
pg_only = pytest.mark.skip(reason="Requires PostgreSQL (uses date_trunc/percentile_cont)")


# ── Metrics ──────────────────────────────────────────────────────────


class TestDashboardMetrics:
    """GET /api/v1/dashboard/metrics"""

    async def test_metrics_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(f"{PREFIX}/metrics", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "total_incidents" in body or "totalIncidents" in body
        assert "open_incidents" in body or "openIncidents" in body
        assert "incidents_by_status" in body or "incidentsByStatus" in body
        assert "incidents_by_severity" in body or "incidentsBySeverity" in body
        assert "recent_incidents" in body or "recentIncidents" in body

    async def test_metrics_empty_org(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """New org with no incidents -> all zeros."""
        resp = await client.get(f"{PREFIX}/metrics", headers=auth_headers)
        body = resp.json()
        total = body.get("total_incidents", body.get("totalIncidents"))
        assert total == 0

    async def test_metrics_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/metrics")
        assert resp.status_code == 401

    async def test_metrics_invalid_token(self, client: AsyncClient):
        resp = await client.get(
            f"{PREFIX}/metrics",
            headers={"Authorization": "Bearer bad-token"},
        )
        assert resp.status_code == 401


# ── Cost Analytics ───────────────────────────────────────────────────


class TestCostAnalytics:
    """GET /api/v1/dashboard/cost-analytics

    Uses date_trunc for daily cost breakdown -> skip functional tests on SQLite.
    """

    @pg_only
    async def test_cost_analytics_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/cost-analytics", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total_cost" in body or "totalCost" in body
        assert "total_requests" in body or "totalRequests" in body

    @pg_only
    async def test_cost_analytics_with_days_param(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/cost-analytics?days=7", headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_cost_analytics_invalid_days(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """days=0 -> 422 (ge=1). Validation happens before SQL."""
        resp = await client.get(
            f"{PREFIX}/cost-analytics?days=0", headers=auth_headers
        )
        assert resp.status_code == 422

    async def test_cost_analytics_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/cost-analytics")
        assert resp.status_code == 401


# ── SLA Metrics ──────────────────────────────────────────────────────


class TestSlaMetrics:
    """GET /api/v1/dashboard/sla-metrics

    Uses percentile_cont and FILTER -> skip on SQLite.
    """

    @pg_only
    async def test_sla_metrics_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/sla-metrics", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total_requests" in body or "totalRequests" in body

    async def test_sla_metrics_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/sla-metrics")
        assert resp.status_code == 401


# ── Detection Efficacy ───────────────────────────────────────────────


class TestDetectionEfficacy:
    """GET /api/v1/dashboard/detection-efficacy

    Uses cast to DATE -> skip on SQLite.
    """

    @pg_only
    async def test_detection_efficacy_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/detection-efficacy", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "categories" in body
        assert "overall_false_positive_rate" in body or "overallFalsePositiveRate" in body

    async def test_detection_efficacy_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/detection-efficacy")
        assert resp.status_code == 401


# ── Provider Comparison ──────────────────────────────────────────────


class TestProviderComparison:
    """GET /api/v1/dashboard/provider-comparison

    Uses percentile_cont -> skip on SQLite.
    """

    @pg_only
    async def test_provider_comparison_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/provider-comparison", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "providers" in body

    async def test_provider_comparison_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/provider-comparison")
        assert resp.status_code == 401


# ── Time Series ──────────────────────────────────────────────────────


class TestTimeSeries:
    """GET /api/v1/dashboard/time-series

    Uses date_trunc -> skip on SQLite.
    """

    @pg_only
    async def test_time_series_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/time-series", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "buckets" in body
        assert "granularity" in body

    async def test_time_series_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/time-series")
        assert resp.status_code == 401


# ── Risk Score ───────────────────────────────────────────────────────


class TestRiskScore:
    """GET /api/v1/dashboard/risk-score

    Uses cast to DATE internally -> skip on SQLite.
    """

    @pg_only
    async def test_risk_score_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/risk-score", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "overall_score" in body or "overallScore" in body
        assert "grade" in body

    async def test_risk_score_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/risk-score")
        assert resp.status_code == 401


# ── Tenant Isolation ─────────────────────────────────────────────────


class TestDashboardTenantIsolation:
    """Dashboard metrics should be scoped to the user's org."""

    async def test_other_org_sees_own_metrics(
        self, client: AsyncClient, other_org_headers: dict[str, str]
    ):
        """Other org gets metrics for THEIR org (zeros), not the primary org."""
        resp = await client.get(
            f"{PREFIX}/metrics", headers=other_org_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        total = body.get("total_incidents", body.get("totalIncidents"))
        assert total == 0
