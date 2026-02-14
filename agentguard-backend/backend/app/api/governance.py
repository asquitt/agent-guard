"""Governance API router — OWASP, MITRE ATLAS, cross-framework, DORA, EU AI Act."""

# pyright: reportGeneralTypeIssues=false, reportArgumentType=false, reportCallIssue=false

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db
from app.models.user import Organization

router = APIRouter()


# ---------------------------------------------------------------------------
# OWASP Compliance (Feature 5)
# ---------------------------------------------------------------------------


class OWASPRisk(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    description: str
    coverage: str  # "full" | "partial" | "none"
    mapped_categories: list[str] = Field(serialization_alias="mappedCategories")
    incidents_detected: int = Field(serialization_alias="incidentsDetected")
    incidents_resolved: int = Field(serialization_alias="incidentsResolved")
    active_incidents: int = Field(serialization_alias="activeIncidents")


class OWASPComplianceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    risks: list[OWASPRisk]
    coverage_percentage: float = Field(serialization_alias="coveragePercentage")
    covered_risks: int = Field(serialization_alias="coveredRisks")
    total_risks: int = Field(serialization_alias="totalRisks")
    period_days: int = Field(serialization_alias="periodDays")


@router.get("/owasp-compliance", response_model=OWASPComplianceResponse)
async def get_owasp_compliance(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> OWASPComplianceResponse:
    """Get OWASP Top 10 for LLM Applications compliance status."""
    from app.services import owasp_service

    data = await owasp_service.get_owasp_compliance(db, UUID(str(org.id)), days)
    return OWASPComplianceResponse(
        risks=[OWASPRisk(**r) for r in data["risks"]],
        coverage_percentage=data["coverage_percentage"],
        covered_risks=data["covered_risks"],
        total_risks=data["total_risks"],
        period_days=data["period_days"],
    )


# ---------------------------------------------------------------------------
# MITRE ATLAS Threat Mapping (Feature 13)
# ---------------------------------------------------------------------------


class ATLASTechnique(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    tactic: str
    description: str
    coverage: str  # "full" | "partial" | "none"
    mapped_categories: list[str] = Field(serialization_alias="mappedCategories")
    incidents_detected: int = Field(serialization_alias="incidentsDetected")
    severity_breakdown: dict[str, int] = Field(serialization_alias="severityBreakdown")


class ThreatMappingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    techniques: list[ATLASTechnique]
    coverage_percentage: float = Field(serialization_alias="coveragePercentage")
    total_techniques: int = Field(serialization_alias="totalTechniques")
    covered_techniques: int = Field(serialization_alias="coveredTechniques")
    period_days: int = Field(serialization_alias="periodDays")


@router.get("/threat-mapping", response_model=ThreatMappingResponse)
async def get_threat_mapping(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ThreatMappingResponse:
    """Get MITRE ATLAS threat technique mapping with incident counts."""
    from app.services import mitre_atlas_service

    data = await mitre_atlas_service.get_threat_mapping(db, UUID(str(org.id)), days)
    return ThreatMappingResponse(
        techniques=[ATLASTechnique(**t) for t in data["techniques"]],
        coverage_percentage=data["coverage_percentage"],
        total_techniques=data["total_techniques"],
        covered_techniques=data["covered_techniques"],
        period_days=data["period_days"],
    )


# ---------------------------------------------------------------------------
# Cross-Framework Compliance (Features 11, 14, 15)
# ---------------------------------------------------------------------------


class FrameworkRequirement(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    framework: str
    requirement_id: str = Field(serialization_alias="requirementId")
    requirement_name: str = Field(serialization_alias="requirementName")
    status: str  # "compliant" | "partial" | "non_compliant"
    mapped_categories: list[str] = Field(serialization_alias="mappedCategories")
    violations: int
    last_violation: str | None = Field(default=None, serialization_alias="lastViolation")


class ComplianceMatrixResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    requirements: list[FrameworkRequirement]
    overall_compliance: float = Field(serialization_alias="overallCompliance")
    frameworks_assessed: int = Field(serialization_alias="frameworksAssessed")
    period_days: int = Field(serialization_alias="periodDays")


@router.get("/compliance-matrix", response_model=ComplianceMatrixResponse)
async def get_compliance_matrix(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ComplianceMatrixResponse:
    """Get full cross-framework compliance matrix (SOX, PCI-DSS, EU AI Act, DORA)."""
    from app.services import compliance_framework_service

    data = await compliance_framework_service.get_compliance_matrix(
        db, UUID(str(org.id)), days
    )
    return ComplianceMatrixResponse(
        requirements=[FrameworkRequirement(**r) for r in data["requirements"]],
        overall_compliance=data["overall_compliance"],
        frameworks_assessed=data["frameworks_assessed"],
        period_days=data["period_days"],
    )


class FrameworkSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    framework: str
    display_name: str = Field(serialization_alias="displayName")
    total_requirements: int = Field(serialization_alias="totalRequirements")
    compliant: int
    partial: int
    non_compliant: int = Field(serialization_alias="nonCompliant")
    compliance_percentage: float = Field(serialization_alias="compliancePercentage")
    total_violations: int = Field(serialization_alias="totalViolations")


class FrameworkSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    frameworks: list[FrameworkSummary]
    overall_compliance: float = Field(serialization_alias="overallCompliance")
    period_days: int = Field(serialization_alias="periodDays")


@router.get("/framework-summary", response_model=FrameworkSummaryResponse)
async def get_framework_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> FrameworkSummaryResponse:
    """Get per-framework violation summary."""
    from app.services import compliance_framework_service

    data = await compliance_framework_service.get_framework_summary(
        db, UUID(str(org.id)), days
    )
    return FrameworkSummaryResponse(
        frameworks=[FrameworkSummary(**f) for f in data["frameworks"]],
        overall_compliance=data["overall_compliance"],
        period_days=data["period_days"],
    )


# ---------------------------------------------------------------------------
# Enforcement Timeline
# ---------------------------------------------------------------------------


class EnforcementDeadline(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    framework: str
    milestone: str
    date: str
    description: str
    impact: str  # "high" | "medium" | "low"
    status: str  # "upcoming" | "active" | "passed"


class EnforcementTimelineResponse(BaseModel):
    deadlines: list[EnforcementDeadline]


@router.get("/enforcement-timeline", response_model=EnforcementTimelineResponse)
async def get_enforcement_timeline(
    org: Organization = Depends(get_current_org),
) -> EnforcementTimelineResponse:
    """Get upcoming regulatory enforcement deadlines."""
    from app.services import compliance_framework_service

    data = compliance_framework_service.get_enforcement_timeline()
    return EnforcementTimelineResponse(
        deadlines=[EnforcementDeadline(**d) for d in data["deadlines"]],
    )


# ---------------------------------------------------------------------------
# DORA Incident Reporting (Digital Operational Resilience Act)
# ---------------------------------------------------------------------------


class DORATimelineStatus(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    initial_24h: str = Field(serialization_alias="initial24h")
    intermediate_72h: str = Field(serialization_alias="intermediate72h")
    final_1m: str = Field(serialization_alias="final1m")


class DORAClassification(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    incident_id: str = Field(serialization_alias="incidentId")
    title: str
    severity: str
    category: str
    classification: str  # "major" | "non_major"
    reasons: list[str]
    timeline: DORATimelineStatus | None = None
    created_at: str = Field(serialization_alias="createdAt")


class DORAMajorIncident(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    incident_id: str = Field(serialization_alias="incidentId")
    title: str
    severity: str
    category: str
    status: str
    classification: str
    reasons: list[str]
    timeline: DORATimelineStatus
    created_at: str = Field(serialization_alias="createdAt")


class DORATimelineBuckets(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    initial_24h: int = Field(serialization_alias="initial24h")
    intermediate_72h: int = Field(serialization_alias="intermediate72h")
    final_1m: int = Field(serialization_alias="final1m")


class DORAReportResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_incidents: int = Field(serialization_alias="totalIncidents")
    major_incidents: int = Field(serialization_alias="majorIncidents")
    non_major_incidents: int = Field(serialization_alias="nonMajorIncidents")
    by_timeline: DORATimelineBuckets = Field(serialization_alias="byTimeline")
    major_incidents_list: list[DORAMajorIncident] = Field(
        serialization_alias="majorIncidentsList"
    )
    period_days: int = Field(serialization_alias="periodDays")


class DORAIncidentTimeline(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    incident_id: str = Field(serialization_alias="incidentId")
    title: str | None = None
    classification: str
    message: str | None = None
    timeline: DORATimelineStatus | None = None
    reasons: list[str] | None = None
    created_at: str | None = Field(default=None, serialization_alias="createdAt")


@router.get("/dora-report", response_model=DORAReportResponse)
async def get_dora_report(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> DORAReportResponse:
    """Get DORA incident summary with Major/Non-Major classification."""
    from app.services import dora_service

    data = await dora_service.get_dora_report(db, UUID(str(org.id)), days)
    return DORAReportResponse(
        total_incidents=data["total_incidents"],
        major_incidents=data["major_incidents"],
        non_major_incidents=data["non_major_incidents"],
        by_timeline=DORATimelineBuckets(**data["by_timeline"]),
        major_incidents_list=[
            DORAMajorIncident(**m) for m in data["major_incidents_list"]
        ],
        period_days=data["period_days"],
    )


@router.get("/dora-classify/{incident_id}", response_model=DORAClassification)
async def classify_dora_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> DORAClassification:
    """Classify a single incident per DORA Major/Non-Major criteria."""
    from app.services import dora_service

    try:
        data = await dora_service.classify_incident(
            db, UUID(str(org.id)), incident_id
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Incident not found")
    return DORAClassification(**data)


@router.get(
    "/dora-timeline/{incident_id}", response_model=DORAIncidentTimeline
)
async def get_dora_timeline(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> DORAIncidentTimeline:
    """Get DORA reporting timeline status for a single incident."""
    from app.services import dora_service

    try:
        data = await dora_service.get_incident_timeline(
            db, UUID(str(org.id)), incident_id
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Incident not found")
    return DORAIncidentTimeline(**data)


# ---------------------------------------------------------------------------
# EU AI Act Article 12 Compliance Logging
# ---------------------------------------------------------------------------


class Article12LogEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    timestamp: str | None
    interaction_id: str = Field(serialization_alias="interactionId")
    model_identifier: str = Field(serialization_alias="modelIdentifier")
    input_summary: str = Field(serialization_alias="inputSummary")
    output_summary: str = Field(serialization_alias="outputSummary")
    risk_classification: str = Field(serialization_alias="riskClassification")
    human_oversight_status: str = Field(serialization_alias="humanOversightStatus")
    decision_traceability: list[str] = Field(
        serialization_alias="decisionTraceability",
    )
    data_retention_compliant: bool = Field(
        serialization_alias="dataRetentionCompliant",
    )


class Article12LogsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    logs: list[Article12LogEntry]
    total: int
    skip: int
    limit: int


class Article12SummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_interactions: int = Field(serialization_alias="totalInteractions")
    models_used: int = Field(serialization_alias="modelsUsed")
    model_names: list[str] = Field(serialization_alias="modelNames")
    high_risk_classifications: int = Field(
        serialization_alias="highRiskClassifications",
    )
    human_oversight_events: int = Field(
        serialization_alias="humanOversightEvents",
    )
    data_retention_compliant: bool = Field(
        serialization_alias="dataRetentionCompliant",
    )
    retention_days_configured: int | None = Field(
        serialization_alias="retentionDaysConfigured",
    )
    retention_days_required: int = Field(
        serialization_alias="retentionDaysRequired",
    )
    period_days: int = Field(serialization_alias="periodDays")


@router.get("/article12-logs", response_model=Article12LogsResponse)
async def get_article12_logs(
    days: int = Query(default=30, ge=1, le=365),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> Article12LogsResponse:
    """Get EU AI Act Article 12 compliance logs for LLM interactions."""
    from app.services import eu_ai_act_service

    date_to = datetime.now(timezone.utc)
    date_from = date_to - timedelta(days=days)
    data = await eu_ai_act_service.get_article12_logs(
        db, UUID(str(org.id)), date_from, date_to, skip, limit,
    )
    return Article12LogsResponse(
        logs=[Article12LogEntry(**entry) for entry in data["logs"]],
        total=data["total"],
        skip=data["skip"],
        limit=data["limit"],
    )


@router.get("/article12-summary", response_model=Article12SummaryResponse)
async def get_article12_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> Article12SummaryResponse:
    """Get EU AI Act Article 12 compliance summary statistics."""
    from app.services import eu_ai_act_service

    data = await eu_ai_act_service.get_article12_summary(
        db, UUID(str(org.id)), days,
    )
    return Article12SummaryResponse(**data)
