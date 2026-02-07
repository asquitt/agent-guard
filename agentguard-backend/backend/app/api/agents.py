"""Agent registry router — CRUD for AI agent inventory and governance."""

# pyright: reportGeneralTypeIssues=false, reportCallIssue=false

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db
from app.models.agent import Agent
from app.models.user import Organization
from app.schemas.agents import (
    AgentCreateRequest,
    AgentListResponse,
    AgentResponse,
    AgentUpdateRequest,
)

router = APIRouter()


@router.get("", response_model=AgentListResponse)
async def list_agents(
    risk_tier: str | None = Query(default=None, alias="riskTier"),
    agent_status: str | None = Query(default=None, alias="status"),
    q: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> AgentListResponse:
    """List registered agents with optional filtering."""
    base = select(Agent).where(Agent.org_id == org.id)

    if risk_tier:
        base = base.where(Agent.risk_tier == risk_tier)
    if agent_status:
        base = base.where(Agent.status == agent_status)
    if q:
        base = base.where(Agent.name.ilike(f"%{q}%"))

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar_one()

    result = await db.execute(base.order_by(Agent.created_at.desc()).offset(skip).limit(limit))
    agents = result.scalars().all()

    return AgentListResponse(
        items=[AgentResponse.model_validate(a) for a in agents],
        total=total,
    )


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreateRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> AgentResponse:
    """Register a new AI agent."""
    agent = Agent(
        org_id=org.id,
        name=body.name,
        description=body.description,
        owner=body.owner,
        risk_tier=body.risk_tier,
        status=body.status,
        provider=body.provider,
        model=body.model,
        frameworks=body.frameworks,
        tags=body.tags,
        metadata_=body.metadata or {},
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> AgentResponse:
    """Get a single agent by ID."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.org_id == org.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    body: AgentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> AgentResponse:
    """Update an existing agent."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.org_id == org.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    update_data = body.model_dump(exclude_unset=True)
    if "metadata" in update_data:
        update_data["metadata_"] = update_data.pop("metadata")
    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> None:
    """Delete an agent from the registry."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.org_id == org.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    await db.delete(agent)
    await db.commit()
