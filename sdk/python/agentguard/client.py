"""AgentGuard API client."""

from __future__ import annotations

import httpx


class AgentGuardClient:
    """Low-level client for the AgentGuard proxy API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.agentguard.app",
        endpoint_id: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.endpoint_id = endpoint_id
        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._headers(),
        )

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Authorization": f"Bearer {self.api_key}"}
        if self.endpoint_id:
            h["X-AgentGuard-Endpoint-Id"] = self.endpoint_id
        return h

    def proxy(self, path: str, body: dict) -> dict:
        """Send a request through the AgentGuard proxy."""
        resp = self._http.post(f"/api/v1/proxy{path}", json=body)
        resp.raise_for_status()
        return resp.json()

    def list_incidents(self, **filters) -> dict:
        """List incidents for the organization."""
        resp = self._http.get("/api/v1/incidents/", params=filters)
        resp.raise_for_status()
        return resp.json()

    def get_incident(self, incident_id: str) -> dict:
        """Get a specific incident."""
        resp = self._http.get(f"/api/v1/incidents/{incident_id}")
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "AgentGuardClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
