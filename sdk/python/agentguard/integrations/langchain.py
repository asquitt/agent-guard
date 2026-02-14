"""LangChain callback handler for AgentGuard.

Captures LLM calls, chain runs, tool invocations, and agent actions,
then forwards them through the AgentGuard proxy for real-time detection.

Usage::

    from langchain_openai import ChatOpenAI
    from agentguard.integrations.langchain import AgentGuardCallbackHandler

    handler = AgentGuardCallbackHandler(api_key="ag_live_...")
    llm = ChatOpenAI(callbacks=[handler])
    llm.invoke("Summarize our Q4 financials")
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Sequence

import httpx

logger = logging.getLogger("agentguard.langchain")


class AgentGuardCallbackHandler:
    """LangChain callback handler that streams events to AgentGuard.

    Captures LLM prompts/completions, chain metadata, tool calls, and agent
    decisions. All events are sent asynchronously to the AgentGuard ingest
    API so they appear in the dashboard alongside proxy-originated events.

    Args:
        api_key: Your AgentGuard API key (``ag_live_...``).
        base_url: AgentGuard API base URL.
        endpoint_id: Optional proxy endpoint UUID for routing.
        metadata: Extra key-value pairs attached to every event.
        flush_on_chain_end: Whether to flush buffered events when a
            top-level chain finishes. Defaults to True.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.agentguard.app",
        endpoint_id: str | None = None,
        metadata: dict[str, str] | None = None,
        flush_on_chain_end: bool = True,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.endpoint_id = endpoint_id
        self.metadata = metadata or {}
        self.flush_on_chain_end = flush_on_chain_end

        self._session_id = str(uuid.uuid4())
        self._events: list[dict[str, Any]] = []
        self._run_starts: dict[str, float] = {}
        self._chain_depth = 0

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

    def _flush(self) -> None:
        if not self._events:
            return
        batch = self._events[:]
        self._events.clear()
        try:
            self._http.post(
                "/api/v1/ingest/events",
                json={"events": batch},
            )
        except Exception as exc:
            logger.debug("Failed to flush events to AgentGuard: %s", exc)
            # Non-blocking: don't break the user's chain

    # ── LLM Events ──────────────────────────────────────────────

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or uuid.uuid4())
        self._run_starts[rid] = time.time()
        self._emit({
            "type": "llm_start",
            "run_id": rid,
            "model": serialized.get("kwargs", {}).get("model_name", ""),
            "prompt_count": len(prompts),
            "prompts": [p[:500] for p in prompts],
        })

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or "")
        duration = time.time() - self._run_starts.pop(rid, time.time())
        generations = []
        if hasattr(response, "generations"):
            for gen_list in response.generations:
                for gen in gen_list:
                    text = gen.text if hasattr(gen, "text") else str(gen)
                    generations.append(text[:500])

        token_usage = {}
        if hasattr(response, "llm_output") and response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})

        self._emit({
            "type": "llm_end",
            "run_id": rid,
            "duration_ms": round(duration * 1000),
            "generation_count": len(generations),
            "generations": generations,
            "token_usage": token_usage,
        })

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or "")
        self._run_starts.pop(rid, None)
        self._emit({
            "type": "llm_error",
            "run_id": rid,
            "error": str(error)[:500],
            "error_type": type(error).__name__,
        })

    # ── Chat Model Events ───────────────────────────────────────

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or uuid.uuid4())
        self._run_starts[rid] = time.time()

        flat_messages = []
        for msg_list in messages:
            for msg in msg_list:
                role = getattr(msg, "type", "unknown")
                content = getattr(msg, "content", str(msg))
                flat_messages.append({
                    "role": role,
                    "content": content[:500] if isinstance(content, str) else str(content)[:500],
                })

        self._emit({
            "type": "chat_model_start",
            "run_id": rid,
            "model": serialized.get("kwargs", {}).get("model_name", ""),
            "message_count": len(flat_messages),
            "messages": flat_messages[:20],
        })

    # ── Chain Events ────────────────────────────────────────────

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self._chain_depth += 1
        rid = str(run_id or uuid.uuid4())
        self._run_starts[rid] = time.time()
        self._emit({
            "type": "chain_start",
            "run_id": rid,
            "chain_type": serialized.get("name", serialized.get("id", ["unknown"])[-1]),
            "depth": self._chain_depth,
        })

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or "")
        duration = time.time() - self._run_starts.pop(rid, time.time())
        self._emit({
            "type": "chain_end",
            "run_id": rid,
            "duration_ms": round(duration * 1000),
            "depth": self._chain_depth,
        })
        self._chain_depth = max(0, self._chain_depth - 1)

        if self._chain_depth == 0 and self.flush_on_chain_end:
            self._flush()

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or "")
        self._run_starts.pop(rid, None)
        self._chain_depth = max(0, self._chain_depth - 1)
        self._emit({
            "type": "chain_error",
            "run_id": rid,
            "error": str(error)[:500],
            "error_type": type(error).__name__,
        })
        self._flush()

    # ── Tool Events ─────────────────────────────────────────────

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or uuid.uuid4())
        self._run_starts[rid] = time.time()
        self._emit({
            "type": "tool_start",
            "run_id": rid,
            "tool_name": serialized.get("name", "unknown"),
            "input": input_str[:500],
        })

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or "")
        duration = time.time() - self._run_starts.pop(rid, time.time())
        self._emit({
            "type": "tool_end",
            "run_id": rid,
            "duration_ms": round(duration * 1000),
            "output": str(output)[:500],
        })

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or "")
        self._run_starts.pop(rid, None)
        self._emit({
            "type": "tool_error",
            "run_id": rid,
            "error": str(error)[:500],
            "error_type": type(error).__name__,
        })

    # ── Agent Events ────────────────────────────────────────────

    def on_agent_action(
        self,
        action: Any,
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self._emit({
            "type": "agent_action",
            "run_id": str(run_id or ""),
            "tool": getattr(action, "tool", str(action)),
            "tool_input": str(getattr(action, "tool_input", ""))[:500],
            "log": getattr(action, "log", "")[:500],
        })

    def on_agent_finish(
        self,
        finish: Any,
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self._emit({
            "type": "agent_finish",
            "run_id": str(run_id or ""),
            "output": str(getattr(finish, "return_values", finish))[:500],
        })
        self._flush()

    # ── Retriever Events ────────────────────────────────────────

    def on_retriever_start(
        self,
        serialized: dict[str, Any],
        query: str,
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or uuid.uuid4())
        self._run_starts[rid] = time.time()
        self._emit({
            "type": "retriever_start",
            "run_id": rid,
            "query": query[:500],
        })

    def on_retriever_end(
        self,
        documents: Sequence[Any],
        *,
        run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or "")
        duration = time.time() - self._run_starts.pop(rid, time.time())
        self._emit({
            "type": "retriever_end",
            "run_id": rid,
            "duration_ms": round(duration * 1000),
            "document_count": len(documents),
        })

    # ── Lifecycle ───────────────────────────────────────────────

    def flush(self) -> None:
        """Manually flush any buffered events."""
        self._flush()

    def close(self) -> None:
        """Flush remaining events and close the HTTP client."""
        self._flush()
        self._http.close()

    def __del__(self) -> None:
        try:
            self._flush()
            self._http.close()
        except Exception:
            pass
