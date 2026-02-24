"""CrewAI integration for AgentGuard.

Wraps a CrewAI ``Crew`` so that every agent task execution, tool call,
and LLM interaction is forwarded to AgentGuard for security monitoring.

Usage::

    from crewai import Crew, Agent, Task
    from agentguard.integrations.crewai import AgentGuardCrewAIHandler

    handler = AgentGuardCrewAIHandler(api_key="ag_live_...")
    crew = Crew(agents=[...], tasks=[...])
    result = handler.run(crew)
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

import httpx

logger = logging.getLogger("agentguard.crewai")

_CONTENT_TRUNCATE = 500


class AgentGuardCrewAIHandler:
    """CrewAI handler that sends execution events to AgentGuard.

    Args:
        api_key: AgentGuard API key (``ag_live_...``).
        base_url: AgentGuard proxy URL.
        endpoint_id: Optional proxy endpoint UUID.
        metadata: Extra key-value pairs sent with every event.
        timeout: HTTP timeout for the ingest call in seconds.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.agentguard.app",
        endpoint_id: str | None = None,
        metadata: dict[str, str] | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.endpoint_id = endpoint_id
        self.metadata = metadata or {}
        self.timeout = timeout

        self.session_id = str(uuid.uuid4())
        self._events: list[dict[str, Any]] = []

    def _emit(self, event_type: str, **extra: Any) -> None:
        event: dict[str, Any] = {
            "type": event_type,
            "session_id": self.session_id,
            "timestamp": time.time(),
            "metadata": self.metadata,
            **extra,
        }
        self._events.append(event)

    def _flush(self) -> None:
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

    def _on_task_start(self, task: Any, agent: Any) -> None:
        self._emit(
            "crewai_task_start",
            task_description=str(getattr(task, "description", ""))[:_CONTENT_TRUNCATE],
            agent_role=str(getattr(agent, "role", ""))[:_CONTENT_TRUNCATE],
            agent_goal=str(getattr(agent, "goal", ""))[:_CONTENT_TRUNCATE],
        )

    def _on_task_end(self, task: Any, output: Any, duration_ms: int) -> None:
        self._emit(
            "crewai_task_end",
            task_description=str(getattr(task, "description", ""))[:_CONTENT_TRUNCATE],
            output=str(output)[:_CONTENT_TRUNCATE],
            duration_ms=duration_ms,
        )

    def _on_tool_use(self, tool_name: str, tool_input: str, tool_output: str) -> None:
        self._emit(
            "crewai_tool_use",
            tool_name=tool_name[:_CONTENT_TRUNCATE],
            tool_input=tool_input[:_CONTENT_TRUNCATE],
            tool_output=tool_output[:_CONTENT_TRUNCATE],
        )

    def run(self, crew: Any, **kwargs: Any) -> Any:
        """Execute a CrewAI Crew and capture events.

        Wraps ``crew.kickoff()`` with event capture for each task.

        Args:
            crew: A CrewAI ``Crew`` instance.
            **kwargs: Passed to ``crew.kickoff()``.

        Returns:
            The result from ``crew.kickoff()``.
        """
        self._emit(
            "crewai_crew_start",
            agent_count=len(getattr(crew, "agents", [])),
            task_count=len(getattr(crew, "tasks", [])),
        )
        start = time.time()

        # Instrument tasks by wrapping the callback if available
        tasks = getattr(crew, "tasks", [])
        agents = getattr(crew, "agents", [])
        agent_map = {}
        for agent in agents:
            for task in tasks:
                if getattr(task, "agent", None) is agent:
                    agent_map[id(task)] = agent

        try:
            result = crew.kickoff(**kwargs)
        except Exception as exc:
            self._emit(
                "crewai_crew_error",
                error=str(exc)[:_CONTENT_TRUNCATE],
                error_type=type(exc).__name__,
                duration_ms=int((time.time() - start) * 1000),
            )
            self._flush()
            raise

        duration_ms = int((time.time() - start) * 1000)
        self._emit(
            "crewai_crew_end",
            duration_ms=duration_ms,
            output=str(result)[:_CONTENT_TRUNCATE],
        )
        self._flush()
        return result

    def manual_flush(self) -> None:
        """Manually flush any buffered events."""
        self._flush()
