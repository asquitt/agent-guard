"""Governance API router — OWASP, MITRE ATLAS, cross-framework compliance."""

# pyright: reportGeneralTypeIssues=false, reportArgumentType=false

from uuid import UUID

from fastapi import APIRouter, Depends, Query
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
