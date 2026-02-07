"""Base detector protocols."""

from __future__ import annotations

from typing import Protocol

from app.services.detection.types import DetectionResult


class SyncDetector(Protocol):
    """Protocol for detectors that run inline before response delivery.

    Used for PII and compliance detectors that can block/redact.
    """

    category: str

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
    ) -> DetectionResult: ...


class AsyncDetector(Protocol):
    """Protocol for detectors that run in Celery after response delivery.

    Used for hallucination, cost anomaly, and loop detectors.
    """

    category: str

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
        org_id: str,
        proxy_request_id: str,
    ) -> DetectionResult: ...
