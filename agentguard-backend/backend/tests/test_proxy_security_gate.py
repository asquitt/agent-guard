"""Provider credential and destination egress security gates."""

from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.exceptions import ProxyError
from app.services import proxy_service


def _endpoint(
    *,
    provider: str = "openai",
    target_url: str = "https://api.openai.com",
    config: dict[str, str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        provider=provider,
        target_url=target_url,
        config=config or {},
    )


def _provider_settings(
    monkeypatch: pytest.MonkeyPatch,
    *,
    environment: str,
    fallback_enabled: bool,
    key: str = "global-provider-key",
) -> None:
    monkeypatch.setitem(settings.__dict__, "ENVIRONMENT", environment)
    monkeypatch.setitem(
        settings.__dict__,
        "GLOBAL_PROVIDER_CREDENTIAL_FALLBACK_ENABLED",
        fallback_enabled,
    )
    monkeypatch.setitem(settings.__dict__, "OPENAI_API_KEY", key)


def test_legacy_inline_endpoint_credential_is_not_usable_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider_settings(monkeypatch, environment="production", fallback_enabled=False)

    with pytest.raises(ProxyError, match="endpoint credential"):
        proxy_service.get_upstream_api_key(
            _endpoint(config={"api_key": "legacy-provider-key"})  # type: ignore[arg-type]
        )


def test_production_blocks_global_fallback_even_when_flag_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider_settings(monkeypatch, environment="production", fallback_enabled=True)

    with pytest.raises(ProxyError, match="endpoint credential"):
        proxy_service.get_upstream_api_key(_endpoint())  # type: ignore[arg-type]


def test_development_global_fallback_requires_dedicated_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider_settings(monkeypatch, environment="development", fallback_enabled=False)
    with pytest.raises(ProxyError, match="endpoint credential"):
        proxy_service.get_upstream_api_key(_endpoint())  # type: ignore[arg-type]

    _provider_settings(monkeypatch, environment="development", fallback_enabled=True)
    assert proxy_service.get_upstream_api_key(_endpoint()) == "global-provider-key"  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "target_url",
    [
        "http://api.openai.com",
        "https://api.openai.com:444",
        "https://api.openai.com.evil.example",
        "https://api.openai.com@evil.example",
        "https://127.0.0.1",
        "https://api.openai.com/v1/../admin",
        "https://api.openai.com/%2e%2e/admin",
        "https://api.openai.com?redirect=https://evil.example",
    ],
)
def test_openai_target_allowlist_rejects_ssrf_and_path_confusion(
    target_url: str,
) -> None:
    with pytest.raises(ProxyError, match="not allowed"):
        proxy_service.validate_provider_target("openai", target_url)


def test_openai_target_and_proxy_path_allowlist_accepts_canonical_route() -> None:
    endpoint = _endpoint(config={"api_key": "endpoint-provider-key"})

    assert (
        proxy_service.build_target_url(endpoint, "/v1/chat/completions")  # type: ignore[arg-type]
        == "https://api.openai.com/v1/chat/completions"
    )


def test_openai_target_rejects_unapproved_outbound_path() -> None:
    endpoint = _endpoint(config={"api_key": "endpoint-provider-key"})

    with pytest.raises(ProxyError, match="path is not allowed"):
        proxy_service.build_target_url(endpoint, "/admin")  # type: ignore[arg-type]
