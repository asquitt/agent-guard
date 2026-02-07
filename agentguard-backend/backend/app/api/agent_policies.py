"""Agent behavior policies router — CRUD + templates for agent governance."""

# pyright: reportGeneralTypeIssues=false, reportCallIssue=false, reportArgumentType=false

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db
from app.models.agent import Agent
from app.models.agent_policy import AgentPolicy
from app.models.user import Organization
from app.schemas.agent_policies import (
    PolicyCreateRequest,
    PolicyListResponse,
    PolicyResponse,
    PolicyTemplateResponse,
    PolicyUpdateRequest,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Policy templates for common financial agent types
# ---------------------------------------------------------------------------

_TEMPLATES: list[dict[str, object]] = [
    {
        "id": "customer_service",
        "name": "Customer Service Agent",
        "description": "Policy for customer-facing support agents handling account inquiries.",
        "policy": {
            "allowed_topics": [
                "account_balance",
                "transaction_history",
                "product_info",
                "faq",
                "support_tickets",
            ],
            "forbidden_topics": [
                "investment_advice",
                "tax_advice",
                "legal_opinions",
                "competitor_comparisons",
                "internal_processes",
            ],
            "max_transaction_amount": {"currency": "USD", "amount": 500},
            "required_disclosures": [
                "I am an AI assistant and cannot provide financial advice.",
                "For account security questions, please contact our support team directly.",
            ],
            "approved_data_sources": [
                "customer_account_api",
                "product_catalog",
                "faq_database",
            ],
            "approved_tools": [
                "lookup_account",
                "search_faq",
                "create_ticket",
                "transfer_to_human",
            ],
            "custom_rules": [],
        },
    },
    {
        "id": "financial_advisor",
        "name": "Financial Advisor Agent",
        "description": "Policy for agents providing investment and financial planning guidance.",
        "policy": {
            "allowed_topics": [
                "portfolio_analysis",
                "market_data",
                "risk_assessment",
                "retirement_planning",
                "asset_allocation",
            ],
            "forbidden_topics": [
                "guaranteed_returns",
                "insider_information",
                "specific_stock_picks",
                "tax_evasion",
                "unauthorized_trading",
            ],
            "max_transaction_amount": {"currency": "USD", "amount": 50000},
            "required_disclosures": [
                "This is AI-generated guidance, not personalized financial advice.",
                "Past performance does not guarantee future results.",
                "Please consult a licensed financial advisor before making investment decisions.",
            ],
            "approved_data_sources": [
                "market_data_api",
                "portfolio_service",
                "risk_models",
                "regulatory_database",
            ],
            "approved_tools": [
                "get_market_data",
                "analyze_portfolio",
                "calculate_risk",
                "generate_report",
            ],
            "custom_rules": [
                {
                    "rule": "suitability_check",
                    "description": "Verify client risk profile before recommendations",
                },
                {
                    "rule": "reg_bi_compliance",
                    "description": "Ensure Regulation Best Interest compliance",
                },
            ],
        },
    },
    {
        "id": "trading_assistant",
        "name": "Trading Assistant Agent",
        "description": "Policy for agents assisting with trade execution and order management.",
        "policy": {
            "allowed_topics": [
                "order_placement",
                "order_status",
                "market_data",
                "position_management",
                "trade_confirmation",
            ],
            "forbidden_topics": [
                "market_manipulation",
                "front_running",
                "wash_trading",
                "insider_trading",
                "unauthorized_leverage",
            ],
            "max_transaction_amount": {"currency": "USD", "amount": 100000},
            "required_disclosures": [
                "Trading involves risk of loss.",
                "Orders are executed on a best-effort basis.",
            ],
            "approved_data_sources": [
                "order_management_system",
                "market_data_feed",
                "position_ledger",
            ],
            "approved_tools": [
                "place_order",
                "cancel_order",
                "get_positions",
                "get_order_status",
            ],
            "custom_rules": [
                {
                    "rule": "position_limit",
                    "description": "Enforce per-instrument position limits",
                },
                {
                    "rule": "pre_trade_check",
                    "description": "Run compliance checks before order submission",
                },
            ],
        },
    },
    {
        "id": "compliance_review",
        "name": "Compliance Review Agent",
        "description": "Policy for agents performing regulatory compliance reviews and monitoring.",
        "policy": {
            "allowed_topics": [
                "regulatory_requirements",
                "policy_violations",
                "audit_findings",
                "risk_assessments",
                "remediation_tracking",
            ],
            "forbidden_topics": [
                "legal_advice",
                "enforcement_predictions",
                "penalty_negotiations",
                "whistleblower_identities",
            ],
            "max_transaction_amount": None,
            "required_disclosures": [
                "This review is AI-assisted and should be validated by compliance staff.",
                "This does not constitute legal advice.",
            ],
            "approved_data_sources": [
                "regulatory_database",
                "audit_logs",
                "incident_database",
                "policy_repository",
            ],
            "approved_tools": [
                "search_regulations",
                "generate_compliance_report",
                "flag_violation",
                "assign_remediation",
            ],
            "custom_rules": [
                {
                    "rule": "human_review_required",
                    "description": "All findings must be reviewed by a human compliance officer",
                },
            ],
        },
    },
]


@router.get("/templates", response_model=list[PolicyTemplateResponse])
async def list_policy_templates() -> list[PolicyTemplateResponse]:
    """List available policy templates for common financial agent types."""
    return [PolicyTemplateResponse(**t) for t in _TEMPLATES]


@router.get("/{agent_id}/policies", response_model=PolicyListResponse)
async def list_policies(
    agent_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> PolicyListResponse:
    """List all policy versions for an agent."""
    await _get_agent_or_404(db, agent_id, org.id)

    base = select(AgentPolicy).where(
        AgentPolicy.agent_id == agent_id,
        AgentPolicy.org_id == org.id,
    )
    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar_one()

    result = await db.execute(
        base.order_by(AgentPolicy.version.desc()).offset(skip).limit(limit)
    )
    policies = result.scalars().all()

    return PolicyListResponse(
        items=[PolicyResponse.model_validate(p) for p in policies],
        total=total,
    )


@router.post(
    "/{agent_id}/policies",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_policy(
    agent_id: UUID,
    body: PolicyCreateRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> PolicyResponse:
    """Create a new behavior policy for an agent."""
    await _get_agent_or_404(db, agent_id, org.id)

    # Determine next version number
    max_ver_result = await db.execute(
        select(func.coalesce(func.max(AgentPolicy.version), 0)).where(
            AgentPolicy.agent_id == agent_id,
            AgentPolicy.org_id == org.id,
        )
    )
    next_version: int = max_ver_result.scalar_one() + 1

    policy = AgentPolicy(
        agent_id=agent_id,
        org_id=org.id,
        name=body.name,
        description=body.description,
        version=next_version,
        allowed_topics=body.allowed_topics,
        forbidden_topics=body.forbidden_topics,
        max_transaction_amount=(
            body.max_transaction_amount.model_dump()
            if body.max_transaction_amount
            else None
        ),
        required_disclosures=body.required_disclosures,
        approved_data_sources=body.approved_data_sources,
        approved_tools=body.approved_tools,
        custom_rules=body.custom_rules,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return PolicyResponse.model_validate(policy)


@router.get("/{agent_id}/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    agent_id: UUID,
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> PolicyResponse:
    """Get a single policy by ID."""
    policy = await _get_policy_or_404(db, agent_id, policy_id, org.id)
    return PolicyResponse.model_validate(policy)


@router.put(
    "/{agent_id}/policies/{policy_id}",
    response_model=PolicyResponse,
)
async def update_policy(
    agent_id: UUID,
    policy_id: UUID,
    body: PolicyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> PolicyResponse:
    """Update a policy — creates a new version with the changes applied."""
    existing = await _get_policy_or_404(db, agent_id, policy_id, org.id)

    # Determine next version
    max_ver_result = await db.execute(
        select(func.coalesce(func.max(AgentPolicy.version), 0)).where(
            AgentPolicy.agent_id == agent_id,
            AgentPolicy.org_id == org.id,
        )
    )
    next_version: int = max_ver_result.scalar_one() + 1

    update_data = body.model_dump(exclude_unset=True)

    new_policy = AgentPolicy(
        agent_id=agent_id,
        org_id=org.id,
        name=update_data.get("name", existing.name),
        description=update_data.get("description", existing.description),
        version=next_version,
        allowed_topics=update_data.get("allowed_topics", existing.allowed_topics),
        forbidden_topics=update_data.get("forbidden_topics", existing.forbidden_topics),
        max_transaction_amount=(
            update_data["max_transaction_amount"].model_dump()
            if "max_transaction_amount" in update_data and update_data["max_transaction_amount"]
            else existing.max_transaction_amount
        ),
        required_disclosures=update_data.get("required_disclosures", existing.required_disclosures),
        approved_data_sources=update_data.get("approved_data_sources", existing.approved_data_sources),
        approved_tools=update_data.get("approved_tools", existing.approved_tools),
        custom_rules=update_data.get("custom_rules", existing.custom_rules),
    )
    db.add(new_policy)
    await db.commit()
    await db.refresh(new_policy)
    return PolicyResponse.model_validate(new_policy)


@router.delete(
    "/{agent_id}/policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_policy(
    agent_id: UUID,
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> None:
    """Delete a policy version."""
    policy = await _get_policy_or_404(db, agent_id, policy_id, org.id)
    await db.delete(policy)
    await db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_agent_or_404(
    db: AsyncSession, agent_id: UUID, org_id: UUID
) -> Agent:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


async def _get_policy_or_404(
    db: AsyncSession, agent_id: UUID, policy_id: UUID, org_id: UUID
) -> AgentPolicy:
    result = await db.execute(
        select(AgentPolicy).where(
            AgentPolicy.id == policy_id,
            AgentPolicy.agent_id == agent_id,
            AgentPolicy.org_id == org_id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy
