"""Detection pipeline data types."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from uuid import UUID


class DetectionAction(str, enum.Enum):
    """What the pipeline should do with this detection."""

    PASS = "pass"
    MONITOR = "monitor"
    WARN = "warn"
    REDACT = "redact"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """Result from a single detector run."""

    detected: bool
    severity: str  # matches IncidentSeverity values
    category: str  # matches DetectorCategory values
    detector_id: UUID | None
    action: DetectionAction
    title: str
    description: str = ""
    details: dict[str, object] = field(default_factory=dict)
    sandbox_execution_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class PipelineDecision:
    """Aggregated decision from all sync detectors."""

    action: DetectionAction  # highest-priority action across all results
    results: list[DetectionResult]  # all individual results
    modified_response: str | None = None  # redacted body if action == REDACT


# Canonical mapping from Detector.action_mode to pipeline DetectionAction.
# Used by both sync pipeline and async Celery tasks.
def _build_action_mode_map() -> dict[str, DetectionAction]:
    from app.models.enums import ActionMode

    return {
        ActionMode.MONITOR.value: DetectionAction.MONITOR,
        ActionMode.WARN.value: DetectionAction.WARN,
        ActionMode.REDACT.value: DetectionAction.REDACT,
        ActionMode.BLOCK.value: DetectionAction.BLOCK,
    }


ACTION_MODE_MAP: dict[str, DetectionAction] = _build_action_mode_map()
