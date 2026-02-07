"""Detector registry — maps categories to detector implementations."""

from __future__ import annotations

from app.models.enums import DetectorCategory
from app.services.detection.base import AsyncDetector, SyncDetector
from app.services.detection.compliance import ComplianceDetector
from app.services.detection.cost import CostAnomalyDetector
from app.services.detection.hallucination import HallucinationDetector
from app.services.detection.loop import LoopDetector
from app.services.detection.pii import PIIDetector
from app.services.detection.types import DetectionAction, DetectionResult

# Categories that run synchronously (can block/redact)
SYNC_CATEGORIES: frozenset[str] = frozenset(
    {
        DetectorCategory.PII_LEAK.value,
        DetectorCategory.COMPLIANCE.value,
    }
)

# Categories that run asynchronously via Celery
ASYNC_CATEGORIES: frozenset[str] = frozenset(
    {
        DetectorCategory.HALLUCINATION.value,
        DetectorCategory.COST_ANOMALY.value,
        DetectorCategory.LOOP.value,
    }
)


class _StubSyncDetector:
    """Placeholder sync detector — always passes."""

    def __init__(self, category: str) -> None:
        self.category = category

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
    ) -> DetectionResult:
        return DetectionResult(
            detected=False,
            severity="info",
            category=self.category,
            detector_id=None,
            action=DetectionAction.PASS,
            title="No detection",
        )


class _StubAsyncDetector:
    """Placeholder async detector — always passes."""

    def __init__(self, category: str) -> None:
        self.category = category

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
        org_id: str,
        proxy_request_id: str,
    ) -> DetectionResult:
        return DetectionResult(
            detected=False,
            severity="info",
            category=self.category,
            detector_id=None,
            action=DetectionAction.PASS,
            title="No detection",
        )


_SYNC_REGISTRY: dict[str, SyncDetector] = {
    DetectorCategory.PII_LEAK.value: PIIDetector(),
    DetectorCategory.COMPLIANCE.value: ComplianceDetector(),
}

_ASYNC_REGISTRY: dict[str, AsyncDetector] = {
    DetectorCategory.HALLUCINATION.value: HallucinationDetector(),
    DetectorCategory.COST_ANOMALY.value: CostAnomalyDetector(),
    DetectorCategory.LOOP.value: LoopDetector(),
}


def get_sync_detector(category: str) -> SyncDetector:
    """Get sync detector implementation for a category."""
    return _SYNC_REGISTRY.get(category, _StubSyncDetector(category))


def get_async_detector(category: str) -> AsyncDetector:
    """Get async detector implementation for a category."""
    return _ASYNC_REGISTRY.get(category, _StubAsyncDetector(category))
