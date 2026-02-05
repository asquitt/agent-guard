"""Custom exceptions for AgentGuard."""

from fastapi import HTTPException, status


class AgentGuardException(Exception):
    """Base exception for AgentGuard."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class AuthenticationError(AgentGuardException):
    """Authentication failed."""

    pass


class AuthorizationError(AgentGuardException):
    """User not authorized for this action."""

    pass


class NotFoundError(AgentGuardException):
    """Resource not found."""

    pass


class ValidationError(AgentGuardException):
    """Validation failed."""

    pass


class ProxyError(AgentGuardException):
    """LLM proxy error."""

    pass


class DetectionError(AgentGuardException):
    """Detection algorithm error."""

    pass


def raise_not_found(resource: str, resource_id: str) -> None:
    """Raise a 404 HTTPException."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} with id {resource_id} not found",
    )


def raise_forbidden(message: str = "Not authorized") -> None:
    """Raise a 403 HTTPException."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message,
    )


def raise_bad_request(message: str) -> None:
    """Raise a 400 HTTPException."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message,
    )
