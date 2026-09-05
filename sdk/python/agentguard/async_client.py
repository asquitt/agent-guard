"""AgentGuard async API client."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from agentguard._base_url import normalize_base_url
from agentguard.exceptions import raise_for_status
from agentguard.types import Incident, IncidentList, ProxyResponse

logger = logging.getLogger("agentguard")


class AsyncAgentGuardClient:
    """Async client for the AgentGuard API.

    Usage::

        from agentguard import AsyncAgentGuardClient

        async with AsyncAgentGuardClient(
            api_key="ag-...",
            base_url="http://localhost:8001",
            access_token="user-access-token",
        ) as client:
            incidents = await client.list_incidents(severity="critical")
            for inc in incidents.items:
                print(inc.title, inc.severity)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        endpoint_id: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 3,
        access_token: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.access_token = access_token
        self.base_url = normalize_base_url(base_url)
        self.endpoint_id = endpoint_id
        self.max_retries = max_retries
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._headers(),
        )

    def _headers(self) -> dict[str, str]:
        """Return organization API-key headers for proxy requests."""
        h: dict[str, str] = {"Authorization": f"Bearer {self.api_key}"}
        if self.endpoint_id:
            h["X-AgentGuard-Endpoint-Id"] = self.endpoint_id
        return h

    def _management_headers(self) -> dict[str, str]:
        """Return user access-token headers for protected management routes."""
        if not self.access_token:
            raise ValueError(
                "access_token is required for AgentGuard management routes"
            )
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _request_with_retry(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """Execute an HTTP request with retry logic for transient errors."""
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                resp = await self._http.request(method, url, **kwargs)
                if resp.status_code == 429 and attempt < self.max_retries - 1:
                    retry_after = int(resp.headers.get("Retry-After", "2"))
                    logger.debug("Rate limited, retrying in %ds", retry_after)
                    await asyncio.sleep(min(retry_after, 30))
                    continue
                if resp.status_code >= 500 and attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    logger.debug("Server error %d, retrying in %ds", resp.status_code, wait)
                    await asyncio.sleep(wait)
                    continue
                return resp
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                last_exc = e
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    logger.debug("Connection error, retrying in %ds: %s", wait, e)
                    await asyncio.sleep(wait)
                    continue
                raise
        if last_exc:
            raise last_exc
        raise RuntimeError("Unreachable")

    async def proxy(self, path: str, body: dict[str, Any]) -> ProxyResponse:
        """Send a request through the AgentGuard proxy."""
        resp = await self._request_with_retry("POST", f"/api/v1/proxy{path}", json=body)
        raise_for_status(resp)
        return ProxyResponse.from_dict(resp.json(), status_code=resp.status_code)

    async def list_incidents(self, **filters: Any) -> IncidentList:
        """List incidents for the organization."""
        resp = await self._request_with_retry(
            "GET",
            "/api/v1/incidents/",
            params=filters,
            headers=self._management_headers(),
        )
        raise_for_status(resp)
        return IncidentList.from_dict(resp.json())

    async def get_incident(self, incident_id: str) -> Incident:
        """Get a specific incident."""
        resp = await self._request_with_retry(
            "GET",
            f"/api/v1/incidents/{incident_id}",
            headers=self._management_headers(),
        )
        raise_for_status(resp)
        return Incident.from_dict(resp.json())

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncAgentGuardClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
