"""LangGraph callback handler for AgentGuard.

Captures LLM calls, tool invocations, and graph node/edge transitions
within LangGraph workflows and forwards them through the AgentGuard
ingest API for security monitoring.

Usage::

    from langgraph.graph import StateGraph
    from agentguard.langgraph import AgentGuardLangGraphHandler

    handler = AgentGuardLangGraphHandler(api_key="ag_live_...")
    app = graph.compile()
    result = app.invoke(inputs, config={"callbacks": [handler]})
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Sequence

import httpx

logger = logging.getLogger("agentguard.langgraph")

_CONTENT_TRUNCATE = 500
_MAX_MESSAGES = 20


class AgentGuardLangGraphHandler:
    """LangGraph-compatible callback handler that sends events to AgentGuard.

    Implements the LangChain BaseCallbackHandler interface (which LangGraph
    uses internally) and adds graph-level tracking for node/edge transitions.

    Args:
        api_key: AgentGuard API key (``ag_live_...``).
        base_url: AgentGuard proxy URL.
        endpoint_id: Optional proxy endpoint UUID.
        metadata: Extra key-value pairs sent with every event.
        flush_on_chain_end: Flush buffered events when the outermost chain ends.
        timeout: HTTP timeout for the ingest call in seconds.
    """

    name = "AgentGuardLangGraphHandler"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.agentguard.app",
        endpoint_id: str | None = None,
        metadata: dict[str, str] | None = None,
        flush_on_chain_end: bool = True,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.endpoint_id = endpoint_id
        self.metadata = metadata or {}
        self.flush_on_chain_end = flush_on_chain_end
        self.timeout = timeout

        self.session_id = str(uuid.uuid4())
        self._events: list[dict[str, Any]] = []
        self._run_starts: dict[str, float] = {}
        self._chain_depth = 0
        self._node_stack: list[str] = []

    # -- Internal helpers --------------------------------------------------

    def _emit(self, event_type: str, run_id: str, **extra: Any) -> None:
        """Buffer a single event."""
        event: dict[str, Any] = {
            "type": event_type,
            "run_id": run_id,
            "session_id": self.session_id,
            "timestamp": time.time(),
            "metadata": self.metadata,
            **extra,
        }
        if self._node_stack:
            event["current_node"] = self._node_stack[-1]
        self._events.append(event)

    def _flush(self) -> None:
        """Send buffered events to the AgentGuard ingest API."""
        if not self._events:
            return
        batch = list(self._events)
        self._events.clear()
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.endpoint_id:
            headers["X-AgentGuard-Endpoint-Id"] = self.endpoint_id
        try:
            httpx.post(
                f"{self.base_url}/api/v1/ingest/events",
                json={"events": batch},
                headers=headers,
                timeout=self.timeout,
            )
        except Exception:
            logger.debug("Failed to flush events to AgentGuard", exc_info=True)

    # -- LLM events --------------------------------------------------------

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM call begins."""
        rid = str(run_id)
        self._run_starts[rid] = time.time()
        model_name = (
            serialized.get("kwargs", {}).get("model_name", "")
            or serialized.get("id", [""])[-1]
        )
        self._emit(
            "llm_start",
            rid,
            model=str(model_name),
            prompt_count=len(prompts),
            prompts=[p[:_CONTENT_TRUNCATE] for p in prompts],
        )

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM call completes."""
        rid = str(run_id)
        start = self._run_starts.pop(rid, time.time())
        token_usage: dict[str, Any] = {}
        if hasattr(response, "llm_output") and isinstance(response.llm_output, dict):
            token_usage = response.llm_output.get("token_usage", {})
        self._emit(
            "llm_end",
            rid,
            duration_ms=int((time.time() - start) * 1000),
            token_usage=token_usage,
        )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM call errors."""
        rid = str(run_id)
        self._run_starts.pop(rid, None)
        self._emit(
            "llm_error",
            rid,
            error=str(error)[:_CONTENT_TRUNCATE],
            error_type=type(error).__name__,
        )

    # -- Chat model events -------------------------------------------------

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a chat model call begins."""
        rid = str(run_id)
        self._run_starts[rid] = time.time()
        flat = []
        for group in messages:
            for msg in group:
                role = getattr(msg, "type", "unknown")
                content = str(getattr(msg, "content", ""))[:_CONTENT_TRUNCATE]
                flat.append({"role": role, "content": content})
        model_name = serialized.get("kwargs", {}).get("model_name", "")
        self._emit(
            "chat_model_start",
            rid,
            model=str(model_name),
            message_count=len(flat),
            messages=flat[:_MAX_MESSAGES],
        )

    # -- Chain events (graph-level in LangGraph) ---------------------------

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: Any,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a chain/graph node begins execution."""
        self._chain_depth += 1
        rid = str(run_id)
        self._run_starts[rid] = time.time()

        chain_type = serialized.get("name", "")
        if not chain_type:
            id_parts = serialized.get("id", [])
            chain_type = id_parts[-1] if id_parts else "unknown"

        # Track node for graph context
        node_name = kwargs.get("name", chain_type)
        self._node_stack.append(str(node_name))

        self._emit(
            "chain_start",
            rid,
            chain_type=str(chain_type),
            depth=self._chain_depth,
            node_name=str(node_name),
        )

    def on_chain_end(
        self,
        outputs: Any,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a chain/graph node completes."""
        rid = str(run_id)
        start = self._run_starts.pop(rid, time.time())
        if self._node_stack:
            self._node_stack.pop()
        self._emit(
            "chain_end",
            rid,
            duration_ms=int((time.time() - start) * 1000),
            depth=self._chain_depth,
        )
        self._chain_depth = max(0, self._chain_depth - 1)
        if self._chain_depth == 0 and self.flush_on_chain_end:
            self._flush()

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a chain/graph node errors."""
        rid = str(run_id)
        self._run_starts.pop(rid, None)
        if self._node_stack:
            self._node_stack.pop()
        self._chain_depth = max(0, self._chain_depth - 1)
        self._emit(
            "chain_error",
            rid,
            error=str(error)[:_CONTENT_TRUNCATE],
            error_type=type(error).__name__,
        )
        self._flush()

    # -- Tool events -------------------------------------------------------

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a tool invocation begins."""
        rid = str(run_id)
        self._run_starts[rid] = time.time()
        self._emit(
            "tool_start",
            rid,
            tool_name=str(serialized.get("name", "unknown")),
            input=input_str[:_CONTENT_TRUNCATE],
        )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a tool invocation completes."""
        rid = str(run_id)
        start = self._run_starts.pop(rid, time.time())
        self._emit(
            "tool_end",
            rid,
            duration_ms=int((time.time() - start) * 1000),
            output=str(output)[:_CONTENT_TRUNCATE],
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a tool invocation errors."""
        rid = str(run_id)
        self._run_starts.pop(rid, None)
        self._emit(
            "tool_error",
            rid,
            error=str(error)[:_CONTENT_TRUNCATE],
            error_type=type(error).__name__,
        )

    # -- Agent events ------------------------------------------------------

    def on_agent_action(
        self,
        action: Any,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when an agent decides on an action."""
        rid = str(run_id)
        self._emit(
            "agent_action",
            rid,
            tool=str(getattr(action, "tool", "")),
            tool_input=str(getattr(action, "tool_input", ""))[:_CONTENT_TRUNCATE],
            log=str(getattr(action, "log", ""))[:_CONTENT_TRUNCATE],
        )

    def on_agent_finish(
        self,
        finish: Any,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when an agent completes its run."""
        rid = str(run_id)
        output = getattr(finish, "return_values", finish)
        self._emit(
            "agent_finish",
            rid,
            output=str(output)[:_CONTENT_TRUNCATE],
        )
        self._flush()

    # -- Lifecycle ---------------------------------------------------------

    def manual_flush(self) -> None:
        """Manually flush any buffered events."""
        self._flush()
