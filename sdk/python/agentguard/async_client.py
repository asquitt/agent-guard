"""AgentGuard async API client."""

from __future__ import annotations

import httpx


class AsyncAgentGuardClient:
    """Async client for the AgentGuard proxy API."""

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
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._headers(),
        )

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Authorization": f"Bearer {self.api_key}"}
        if self.endpoint_id:
            h["X-AgentGuard-Endpoint-Id"] = self.endpoint_id
        return h

    async def proxy(self, path: str, body: dict) -> dict:  # type: ignore[type-arg]
        """Send a request through the AgentGuard proxy."""
        resp = await self._http.post(f"/api/v1/proxy{path}", json=body)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def list_incidents(self, **filters: str | int) -> dict:  # type: ignore[type-arg]
        """List incidents for the organization."""
        resp = await self._http.get("/api/v1/incidents/", params=filters)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def get_incident(self, incident_id: str) -> dict:  # type: ignore[type-arg]
        """Get a specific incident."""
        resp = await self._http.get(f"/api/v1/incidents/{incident_id}")
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncAgentGuardClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
