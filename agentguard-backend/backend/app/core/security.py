"""Security middleware and utilities for hardening."""

import hashlib
import hmac
import os
from base64 import b64decode, b64encode

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

# ---------------------------------------------------------------------------
# AES-256-GCM field-level encryption
# ---------------------------------------------------------------------------

_NONCE_BYTES = 12  # 96-bit nonce recommended for AES-GCM


def _get_encryption_key() -> bytes:
    """Derive 32-byte AES key from ENCRYPTION_KEY setting (hex-encoded)."""
    raw = settings.ENCRYPTION_KEY
    if not raw:
        raise RuntimeError("ENCRYPTION_KEY not set — cannot encrypt/decrypt")
    return bytes.fromhex(raw)


def encrypt_field(plaintext: str) -> str:
    """Encrypt a string with AES-256-GCM. Returns base64(nonce + ciphertext + tag)."""
    key = _get_encryption_key()
    nonce = os.urandom(_NONCE_BYTES)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return b64encode(nonce + ct).decode()


def decrypt_field(token: str) -> str:
    """Decrypt a base64(nonce + ciphertext + tag) back to plaintext."""
    key = _get_encryption_key()
    raw = b64decode(token)
    nonce = raw[:_NONCE_BYTES]
    ct = raw[_NONCE_BYTES:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode()


def hmac_hash_api_key(key: str) -> str:
    """HMAC-SHA256 hash of an API key using the app secret.

    Stronger than bare SHA-256 because it's keyed — an attacker
    who steals the DB cannot brute-force keys without the secret.
    """
    return hmac.new(
        settings.SECRET_KEY.encode(),
        key.encode(),
        hashlib.sha256,
    ).hexdigest()


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add OWASP-recommended security headers to every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS filter (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy — only send origin, never path
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy — disable unnecessary browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # HSTS — enforce HTTPS (only in production)
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content-Security-Policy — API only serves JSON, no HTML rendering
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        # Prevent caching of sensitive responses
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"

        return response


# ---------------------------------------------------------------------------
# Request size limiter middleware
# ---------------------------------------------------------------------------

MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024  # 10 MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with bodies larger than MAX_REQUEST_BODY_BYTES."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            if int(content_length) > MAX_REQUEST_BODY_BYTES:
                return Response(
                    content='{"detail":"Request body too large"}',
                    status_code=413,
                    media_type="application/json",
                )
        return await call_next(request)
