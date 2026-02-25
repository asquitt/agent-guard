"""TOTP-based MFA service for two-factor authentication."""

from __future__ import annotations

import base64
import hashlib
import io
import secrets

import pyotp
import qrcode  # type: ignore[import-untyped]
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

APP_NAME = "AgentGuard"
BACKUP_CODE_COUNT = 10


def generate_totp_secret() -> str:
    """Generate a random base32 TOTP secret."""
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, email: str) -> str:
    """Build the otpauth:// URI for QR code scanning."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=APP_NAME)


def generate_qr_code_base64(uri: str) -> str:
    """Generate a QR code image as a base64-encoded PNG string."""
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")  # type: ignore[call-arg]
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code (allows +-1 time step for clock drift)."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_backup_codes() -> list[str]:
    """Generate a set of single-use backup codes (8-char hex strings)."""
    return [secrets.token_hex(4).upper() for _ in range(BACKUP_CODE_COUNT)]


def _hash_backup_code(code: str) -> str:
    """Hash a backup code for storage."""
    return hashlib.sha256(code.upper().encode()).hexdigest()


async def setup_totp(db: AsyncSession, user: User) -> tuple[str, str, list[str]]:
    """Begin MFA enrollment.

    Returns (secret, qr_code_base64, backup_codes).
    Does NOT enable MFA yet — call confirm_totp_setup after verification.
    """
    secret = generate_totp_secret()
    uri = get_provisioning_uri(secret, str(user.email))
    qr_b64 = generate_qr_code_base64(uri)
    backup_codes = generate_backup_codes()

    # Store secret and hashed backup codes (MFA not yet enabled)
    user.totp_secret = secret  # type: ignore[assignment]
    user.mfa_backup_codes = [_hash_backup_code(c) for c in backup_codes]  # type: ignore[assignment]
    await db.flush()

    return secret, qr_b64, backup_codes


async def confirm_totp_setup(db: AsyncSession, user: User, code: str) -> bool:
    """Verify the TOTP code and enable MFA if correct.

    Returns True on success.
    """
    secret = user.totp_secret
    if secret is None:
        return False

    if not verify_totp_code(str(secret), code):
        return False

    user.mfa_enabled = True  # type: ignore[assignment]
    await db.flush()
    return True


async def disable_mfa(db: AsyncSession, user: User) -> None:
    """Disable MFA and clear secrets."""
    user.mfa_enabled = False  # type: ignore[assignment]
    user.totp_secret = None  # type: ignore[assignment]
    user.mfa_backup_codes = None  # type: ignore[assignment]
    await db.flush()


def verify_backup_code(user: User, code: str) -> bool:
    """Check a backup code against stored hashes. Returns True on match.

    Does NOT consume the code — caller must call consume_backup_code.
    """
    stored: list[str] = user.mfa_backup_codes or []  # type: ignore[assignment]
    code_hash = _hash_backup_code(code)
    return code_hash in stored


async def consume_backup_code(db: AsyncSession, user: User, code: str) -> None:
    """Remove a used backup code from storage."""
    stored: list[str] = list(user.mfa_backup_codes or [])  # type: ignore[arg-type]
    code_hash = _hash_backup_code(code)
    if code_hash in stored:
        stored.remove(code_hash)
        user.mfa_backup_codes = stored  # type: ignore[assignment]
        await db.flush()
