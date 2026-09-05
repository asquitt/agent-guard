"""AgentGuard SDK exception hierarchy."""

from __future__ import annotations


class AgentGuardError(Exception):
    """Base exception for all AgentGuard SDK errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(AgentGuardError):
    """Raised when the API key is invalid or expired."""

    def __init__(self, message: str = "Invalid or expired API key") -> None:
        super().__init__(message, status_code=401)


class RateLimitError(AgentGuardError):
    """Raised when the request rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class DetectionBlockedError(AgentGuardError):
    """Raised when a request is blocked by a security detector."""

    def __init__(self, message: str = "Request blocked by security policy") -> None:
        super().__init__(message, status_code=403)


class CircuitOpenError(AgentGuardError):
    """Raised when the upstream provider circuit breaker is open."""

    def __init__(self, message: str = "Provider temporarily unavailable") -> None:
        super().__init__(message, status_code=503)


class ValidationError(AgentGuardError):
    """Raised when the request payload is invalid."""

    def __init__(self, message: str = "Invalid request") -> None:
        super().__init__(message, status_code=422)


def raise_for_status(response) -> None:
    """Raise the appropriate AgentGuard exception for HTTP error responses."""
    if response.status_code < 400:
        return

    body = None
    try:
        body = response.json()
        detail = body.get("detail", "") if isinstance(body, dict) else str(body)
    except Exception:
        detail = response.text[:200]

    if isinstance(detail, dict):
        error_type = detail.get("type", "")
        message = detail.get("error", str(detail))
    elif isinstance(body, dict) and isinstance(body.get("error"), dict):
        error = body["error"]
        error_type = str(error.get("type", ""))
        message = str(error.get("message", error))
    else:
        error_type = ""
        message = str(detail)

    if response.status_code == 401:
        raise AuthenticationError(message)
    if response.status_code == 403:
        if "detection" in error_type:
            raise DetectionBlockedError(message)
        raise AgentGuardError(message, status_code=403)
    if response.status_code == 422:
        raise ValidationError(message)
    if response.status_code == 429:
        retry_after = None
        if "retry_after" in response.headers:
            try:
                retry_after = int(response.headers["retry_after"])
            except (ValueError, TypeError):
                pass
        raise RateLimitError(message, retry_after=retry_after)
    if response.status_code == 503:
        if "circuit" in error_type:
            raise CircuitOpenError(message)
        raise AgentGuardError(message, status_code=503)

    raise AgentGuardError(message, status_code=response.status_code)
