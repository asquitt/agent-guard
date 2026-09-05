"""Best-effort callback delivery and explicit-flush failure semantics."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agentguard.integrations.crewai import AgentGuardCrewAIHandler
from agentguard.integrations.langchain import AgentGuardCallbackHandler
from agentguard.integrations.langgraph import AgentGuardLangGraphHandler
from agentguard.integrations.llamaindex import (
    AgentGuardCallbackHandler as LlamaIndexCallbackHandler,
)

BASE = "https://guard.example.test"


class StubResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _exercise_retained_retry(
    handler,
    emit,
    explicit_flush,
    patch_sender,
    failure_status: int,
) -> None:
    emit()
    with patch_sender(StubResponse(failure_status)) as failed_post:
        with pytest.raises(RuntimeError, match=f"HTTP {failure_status}"):
            explicit_flush()
        failed_payload = failed_post.call_args.kwargs["json"]

    assert len(handler._events) == 1

    with patch_sender(StubResponse(200)) as successful_post:
        explicit_flush()
        successful_payload = successful_post.call_args.kwargs["json"]

    assert successful_payload == failed_payload
    assert handler._events == []


def test_langchain_manual_flush_retains_unauthorized_batch() -> None:
    handler = AgentGuardCallbackHandler(api_key="ag_test", base_url=BASE)
    _exercise_retained_retry(
        handler,
        lambda: handler._emit({"type": "test", "run_id": "run"}),
        handler.flush,
        lambda response: patch.object(handler._http, "post", return_value=response),
        401,
    )
    handler._http.close()


def test_llamaindex_manual_flush_retains_server_failure_batch() -> None:
    handler = LlamaIndexCallbackHandler(api_key="ag_test", base_url=BASE)
    _exercise_retained_retry(
        handler,
        lambda: handler._emit({"type": "test", "run_id": "run"}),
        handler.flush,
        lambda response: patch.object(handler._http, "post", return_value=response),
        500,
    )
    handler._http.close()


def test_langgraph_manual_flush_retains_server_failure_batch() -> None:
    handler = AgentGuardLangGraphHandler(api_key="ag_test", base_url=BASE)
    _exercise_retained_retry(
        handler,
        lambda: handler._emit("test", "run"),
        handler.manual_flush,
        lambda response: patch(
            "agentguard.integrations.langgraph.httpx.post", return_value=response
        ),
        500,
    )


def test_crewai_manual_flush_retains_unauthorized_batch() -> None:
    handler = AgentGuardCrewAIHandler(api_key="ag_test", base_url=BASE)
    _exercise_retained_retry(
        handler,
        lambda: handler._emit("test"),
        handler.manual_flush,
        lambda response: patch(
            "agentguard.integrations.crewai.httpx.post", return_value=response
        ),
        401,
    )
