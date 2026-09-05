"""Fail-closed security rules for provider endpoint configuration and egress."""

import re
from typing import Any
from urllib.parse import urlsplit

from app.core.exceptions import ProxyError

_ENDPOINT_CONFIG_ERROR = "Proxy endpoint config supports only model_allowlist as a list of model identifiers"
_MODEL_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,254}$")

_AZURE_HOST = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.openai\.azure\.com$")
_BEDROCK_HOST = re.compile(r"^bedrock-runtime\.[a-z0-9-]+\.amazonaws\.com(?:\.cn)?$")
_AZURE_BASE_PATH = re.compile(r"^/openai/deployments/[A-Za-z0-9._-]+$")
_BEDROCK_BASE_PATH = re.compile(r"^/model/[A-Za-z0-9._:/-]+$")

_EXACT_HOSTS: dict[str, frozenset[str]] = {
    "openai": frozenset({"api.openai.com"}),
    "anthropic": frozenset({"api.anthropic.com"}),
    "google_gemini": frozenset({"generativelanguage.googleapis.com"}),
}
_ROOT_ONLY_PROVIDERS = frozenset({"openai", "anthropic", "google_gemini"})
_EXACT_OUTBOUND_PATHS: dict[str, frozenset[str]] = {
    "openai": frozenset({"/v1/chat/completions", "/v1/completions", "/v1/embeddings"}),
    "anthropic": frozenset({"/v1/messages"}),
}
_GEMINI_PATH = re.compile(r"^/v1beta/models/[A-Za-z0-9._-]+:(?:generateContent|streamGenerateContent)$")
_AZURE_PATH = re.compile(r"^/openai/deployments/[A-Za-z0-9._-]+/(?:chat/completions|completions|embeddings)$")
_BEDROCK_PATH = re.compile(
    r"^/model/[A-Za-z0-9._:/-]+/(?:invoke|invoke-with-response-stream|converse|converse-stream)$"
)


def validate_endpoint_config(config: dict[str, Any] | None) -> dict[str, list[str]]:
    """Return the only supported endpoint config shape or reject it closed."""
    if config is None or config == {}:
        return {}
    if set(config) != {"model_allowlist"}:
        raise ProxyError(_ENDPOINT_CONFIG_ERROR)

    model_allowlist = config["model_allowlist"]
    if not isinstance(model_allowlist, list) or any(
        not isinstance(model, str) or _MODEL_IDENTIFIER.fullmatch(model) is None for model in model_allowlist
    ):
        raise ProxyError(_ENDPOINT_CONFIG_ERROR)

    return {"model_allowlist": list(model_allowlist)}


def sanitize_endpoint_config(value: object) -> dict[str, list[str]]:
    """Serialize only a valid model allowlist from potentially unsafe legacy rows."""
    if not isinstance(value, dict) or "model_allowlist" not in value:
        return {}
    try:
        return validate_endpoint_config({"model_allowlist": value["model_allowlist"]})
    except ProxyError:
        return {}


def _safe_path(path: str) -> bool:
    if "%" in path or "\\" in path or "\x00" in path or path.startswith("//"):
        return False
    return all(segment not in {".", ".."} for segment in path.split("/"))


def _host_is_allowed(provider: str, hostname: str) -> bool:
    if provider in _EXACT_HOSTS:
        return hostname in _EXACT_HOSTS[provider]
    if provider == "azure_openai":
        return _AZURE_HOST.fullmatch(hostname) is not None
    if provider == "bedrock":
        return _BEDROCK_HOST.fullmatch(hostname) is not None
    return False


def validate_provider_target(provider: str, target_url: str) -> str:
    """Validate and normalize a provider-owned HTTPS base URL."""
    try:
        parsed = urlsplit(target_url)
        port = parsed.port
    except ValueError as exc:
        raise ProxyError(f"Provider target is not allowed for '{provider}'") from exc

    hostname = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path
    valid = (
        parsed.scheme == "https"
        and parsed.username is None
        and parsed.password is None
        and port in {None, 443}
        and not parsed.query
        and not parsed.fragment
        and _host_is_allowed(provider, hostname)
        and _safe_path(path)
    )
    if provider in _ROOT_ONLY_PROVIDERS:
        valid = valid and path in {"", "/"}
    elif provider == "azure_openai":
        valid = valid and (path in {"", "/"} or _AZURE_BASE_PATH.fullmatch(path) is not None)
    elif provider == "bedrock":
        valid = valid and (path in {"", "/"} or _BEDROCK_BASE_PATH.fullmatch(path) is not None)

    if not valid:
        raise ProxyError(f"Provider target is not allowed for '{provider}'")
    return target_url.rstrip("/")


def build_provider_target_url(provider: str, target_url: str, path: str) -> str:
    """Build an outbound URL only when host and final path are allowlisted."""
    base = validate_provider_target(provider, target_url)
    if not path.startswith("/") or not _safe_path(path):
        raise ProxyError(f"Provider path is not allowed for '{provider}'")

    base_path = urlsplit(base).path.rstrip("/")
    final_path = f"{base_path}{path}"
    allowed = final_path in _EXACT_OUTBOUND_PATHS.get(provider, frozenset())
    if provider == "google_gemini":
        allowed = _GEMINI_PATH.fullmatch(final_path) is not None
    elif provider == "azure_openai":
        allowed = _AZURE_PATH.fullmatch(final_path) is not None
    elif provider == "bedrock":
        allowed = _BEDROCK_PATH.fullmatch(final_path) is not None

    if not allowed:
        raise ProxyError(f"Provider path is not allowed for '{provider}'")
    return f"{base}{path}"
