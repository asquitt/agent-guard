"""OpenTelemetry span exporter for AgentGuard.

Exports trace spans to the AgentGuard traces API so they appear in the
observability dashboard alongside proxy-originated traces.

Usage::

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from agentguard.integrations.otel import AgentGuardSpanExporter

    exporter = AgentGuardSpanExporter(api_key="ag_live_...")
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

import httpx

logger = logging.getLogger("agentguard.otel")


class AgentGuardSpanExporter:
    """OpenTelemetry SpanExporter that sends spans to AgentGuard.

    Implements the ``opentelemetry.sdk.trace.export.SpanExporter`` protocol
    so it can be used with ``BatchSpanProcessor`` or ``SimpleSpanProcessor``.

    Args:
        api_key: Your AgentGuard API key (``ag_live_...``).
        base_url: AgentGuard API base URL.
        endpoint_id: Optional proxy endpoint UUID.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.agentguard.app",
        endpoint_id: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.endpoint_id = endpoint_id
        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=10.0,
            headers=self._headers(),
        )

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Authorization": f"Bearer {self.api_key}"}
        if self.endpoint_id:
            h["X-AgentGuard-Endpoint-Id"] = self.endpoint_id
        return h

    def export(self, spans: Sequence[Any]) -> int:
        """Export a batch of spans to AgentGuard.

        Returns:
            SpanExportResult.SUCCESS (0) or SpanExportResult.FAILURE (1).
        """
        payload = []
        for span in spans:
            ctx = span.get_span_context()
            payload.append({
                "trace_id": format(ctx.trace_id, "032x"),
                "span_id": format(ctx.span_id, "016x"),
                "parent_span_id": (
                    format(span.parent.span_id, "016x")
                    if span.parent
                    else None
                ),
                "name": span.name,
                "kind": span.kind.name if hasattr(span.kind, "name") else str(span.kind),
                "start_time_ns": span.start_time,
                "end_time_ns": span.end_time,
                "status": span.status.status_code.name if span.status else "UNSET",
                "attributes": dict(span.attributes) if span.attributes else {},
                "events": [
                    {
                        "name": evt.name,
                        "timestamp_ns": evt.timestamp,
                        "attributes": dict(evt.attributes) if evt.attributes else {},
                    }
                    for evt in (span.events or [])
                ],
            })

        try:
            resp = self._http.post(
                "/api/v1/ingest/traces",
                json={"spans": payload},
            )
            if resp.status_code < 400:
                return 0  # SUCCESS
            logger.debug("AgentGuard trace export failed: %d", resp.status_code)
            return 1  # FAILURE
        except Exception as exc:
            logger.debug("AgentGuard trace export error: %s", exc)
            return 1

    def shutdown(self) -> None:
        """Shut down the exporter and close the HTTP client."""
        self._http.close()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush is a no-op since we export synchronously."""
        return True
