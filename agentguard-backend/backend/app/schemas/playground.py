"""Pydantic schemas for the API playground (detector testing)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PlaygroundTestRequest(BaseModel):
    """Input for testing detectors against sample text."""

    request_text: str = Field(min_length=1, max_length=10000)
    response_text: str = Field(min_length=1, max_length=10000)
    categories: list[str] = Field(min_length=1, max_length=10)
    model: str | None = None


class PlaygroundDetectionHit(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    detected: bool
    severity: str
    category: str
    action: str
    title: str
    description: str = ""
    details: dict[str, object] = Field(default_factory=dict)


class PlaygroundTestResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    results: list[PlaygroundDetectionHit]
    total_detections: int = Field(serialization_alias="totalDetections")
    categories_tested: list[str] = Field(serialization_alias="categoriesTested")
