"""Pydantic schemas for cost analytics."""

from pydantic import BaseModel, ConfigDict, Field


class CostByModel(BaseModel):
    """Cost breakdown for a single model."""

    model: str
    cost: float
    requests: int
    input_tokens: int = Field(serialization_alias="inputTokens")
    output_tokens: int = Field(serialization_alias="outputTokens")


class DailyCost(BaseModel):
    """Cost data for a single day."""

    date: str
    cost: float
    requests: int
    input_tokens: int = Field(serialization_alias="inputTokens")
    output_tokens: int = Field(serialization_alias="outputTokens")


class CostAnalyticsResponse(BaseModel):
    """Aggregate cost analytics response."""

    model_config = ConfigDict(populate_by_name=True)

    total_cost: float = Field(serialization_alias="totalCost")
    total_requests: int = Field(serialization_alias="totalRequests")
    total_input_tokens: int = Field(serialization_alias="totalInputTokens")
    total_output_tokens: int = Field(serialization_alias="totalOutputTokens")
    cost_by_model: list[CostByModel] = Field(serialization_alias="costByModel")
    daily_costs: list[DailyCost] = Field(serialization_alias="dailyCosts")
    period_days: int = Field(serialization_alias="periodDays")
