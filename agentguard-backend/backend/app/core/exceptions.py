"""Custom exceptions for AgentGuard."""


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
