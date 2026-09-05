"""Release-blocking registration controls and acceptance persistence."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import limiter as registration_limiter
from app.core.config import settings
from app.models.audit import AuditLog
from app.models.user import Organization, User

REGISTER_URL = "/api/v1/auth/register"
UNAVAILABLE_DETAIL = "Registration is not available"


@pytest.fixture(autouse=True)
def _reset_registration_rate_limit() -> None:
    registration_limiter.reset()


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "email": "evaluation@example.com",
        "password": "StrongPass1!xx",
        "full_name": "Evaluation User",
        "org_name": "Evaluation Org",
        "controlled_evaluation_accepted": True,
    }
    payload.update(overrides)
    return payload


def _registration_settings(
    monkeypatch: pytest.MonkeyPatch,
    *,
    enabled: bool,
    environment: str = "production",
    access_code: str = "",
    local_bypass: bool = False,
) -> None:
    monkeypatch.setitem(settings.__dict__, "REGISTRATION_ENABLED", enabled)
    monkeypatch.setitem(settings.__dict__, "ENVIRONMENT", environment)
    monkeypatch.setitem(settings.__dict__, "REGISTRATION_ACCESS_CODE", access_code)
    monkeypatch.setitem(settings.__dict__, "LOCAL_REGISTRATION_BYPASS_ENABLED", local_bypass)
    monkeypatch.setitem(
        settings.__dict__,
        "CONTROLLED_EVALUATION_ACCEPTANCE_VERSION",
        "controlled-evaluation-v1",
    )


async def _row_counts(db: AsyncSession) -> tuple[int, int]:
    users = await db.scalar(select(func.count(User.id)))
    organizations = await db.scalar(select(func.count(Organization.id)))
    return int(users or 0), int(organizations or 0)


@pytest.mark.parametrize(
    ("accepted", "include_field"),
    [(False, True), (False, False)],
)
async def test_registration_requires_literal_acceptance_without_mutation(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    accepted: bool,
    include_field: bool,
) -> None:
    _registration_settings(monkeypatch, enabled=True, access_code="operator-code")
    payload = _payload(access_code="operator-code")
    if include_field:
        payload["controlled_evaluation_accepted"] = accepted
    else:
        payload.pop("controlled_evaluation_accepted")

    response = await client.post(REGISTER_URL, json=payload)

    assert response.status_code == 422
    assert await _row_counts(db_session) == (0, 0)


async def test_registration_is_disabled_by_default_without_mutation(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _registration_settings(monkeypatch, enabled=False, access_code="operator-code")

    response = await client.post(REGISTER_URL, json=_payload(access_code="operator-code"))

    assert response.status_code == 403
    assert response.json() == {"detail": UNAVAILABLE_DETAIL}
    assert await _row_counts(db_session) == (0, 0)


@pytest.mark.parametrize("submitted_code", [None, "", "wrong-code"])
async def test_production_registration_rejects_missing_or_wrong_code_without_mutation(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    submitted_code: str | None,
) -> None:
    _registration_settings(monkeypatch, enabled=True, access_code="operator-code")
    payload = _payload()
    if submitted_code is not None:
        payload["access_code"] = submitted_code

    response = await client.post(REGISTER_URL, json=payload)

    assert response.status_code == 403
    assert response.json() == {"detail": UNAVAILABLE_DETAIL}
    assert await _row_counts(db_session) == (0, 0)


async def test_production_registration_rejects_unconfigured_code_without_mutation(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _registration_settings(monkeypatch, enabled=True, access_code="")

    response = await client.post(REGISTER_URL, json=_payload(access_code="operator-code"))

    assert response.status_code == 403
    assert response.json() == {"detail": UNAVAILABLE_DETAIL}
    assert await _row_counts(db_session) == (0, 0)


async def test_correct_code_persists_versioned_acceptance_with_user_and_org(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _registration_settings(monkeypatch, enabled=True, access_code="operator-code")

    with patch(
        "app.services.billing_service.get_or_create_stripe_customer",
        new_callable=AsyncMock,
    ) as create_stripe_customer:
        response = await client.post(REGISTER_URL, json=_payload(access_code="operator-code"))

    assert response.status_code == 201
    assert await _row_counts(db_session) == (1, 1)
    organization = await db_session.scalar(select(Organization))
    assert organization is not None
    acceptance = organization.settings["controlled_evaluation_acceptance"]
    assert acceptance["version"] == "controlled-evaluation-v1"
    assert datetime.fromisoformat(acceptance["accepted_at"]).tzinfo is not None
    create_stripe_customer.assert_not_awaited()
    audit_count = await db_session.scalar(select(func.count(AuditLog.id)).where(AuditLog.action == "auth.register"))
    assert audit_count == 1


async def test_audit_failure_rolls_back_registration_and_same_payload_can_retry(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _registration_settings(monkeypatch, enabled=True, access_code="operator-code")
    payload = _payload(access_code="operator-code")

    with patch(
        "app.api.auth.write_audit",
        new_callable=AsyncMock,
        side_effect=RuntimeError("forced audit failure"),
    ):
        with pytest.raises(RuntimeError, match="forced audit failure"):
            await client.post(REGISTER_URL, json=payload)

    assert await _row_counts(db_session) == (0, 0)
    audit_count = await db_session.scalar(select(func.count(AuditLog.id)))
    assert audit_count == 0

    retry = await client.post(REGISTER_URL, json=payload)

    assert retry.status_code == 201
    assert await _row_counts(db_session) == (1, 1)
    retry_audit_count = await db_session.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.action == "auth.register")
    )
    assert retry_audit_count == 1


async def test_local_registration_bypass_requires_both_flags(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _registration_settings(
        monkeypatch,
        enabled=True,
        environment="development",
        local_bypass=False,
    )
    denied = await client.post(REGISTER_URL, json=_payload())
    assert denied.status_code == 403
    assert denied.json() == {"detail": UNAVAILABLE_DETAIL}
    assert await _row_counts(db_session) == (0, 0)

    _registration_settings(
        monkeypatch,
        enabled=True,
        environment="development",
        local_bypass=True,
    )
    with patch(
        "app.services.billing_service.get_or_create_stripe_customer",
        new_callable=AsyncMock,
    ):
        allowed = await client.post(REGISTER_URL, json=_payload())

    assert allowed.status_code == 201
    assert await _row_counts(db_session) == (1, 1)
