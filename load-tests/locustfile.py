"""AgentGuard Load Tests

Two user classes:
- DashboardUser: login + browse dashboard/incident endpoints
- ProxyUser: hit the LLM proxy layer with simulated requests

Usage:
    locust -f locustfile.py --host=http://localhost:8001
    locust -f locustfile.py --host=http://localhost:8001 --headless -u 10 -r 2 -t 60s

Environment variables:
    AG_TEST_EMAIL    - Test user email (default: testadmin@agentguard.dev)
    AG_TEST_PASSWORD - Test user password (default: TestPassword1!)
    AG_API_KEY       - API key for proxy tests (ag_live_<hex>). If unset, ProxyUser is skipped.
"""

import logging
import os

from locust import HttpUser, between, task

logger = logging.getLogger(__name__)

TEST_EMAIL = os.getenv("AG_TEST_EMAIL", "testadmin@agentguard.dev")
TEST_PASSWORD = os.getenv("AG_TEST_PASSWORD", "TestPassword1!")
API_KEY = os.getenv("AG_API_KEY", "")


class DashboardUser(HttpUser):
    """Simulates a user browsing the AgentGuard dashboard."""

    wait_time = between(1, 3)
    weight = 3

    def on_start(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            name="/api/v1/auth/login",
        )
        if resp.status_code != 200:
            logger.error("Login failed (%s): %s", resp.status_code, resp.text[:200])
            self.token = None
            self.auth_headers = {}
            return

        data = resp.json()
        self.token = data.get("access_token")
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}

    def _get(self, path: str, **kwargs):
        if not self.token:
            return
        self.client.get(path, headers=self.auth_headers, **kwargs)

    @task(3)
    def get_dashboard_metrics(self):
        self._get("/api/v1/dashboard/metrics")

    @task(2)
    def list_incidents(self):
        self._get("/api/v1/incidents/", params={"limit": 20})

    @task(1)
    def get_incident_stats(self):
        self._get("/api/v1/incidents/stats")

    @task(1)
    def get_cost_analytics(self):
        self._get("/api/v1/dashboard/cost-analytics", params={"days": 30})

    @task(1)
    def get_sla_metrics(self):
        self._get("/api/v1/dashboard/sla-metrics", params={"days": 30})

    @task(1)
    def get_time_series(self):
        self._get("/api/v1/dashboard/time-series", params={"days": 7})

    @task(1)
    def list_detectors(self):
        self._get("/api/v1/detectors/")

    @task(1)
    def get_me(self):
        self._get("/api/v1/auth/me")


class ProxyUser(HttpUser):
    """Simulates API traffic through the LLM proxy layer.

    Requires AG_API_KEY env var set to a valid ag_live_<hex> key.
    Without it, all tasks are skipped silently.
    """

    wait_time = between(2, 5)
    weight = 1

    def on_start(self):
        if not API_KEY:
            logger.warning("AG_API_KEY not set — ProxyUser tasks will be skipped")
            self.api_headers = {}
            return
        self.api_headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

    @task
    def proxy_chat_completion(self):
        if not self.api_headers:
            return
        payload = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are a financial advisor."},
                {"role": "user", "content": "What are current treasury yields?"},
            ],
            "temperature": 0.7,
            "max_tokens": 100,
        }
        self.client.post(
            "/api/v1/proxy/v1/chat/completions",
            json=payload,
            headers=self.api_headers,
            name="/api/v1/proxy/v1/chat/completions",
        )
