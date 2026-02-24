"""Tests for agentguard.integrations.langchain callback handler."""

import uuid
from unittest.mock import MagicMock, patch

from agentguard.integrations.langchain import AgentGuardCallbackHandler


def _make_handler(**kwargs) -> AgentGuardCallbackHandler:
    return AgentGuardCallbackHandler(api_key="ag_test_key", **kwargs)


# ── Construction ─────────────────────────────────────────────────

def test_handler_defaults():
    h = _make_handler()
    assert h.api_key == "ag_test_key"
    assert h.base_url == "https://api.agentguard.app"
    assert h.endpoint_id is None
    assert h.metadata == {}
    assert h.flush_on_chain_end is True
    assert h._chain_depth == 0
    assert len(h._events) == 0


def test_handler_custom_params():
    h = _make_handler(
        base_url="https://custom.example.com/",
        endpoint_id="ep-1",
        metadata={"env": "test"},
        flush_on_chain_end=False,
    )
    assert h.base_url == "https://custom.example.com"
    assert h.endpoint_id == "ep-1"
    assert h.metadata == {"env": "test"}
    assert h.flush_on_chain_end is False


def test_headers_include_auth():
    h = _make_handler()
    assert h._headers()["Authorization"] == "Bearer ag_test_key"


def test_headers_include_endpoint_id():
    h = _make_handler(endpoint_id="ep-2")
    assert h._headers()["X-AgentGuard-Endpoint-Id"] == "ep-2"


# ── Event emission ───────────────────────────────────────────────

def test_emit_adds_session_and_timestamp():
    h = _make_handler()
    h._emit({"type": "test_event", "data": "value"})
    assert len(h._events) == 1
    evt = h._events[0]
    assert evt["type"] == "test_event"
    assert "session_id" in evt
    assert "timestamp" in evt
    assert evt["metadata"] == {}


def test_emit_attaches_metadata():
    h = _make_handler(metadata={"env": "staging"})
    h._emit({"type": "x"})
    assert h._events[0]["metadata"] == {"env": "staging"}


# ── LLM events ───────────────────────────────────────────────────

def test_on_llm_start():
    h = _make_handler()
    rid = uuid.uuid4()
    h.on_llm_start(
        {"kwargs": {"model_name": "gpt-4"}},
        ["Hello world", "What is 2+2?"],
        run_id=rid,
    )
    assert len(h._events) == 1
    evt = h._events[0]
    assert evt["type"] == "llm_start"
    assert evt["run_id"] == str(rid)
    assert evt["model"] == "gpt-4"
    assert evt["prompt_count"] == 2
    assert str(rid) in h._run_starts


def test_on_llm_end():
    h = _make_handler()
    rid = uuid.uuid4()
    h._run_starts[str(rid)] = 1000.0
    response = MagicMock()
    response.generations = [[MagicMock(text="Generated text")]]
    response.llm_output = {"token_usage": {"total_tokens": 50}}
    h.on_llm_end(response, run_id=rid)
    evt = h._events[0]
    assert evt["type"] == "llm_end"
    assert evt["generation_count"] == 1
    assert evt["token_usage"] == {"total_tokens": 50}
    assert evt["duration_ms"] > 0


def test_on_llm_error():
    h = _make_handler()
    rid = uuid.uuid4()
    h._run_starts[str(rid)] = 1000.0
    h.on_llm_error(ValueError("boom"), run_id=rid)
    evt = h._events[0]
    assert evt["type"] == "llm_error"
    assert "boom" in evt["error"]
    assert evt["error_type"] == "ValueError"
    assert str(rid) not in h._run_starts


# ── Chat model events ────────────────────────────────────────────

def test_on_chat_model_start():
    h = _make_handler()
    msg = MagicMock()
    msg.type = "human"
    msg.content = "Hello"
    h.on_chat_model_start(
        {"kwargs": {"model_name": "gpt-4o"}},
        [[msg]],
    )
    evt = h._events[0]
    assert evt["type"] == "chat_model_start"
    assert evt["model"] == "gpt-4o"
    assert evt["message_count"] == 1
    assert evt["messages"][0]["role"] == "human"


# ── Chain events ─────────────────────────────────────────────────

def test_on_chain_start_increments_depth():
    h = _make_handler()
    h.on_chain_start({"name": "TestChain"}, {})
    assert h._chain_depth == 1
    h.on_chain_start({"name": "InnerChain"}, {})
    assert h._chain_depth == 2


def test_on_chain_end_decrements_depth():
    h = _make_handler()
    h._chain_depth = 2
    rid = uuid.uuid4()
    h._run_starts[str(rid)] = 1000.0
    h.on_chain_end({}, run_id=rid)
    assert h._chain_depth == 1


@patch.object(AgentGuardCallbackHandler, "_flush")
def test_chain_end_flushes_at_depth_zero(mock_flush):
    h = _make_handler()
    h._chain_depth = 1
    rid = uuid.uuid4()
    h._run_starts[str(rid)] = 1000.0
    h.on_chain_end({}, run_id=rid)
    assert h._chain_depth == 0
    mock_flush.assert_called_once()


@patch.object(AgentGuardCallbackHandler, "_flush")
def test_chain_end_no_flush_when_disabled(mock_flush):
    h = _make_handler(flush_on_chain_end=False)
    h._chain_depth = 1
    rid = uuid.uuid4()
    h._run_starts[str(rid)] = 1000.0
    h.on_chain_end({}, run_id=rid)
    mock_flush.assert_not_called()


@patch.object(AgentGuardCallbackHandler, "_flush")
def test_chain_error_flushes(mock_flush):
    h = _make_handler()
    h._chain_depth = 1
    h.on_chain_error(RuntimeError("chain broke"))
    assert h._chain_depth == 0
    mock_flush.assert_called_once()


# ── Tool events ──────────────────────────────────────────────────

def test_on_tool_start():
    h = _make_handler()
    h.on_tool_start({"name": "search_tool"}, "query=test")
    evt = h._events[0]
    assert evt["type"] == "tool_start"
    assert evt["tool_name"] == "search_tool"
    assert evt["input"] == "query=test"


def test_on_tool_end():
    h = _make_handler()
    rid = uuid.uuid4()
    h._run_starts[str(rid)] = 1000.0
    h.on_tool_end("result data", run_id=rid)
    evt = h._events[0]
    assert evt["type"] == "tool_end"
    assert evt["output"] == "result data"


def test_on_tool_error():
    h = _make_handler()
    h.on_tool_error(TimeoutError("timed out"))
    evt = h._events[0]
    assert evt["type"] == "tool_error"
    assert evt["error_type"] == "TimeoutError"


# ── Agent events ─────────────────────────────────────────────────

def test_on_agent_action():
    h = _make_handler()
    action = MagicMock()
    action.tool = "calculator"
    action.tool_input = "2+2"
    action.log = "Using calculator"
    h.on_agent_action(action)
    evt = h._events[0]
    assert evt["type"] == "agent_action"
    assert evt["tool"] == "calculator"


@patch.object(AgentGuardCallbackHandler, "_flush")
def test_on_agent_finish_flushes(mock_flush):
    h = _make_handler()
    finish = MagicMock()
    finish.return_values = {"output": "4"}
    h.on_agent_finish(finish)
    assert h._events[0]["type"] == "agent_finish"
    mock_flush.assert_called_once()


# ── Retriever events ─────────────────────────────────────────────

def test_on_retriever_start():
    h = _make_handler()
    h.on_retriever_start({}, "search query")
    evt = h._events[0]
    assert evt["type"] == "retriever_start"
    assert evt["query"] == "search query"


def test_on_retriever_end():
    h = _make_handler()
    rid = uuid.uuid4()
    h._run_starts[str(rid)] = 1000.0
    h.on_retriever_end([MagicMock(), MagicMock()], run_id=rid)
    evt = h._events[0]
    assert evt["type"] == "retriever_end"
    assert evt["document_count"] == 2


# ── Flush / close ────────────────────────────────────────────────

def test_flush_empty_noop():
    h = _make_handler()
    h._flush()  # should not raise


@patch("httpx.Client.post")
def test_flush_sends_batch(mock_post):
    h = _make_handler()
    h._emit({"type": "a"})
    h._emit({"type": "b"})
    h._flush()
    assert len(h._events) == 0
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert "/api/v1/ingest/events" in call_kwargs.args[0]
    batch = call_kwargs.kwargs["json"]["events"]
    assert len(batch) == 2


@patch("httpx.Client.post", side_effect=ConnectionError("offline"))
def test_flush_swallows_errors(mock_post):
    h = _make_handler()
    h._emit({"type": "a"})
    h._flush()  # should not raise
    assert len(h._events) == 0


def test_close():
    h = _make_handler()
    h._emit({"type": "test"})
    with patch.object(h, "_flush") as mock_flush, patch.object(h._http, "close") as mock_close:
        h.close()
        mock_flush.assert_called_once()
        mock_close.assert_called_once()


# ── Truncation ───────────────────────────────────────────────────

def test_prompt_truncated_to_500():
    h = _make_handler()
    long_prompt = "x" * 1000
    h.on_llm_start({"kwargs": {}}, [long_prompt])
    assert len(h._events[0]["prompts"][0]) == 500


def test_error_truncated_to_500():
    h = _make_handler()
    long_error = "e" * 1000
    h.on_llm_error(ValueError(long_error))
    assert len(h._events[0]["error"]) == 500
