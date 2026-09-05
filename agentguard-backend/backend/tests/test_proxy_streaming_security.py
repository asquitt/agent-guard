"""Focused regressions for truthful streaming proxy status and cleanup."""

from __future__ import annotations

import json
import time
import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.proxy import _handle_streaming
from app.services.providers.base import StreamChunkResult


class _StreamContext:
    """Async context double that records acquisition and deterministic release."""

    def __init__(
        self,
        response: httpx.Response | None = None,
        entry_error: Exception | None = None,
    ) -> None:
        self.response = response
        self.entry_error = entry_error
        self.enter_count = 0
        self.exit_count = 0

    async def __aenter__(self) -> httpx.Response:
        self.enter_count += 1
        if self.entry_error is not None:
            raise self.entry_error
        assert self.response is not None
        return self.response

    async def __aexit__(self, *_args: Any) -> None:
        self.exit_count += 1


def _stream_dependencies(context: _StreamContext) -> tuple[MagicMock, MagicMock, SimpleNamespace, AsyncMock]:
    client = MagicMock(spec=httpx.AsyncClient)
    client.stream = MagicMock(return_value=context)

    adapter = MagicMock()
    adapter.inject_stream_options.side_effect = lambda body: dict(body)
    adapter.build_stream_headers.return_value = {
        "Authorization": "Bearer test-provider-credential",
        "Content-Type": "application/json",
    }
    adapter.parse_stream_chunk.return_value = StreamChunkResult()

    proxy_request = SimpleNamespace(id=uuid.uuid4(), sandbox_execution_id=None)
    db = AsyncMock()
    return client, adapter, proxy_request, db


async def _consume(response: StreamingResponse) -> bytes:
    chunks: list[bytes] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.encode() if isinstance(chunk, str) else chunk)
    return b"".join(chunks)


async def test_streaming_redirect_is_outer_502_and_never_followed() -> None:
    redirect = httpx.Response(
        307,
        headers={"Location": "https://evil.example/collect"},
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )
    context = _StreamContext(response=redirect)
    client, adapter, proxy_request, db = _stream_dependencies(context)

    with patch(
        "app.api.proxy.proxy_service.update_request_log",
        new_callable=AsyncMock,
    ) as update_log:
        result = await _handle_streaming(
            client,
            "https://api.openai.com/v1/chat/completions",
            {"model": "gpt-4o", "stream": True},
            "test-provider-credential",
            adapter,
            proxy_request,
            db,
            time.time(),
            uuid.uuid4(),
        )

    assert isinstance(result, JSONResponse)
    assert result.status_code == 502
    assert json.loads(result.body)["error"]["type"] == "proxy_redirect_rejected"
    client.stream.assert_called_once()
    assert client.stream.call_args.kwargs["follow_redirects"] is False
    assert context.enter_count == 1
    assert context.exit_count == 1
    update_args = update_log.await_args
    assert update_args is not None
    assert update_args.args[2] == 502


async def test_streaming_upstream_non_200_preserves_outer_status() -> None:
    upstream = httpx.Response(
        429,
        content=b'{"error":{"message":"rate limited"}}',
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )
    context = _StreamContext(response=upstream)
    client, adapter, proxy_request, db = _stream_dependencies(context)

    with patch(
        "app.api.proxy.proxy_service.update_request_log",
        new_callable=AsyncMock,
    ) as update_log:
        result = await _handle_streaming(
            client,
            "https://api.openai.com/v1/chat/completions",
            {"model": "gpt-4o", "stream": True},
            "test-provider-credential",
            adapter,
            proxy_request,
            db,
            time.time(),
            uuid.uuid4(),
        )

        assert isinstance(result, StreamingResponse)
        assert result.status_code == 429
        assert await _consume(result) == b'{"error":{"message":"rate limited"}}'

    assert context.enter_count == 1
    assert context.exit_count == 1
    update_args = update_log.await_args
    assert update_args is not None
    assert update_args.args[2] == 429


@pytest.mark.parametrize(
    ("entry_error", "expected_status", "expected_type"),
    [
        (
            httpx.ReadTimeout(
                "sensitive timeout detail",
                request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
            ),
            504,
            "timeout_error",
        ),
        (
            httpx.ConnectError(
                "sensitive connection detail",
                request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
            ),
            502,
            "proxy_error",
        ),
    ],
)
async def test_streaming_entry_failure_is_truthful_and_generic(
    entry_error: Exception,
    expected_status: int,
    expected_type: str,
) -> None:
    context = _StreamContext(entry_error=entry_error)
    client, adapter, proxy_request, db = _stream_dependencies(context)

    with patch(
        "app.api.proxy.proxy_service.update_request_log",
        new_callable=AsyncMock,
    ) as update_log:
        result = await _handle_streaming(
            client,
            "https://api.openai.com/v1/chat/completions",
            {"model": "gpt-4o", "stream": True},
            "test-provider-credential",
            adapter,
            proxy_request,
            db,
            time.time(),
            uuid.uuid4(),
        )

    assert isinstance(result, JSONResponse)
    assert result.status_code == expected_status
    assert json.loads(result.body)["error"]["type"] == expected_type
    assert "sensitive" not in bytes(result.body).decode()
    assert context.enter_count == 1
    assert context.exit_count == 0
    update_args = update_log.await_args
    assert update_args is not None
    assert update_args.args[2] == expected_status


async def test_successful_stream_closes_and_records_once() -> None:
    upstream = httpx.Response(
        200,
        content=(b'data: {"model":"gpt-4o","choices":[{"delta":{"content":"hello"}}]}\n\n' b"data: [DONE]\n\n"),
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )
    context = _StreamContext(response=upstream)
    client, adapter, proxy_request, db = _stream_dependencies(context)

    with (
        patch(
            "app.api.proxy.proxy_service.update_request_log",
            new_callable=AsyncMock,
        ) as update_log,
        patch(
            "app.api.proxy.detection_pipeline.queue_async_detectors",
            new_callable=AsyncMock,
        ) as queue_detectors,
    ):
        result = await _handle_streaming(
            client,
            "https://api.openai.com/v1/chat/completions",
            {"model": "gpt-4o", "stream": True},
            "test-provider-credential",
            adapter,
            proxy_request,
            db,
            time.time(),
            uuid.uuid4(),
        )

        assert isinstance(result, StreamingResponse)
        assert result.status_code == 200
        body = await _consume(result)

    assert b'data: {"model":"gpt-4o"' in body
    assert context.enter_count == 1
    assert context.exit_count == 1
    update_log.assert_awaited_once()
    queue_detectors.assert_awaited_once()
