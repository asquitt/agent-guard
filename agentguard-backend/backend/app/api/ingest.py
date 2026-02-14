"""SDK event and trace ingest router.

Receives events from LangChain callbacks, OpenTelemetry exporters, and
other SDK integrations. Events are stored for the organization's dashboard.
"""

# pyright: reportGeneralTypeIssues=false, reportArgumentType=false

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org_from_api_key, get_db
from app.models.user import Organization

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────

class SDKEvent(BaseModel):
    type: str
    run_id: str = ""
    session_id: str = ""
    timestamp: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Flexible payload — each event type has different fields
    model: str = ""
    prompts: list[str] = Field(default_factory=list)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    generations: list[str] = Field(default_factory=list)
    token_usage: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0
    error: str = ""
    error_type: str = ""
    tool_name: str = ""
    input: str = ""
    output: str = ""
    chain_type: str = ""
    depth: int = 0
    tool: str = ""
    tool_input: str = ""
    log: str = ""
    query: str = ""
    document_count: int = 0
    prompt_count: int = 0
    generation_count: int = 0
    message_count: int = 0


class EventBatch(BaseModel):
    events: list[SDKEvent]


class TraceSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    name: str
    kind: str = "INTERNAL"
    start_time_ns: int = 0
    end_time_ns: int = 0
    status: str = "UNSET"
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)


class TraceBatch(BaseModel):
    spans: list[TraceSpan]


class IngestResponse(BaseModel):
    accepted: int
    message: str = "ok"


# ── Endpoints ───────────────────────────────────────────────────

@router.post("/events", response_model=IngestResponse)
async def ingest_events(
    batch: EventBatch,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org_from_api_key),
) -> IngestResponse:
    """Ingest SDK events (LangChain callbacks, etc).

    Events are stored in the sdk_events table for dashboard display
    and fed into the detection pipeline for anomaly analysis.
    """
    from app.models.sdk_event import SDKEventRecord

    records = []
    for evt in batch.events:
        records.append(
            SDKEventRecord(
                org_id=org.id,
                event_type=evt.type,
                run_id=evt.run_id,
                session_id=evt.session_id,
                timestamp=evt.timestamp,
                payload=evt.model_dump(exclude={"type", "run_id", "session_id", "timestamp", "metadata"}),
                metadata_=evt.metadata,
            )
        )

    db.add_all(records)
    await db.commit()

    logger.info("Ingested %d SDK events for org %s", len(records), org.id)
    return IngestResponse(accepted=len(records))


@router.post("/traces", response_model=IngestResponse)
async def ingest_traces(
    batch: TraceBatch,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org_from_api_key),
) -> IngestResponse:
    """Ingest OpenTelemetry trace spans.

    Spans are stored in the sdk_traces table and linked to the
    organization for display in the observability dashboard.
    """
    from app.models.sdk_event import SDKTraceSpan

    records = []
    for span in batch.spans:
        records.append(
            SDKTraceSpan(
                org_id=org.id,
                trace_id=span.trace_id,
                span_id=span.span_id,
                parent_span_id=span.parent_span_id,
                name=span.name,
                kind=span.kind,
                start_time_ns=span.start_time_ns,
                end_time_ns=span.end_time_ns,
                status=span.status,
                attributes=span.attributes,
                events=span.events,
            )
        )

    db.add_all(records)
    await db.commit()

    logger.info("Ingested %d trace spans for org %s", len(records), org.id)
    return IngestResponse(accepted=len(records))
