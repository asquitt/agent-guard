"""Governance API — stress testing, policy classification, interpretability."""

# pyright: reportGeneralTypeIssues=false, reportArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db
from app.models.user import Organization

router = APIRouter()


# ---------------------------------------------------------------------------
# Stress Testing / Red Teaming (Feature 16)
# ---------------------------------------------------------------------------


class StressTestCase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str
    request_payload: str = Field(serialization_alias="requestPayload")
    response_payload: str = Field(serialization_alias="responsePayload")
    expected_detection: bool = Field(serialization_alias="expectedDetection")


class StressTestCategory(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    category: str
    test_cases: list[StressTestCase] = Field(serialization_alias="testCases")


class StressTestSuiteResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    categories: list[StressTestCategory]
    total_tests: int = Field(serialization_alias="totalTests")


class CategoryBreakdown(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    category: str
    detector_category: str = Field(serialization_alias="detectorCategory")
    covered: bool


class ReadinessScoreResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    score: int
    covered_categories: int = Field(serialization_alias="coveredCategories")
    total_categories: int = Field(serialization_alias="totalCategories")
    breakdown: list[CategoryBreakdown]


class StressTestRunRequest(BaseModel):
    categories: list[str]


class TestDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    expected_detection: bool = Field(serialization_alias="expectedDetection")
    actual_detection: bool = Field(serialization_alias="actualDetection")
    passed: bool
    severity: str | None = None
    action: str | None = None


class CategoryResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total: int
    passed: int
    failed: int
    details: list[TestDetail]


class StressTestRunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_tests: int = Field(serialization_alias="totalTests")
    passed: int
    failed: int
    results_by_category: dict[str, CategoryResult] = Field(
        serialization_alias="resultsByCategory"
    )


@router.get("/stress-test/suite", response_model=StressTestSuiteResponse)
async def get_stress_test_suite(
    org: Organization = Depends(get_current_org),
) -> StressTestSuiteResponse:
    """Return all available adversarial test cases."""
    from app.services import stress_test_service

    suite = stress_test_service.get_test_suite()
    categories = [
        StressTestCategory(
            category=s["category"],
            test_cases=[StressTestCase(**tc) for tc in s["test_cases"]],
        )
        for s in suite
    ]
    total = sum(len(c.test_cases) for c in categories)
    return StressTestSuiteResponse(categories=categories, total_tests=total)


@router.get("/stress-test/readiness", response_model=ReadinessScoreResponse)
async def get_readiness_score(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ReadinessScoreResponse:
    """Calculate deployment readiness score based on active detector coverage."""
    from app.services import stress_test_service

    data = await stress_test_service.get_readiness_score(db, UUID(str(org.id)))
    return ReadinessScoreResponse(
        score=data["score"],
        covered_categories=data["covered_categories"],
        total_categories=data["total_categories"],
        breakdown=[CategoryBreakdown(**b) for b in data["breakdown"]],
    )


@router.post("/stress-test/run", response_model=StressTestRunResponse)
async def run_stress_test(
    body: StressTestRunRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> StressTestRunResponse:
    """Run selected adversarial test categories through detectors."""
    from app.services import stress_test_service

    data = await stress_test_service.run_stress_test(
        db, UUID(str(org.id)), body.categories
    )
    results_by_cat = {
        cat: CategoryResult(
            total=r["total"],
            passed=r["passed"],
            failed=r["failed"],
            details=[TestDetail(**d) for d in r["details"]],
        )
        for cat, r in data["results_by_category"].items()
    }
    return StressTestRunResponse(
        total_tests=data["total_tests"],
        passed=data["passed"],
        failed=data["failed"],
        results_by_category=results_by_cat,
    )


# ---------------------------------------------------------------------------
# Interpretability-Powered Investigation (Feature 20)
# ---------------------------------------------------------------------------


class AttackChainStep(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    step: str
    description: str
    evidence: str = ""


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    root_cause: str = Field(serialization_alias="rootCause")
    contributing_factors: list[str] = Field(serialization_alias="contributingFactors")
    attack_chain: list[AttackChainStep] = Field(serialization_alias="attackChain")
    recommendations: list[str]
    similar_incidents: list[str] = Field(serialization_alias="similarIncidents")
    confidence: float


class RootCauseEntry(BaseModel):
    cause: str
    count: int


class RecurringPattern(BaseModel):
    pattern: str
    frequency: int


class InvestigationSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    top_root_causes: list[RootCauseEntry] = Field(serialization_alias="topRootCauses")
    recurring_patterns: list[RecurringPattern] = Field(
        serialization_alias="recurringPatterns"
    )
    recommended_actions: list[str] = Field(serialization_alias="recommendedActions")


@router.get("/investigations/summary", response_model=InvestigationSummaryResponse)
async def get_investigation_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> InvestigationSummaryResponse:
    """Get aggregate investigation stats over a time window."""
    from app.services import interpretability_service

    data = await interpretability_service.get_investigation_summary(
        db, UUID(str(org.id)), days
    )
    return InvestigationSummaryResponse(
        top_root_causes=[RootCauseEntry(**r) for r in data["top_root_causes"]],
        recurring_patterns=[
            RecurringPattern(**p) for p in data["recurring_patterns"]
        ],
        recommended_actions=data["recommended_actions"],
    )


@router.get("/investigations/{incident_id}", response_model=InvestigationResponse)
async def get_investigation(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> InvestigationResponse:
    """Get root-cause investigation for a specific incident."""
    from app.services import interpretability_service

    data = await interpretability_service.investigate_incident(
        db, UUID(str(org.id)), incident_id
    )
    if data["confidence"] == 0.0 and data["root_cause"] == "Incident not found":
        raise HTTPException(status_code=404, detail="Incident not found")

    return InvestigationResponse(
        root_cause=data["root_cause"],
        contributing_factors=data["contributing_factors"],
        attack_chain=[AttackChainStep(**s) for s in data["attack_chain"]],
        recommendations=data["recommendations"],
        similar_incidents=data["similar_incidents"],
        confidence=data["confidence"],
    )


# ---------------------------------------------------------------------------
# Self-Hosted Policy Classifier (Feature 18)
# ---------------------------------------------------------------------------


class PolicyInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str
    category: str
    severity: str
    action: str
    rule_count: str = Field(serialization_alias="ruleCount")


class PoliciesResponse(BaseModel):
    policies: list[PolicyInfo]


class ClassifyRequest(BaseModel):
    request_text: str = Field(default="")
    response_text: str = Field(default="")


class PolicyViolationOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    policy_name: str = Field(serialization_alias="policyName")
    severity: str
    description: str
    matched_text: str = Field(serialization_alias="matchedText")
    action: str


class ClassifyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    violations: list[PolicyViolationOut]
    total_violations: int = Field(serialization_alias="totalViolations")
    has_blocks: bool = Field(serialization_alias="hasBlocks")


class PolicyComplianceStat(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    policy_name: str = Field(serialization_alias="policyName")
    category: str
    severity: str
    violations: int
    status: str


class ComplianceStatsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    policies: list[PolicyComplianceStat]
    total_policies: int = Field(serialization_alias="totalPolicies")
    clean_policies: int = Field(serialization_alias="cleanPolicies")
    total_violations: int = Field(serialization_alias="totalViolations")
    compliance_rate: float = Field(serialization_alias="complianceRate")
    period_days: int = Field(serialization_alias="periodDays")


@router.get("/policies", response_model=PoliciesResponse)
async def get_policies(
    org: Organization = Depends(get_current_org),
) -> PoliciesResponse:
    """Return all available built-in compliance policies."""
    from app.services import policy_classifier_service

    policies = policy_classifier_service.get_available_policies()
    return PoliciesResponse(policies=[PolicyInfo(**p) for p in policies])


@router.post("/policies/classify", response_model=ClassifyResponse)
async def classify_interaction(
    body: ClassifyRequest,
    org: Organization = Depends(get_current_org),
) -> ClassifyResponse:
    """Run policy classification on an LLM request/response pair."""
    from app.services import policy_classifier_service

    violations = policy_classifier_service.classify(
        request_text=body.request_text,
        response_text=body.response_text,
    )
    return ClassifyResponse(
        violations=[
            PolicyViolationOut(
                policy_name=v.policy_name,
                severity=v.severity,
                description=v.description,
                matched_text=v.matched_text,
                action=v.action,
            )
            for v in violations
        ],
        total_violations=len(violations),
        has_blocks=any(v.action == "block" for v in violations),
    )


@router.get("/policies/compliance", response_model=ComplianceStatsResponse)
async def get_policy_compliance(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ComplianceStatsResponse:
    """Return compliance statistics across all policy categories."""
    from app.services import policy_classifier_service

    data = await policy_classifier_service.evaluate_compliance(
        db, UUID(str(org.id)), days
    )
    return ComplianceStatsResponse(
        policies=[PolicyComplianceStat(**p) for p in data["policies"]],
        total_policies=data["total_policies"],
        clean_policies=data["clean_policies"],
        total_violations=data["total_violations"],
        compliance_rate=data["compliance_rate"],
        period_days=data["period_days"],
    )
