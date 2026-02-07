"""API Playground — test detectors against sample text without proxying."""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db
from app.models.user import Organization
from app.schemas.playground import (
    PlaygroundDetectionHit,
    PlaygroundTestRequest,
    PlaygroundTestResponse,
)
from app.services.detection.registry import (
    ASYNC_CATEGORIES,
    SYNC_CATEGORIES,
    get_async_detector,
    get_sync_detector,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/test", response_model=PlaygroundTestResponse)
async def test_detectors(
    body: PlaygroundTestRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> PlaygroundTestResponse:
    """Run selected detectors against sample text and return results.

    This endpoint does NOT proxy to any LLM — it only runs detectors
    against the provided request/response text.
    """
    org_id = str(org.id)
    fake_proxy_id = str(uuid4())
    results: list[PlaygroundDetectionHit] = []

    for category in body.categories:
        if category in SYNC_CATEGORIES:
            detector = get_sync_detector(category)
            result = detector.run(
                request_body=body.request_text,
                response_body=body.response_text,
                model=body.model,
                detector_config={},
            )
        elif category in ASYNC_CATEGORIES:
            detector = get_async_detector(category)
            result = detector.run(
                request_body=body.request_text,
                response_body=body.response_text,
                model=body.model,
                detector_config={},
                org_id=org_id,
                proxy_request_id=fake_proxy_id,
            )
        else:
            continue

        results.append(
            PlaygroundDetectionHit(
                detected=result.detected,
                severity=result.severity,
                category=result.category,
                action=result.action.value,
                title=result.title,
                description=result.description,
                details=result.details,
            )
        )

    return PlaygroundTestResponse(
        results=results,
        total_detections=sum(1 for r in results if r.detected),
        categories_tested=body.categories,
    )


@router.get("/categories")
async def list_categories(
    org: Organization = Depends(get_current_org),
) -> dict[str, list[str]]:
    """List available detector categories grouped by execution type."""
    return {
        "sync": sorted(SYNC_CATEGORIES),
        "async": sorted(ASYNC_CATEGORIES),
    }
