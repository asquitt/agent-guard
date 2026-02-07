"""Pydantic schemas for agent behavior policies."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransactionLimit(BaseModel):
    currency: str = "USD"
    amount: float


class PolicyCreateRequest(BaseModel):
    """Create a new behavior policy for an agent."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    allowed_topics: list[str] = Field(default_factory=list)
    forbidden_topics: list[str] = Field(default_factory=list)
    max_transaction_amount: TransactionLimit | None = None
    required_disclosures: list[str] = Field(default_factory=list)
    approved_data_sources: list[str] = Field(default_factory=list)
    approved_tools: list[str] = Field(default_factory=list)
    custom_rules: list[dict[str, str]] = Field(default_factory=list)


class PolicyUpdateRequest(BaseModel):
    """Update an existing policy (creates new version)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    allowed_topics: list[str] | None = None
    forbidden_topics: list[str] | None = None
    max_transaction_amount: TransactionLimit | None = None
    required_disclosures: list[str] | None = None
    approved_data_sources: list[str] | None = None
    approved_tools: list[str] | None = None
    custom_rules: list[dict[str, str]] | None = None


class PolicyResponse(BaseModel):
    """Agent behavior policy details."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    agent_id: UUID = Field(serialization_alias="agentId")
    name: str
    description: str | None
    version: int
    allowed_topics: list[str] = Field(serialization_alias="allowedTopics")
    forbidden_topics: list[str] = Field(serialization_alias="forbiddenTopics")
    max_transaction_amount: TransactionLimit | None = Field(
        serialization_alias="maxTransactionAmount"
    )
    required_disclosures: list[str] = Field(serialization_alias="requiredDisclosures")
    approved_data_sources: list[str] = Field(serialization_alias="approvedDataSources")
    approved_tools: list[str] = Field(serialization_alias="approvedTools")
    custom_rules: list[dict[str, str]] = Field(serialization_alias="customRules")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class PolicyListResponse(BaseModel):
    """Paginated list of policies."""

    items: list[PolicyResponse]
    total: int


class PolicyTemplateResponse(BaseModel):
    """A pre-defined policy template."""

    id: str
    name: str
    description: str
    policy: PolicyCreateRequest
