"""LlamaIndex callback handler for AgentGuard.

Buffers selected LlamaIndex callback events and attempts best-effort delivery
to the AgentGuard ingest API.

Usage::

    from llama_index.core import Settings
    from agentguard.integrations.llamaindex import AgentGuardCallbackHandler

    handler = AgentGuardCallbackHandler(
        api_key="ag_live_...",
        base_url="http://localhost:8001",
    )
    Settings.callback_manager.add_handler(handler)
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

import httpx

from agentguard._base_url import normalize_base_url

logger = logging.getLogger("agentguard.llamaindex")

# LlamaIndex CBEventType values we care about
_LLM_EVENT = "llm"
_EMBEDDING_EVENT = "embedding"
_RETRIEVE_EVENT = "retrieve"
_QUERY_EVENT = "query"
_CHUNKING_EVENT = "chunking"


class AgentGuardCallbackHandler:
    """LlamaIndex callback handler that streams events to AgentGuard.

    Implements the ``llama_index.core.callbacks.base.BaseCallbackHandler``
    protocol without requiring a direct import dependency.

    Args:
        api_key: Your AgentGuard API key (``ag_live_...``).
        base_url: AgentGuard API base URL.
        endpoint_id: Optional proxy endpoint UUID.
        metadata: Extra key-value pairs attached to every event.
    """

    event_starts_to_ignore: list[str] = []
    event_ends_to_ignore: list[str] = []

    def __init__(
        self,
        api_key: str,
        base_url: str,
        endpoint_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = normalize_base_url(base_url)
        self.endpoint_id = endpoint_id
        self.metadata = metadata or {}

        self._session_id = str(uuid.uuid4())
        self._events: list[dict[str, Any]] = []
        self._trace_starts: dict[str, float] = {}
        self._event_starts: dict[str, float] = {}

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

    def _emit(self, event: dict[str, Any]) -> None:
        event["session_id"] = self._session_id
        event["metadata"] = self.metadata
        event["timestamp"] = time.time()
        self._events.append(event)

    def _flush(self, *, raise_on_error: bool = False) -> bool:
        if not self._events:
            return True
        batch = self._events[:]
        self._events.clear()
        try:
            response = self._http.post(
                "/api/v1/ingest/events", json={"events": batch}
            )
            response.raise_for_status()
            return True
        except Exception as exc:
            self._events[0:0] = batch
            logger.debug("Failed to flush events to AgentGuard: %s", exc)
            if raise_on_error:
                raise
            return False

    # ── Trace-level callbacks ───────────────────────────────────

    def start_trace(self, trace_id: str | None = None) -> None:
        tid = trace_id or str(uuid.uuid4())
        self._trace_starts[tid] = time.time()
        self._emit({"type": "trace_start", "run_id": tid})

    def end_trace(
        self,
        trace_id: str | None = None,
        trace_map: dict[str, list[str]] | None = None,
    ) -> None:
        tid = trace_id or ""
        duration = time.time() - self._trace_starts.pop(tid, time.time())
        self._emit({
            "type": "trace_end",
            "run_id": tid,
            "duration_ms": round(duration * 1000),
        })
        self._flush()

    # ── Event-level callbacks ───────────────────────────────────

    def on_event_start(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        eid = event_id or str(uuid.uuid4())
        self._event_starts[eid] = time.time()
        payload = payload or {}

        event_data: dict[str, Any] = {
            "type": f"{event_type}_start",
            "run_id": eid,
        }

        if event_type == _LLM_EVENT:
            messages = payload.get("messages", [])
            event_data["message_count"] = len(messages)
            event_data["messages"] = [
                {"role": str(getattr(m, "role", "unknown")),
                 "content": str(getattr(m, "content", m))[:500]}
                for m in messages[:20]
            ]
            event_data["model"] = str(payload.get("model_name", ""))

        elif event_type == _EMBEDDING_EVENT:
            chunks = payload.get("chunks", [])
            event_data["chunk_count"] = len(chunks)

        elif event_type == _RETRIEVE_EVENT:
            event_data["query"] = str(payload.get("query_str", ""))[:500]

        elif event_type == _QUERY_EVENT:
            event_data["query"] = str(payload.get("query_str", ""))[:500]

        self._emit(event_data)
        return eid

    def on_event_end(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        duration = time.time() - self._event_starts.pop(event_id, time.time())
        payload = payload or {}

        event_data: dict[str, Any] = {
            "type": f"{event_type}_end",
            "run_id": event_id,
            "duration_ms": round(duration * 1000),
        }

        if event_type == _LLM_EVENT:
            response = payload.get("response")
            if response and hasattr(response, "message"):
                content = getattr(response.message, "content", "")
                event_data["output"] = str(content)[:500]
            token_usage = {}
            if response and hasattr(response, "raw"):
                raw = response.raw or {}
                usage = raw.get("usage") if isinstance(raw, dict) else getattr(raw, "usage", None)
                if usage:
                    token_usage = {
                        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(usage, "completion_tokens", 0),
                        "total_tokens": getattr(usage, "total_tokens", 0),
                    }
            event_data["token_usage"] = token_usage

        elif event_type == _RETRIEVE_EVENT:
            nodes = payload.get("nodes", [])
            event_data["document_count"] = len(nodes)

        self._emit(event_data)

    # ── Lifecycle ───────────────────────────────────────────────

    def flush(self) -> None:
        """Flush buffered events, raising on transport or HTTP failure."""
        self._flush(raise_on_error=True)

    def close(self) -> None:
        self._flush()
        self._http.close()

    def __del__(self) -> None:
        try:
            self._flush()
            self._http.close()
        except Exception:
            pass
