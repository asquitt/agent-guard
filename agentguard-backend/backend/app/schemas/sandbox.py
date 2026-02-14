"""Pydantic schemas for sandbox execution runtime endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CapabilityType, SandboxStatus


class Capability(BaseModel):
    """A single capability grant for a sandbox."""

    type: str
    target: str = Field(max_length=512, description="Target pattern, e.g. '*.openai.com'")
    expires_at: datetime | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid = [t.value for t in CapabilityType]
        if v not in valid:
            raise ValueError(f"type must be one of: {', '.join(valid)}")
        return v


class ResourceLimits(BaseModel):
    """Resource constraints for a sandbox."""

    cpu_shares: int = Field(default=512, ge=128, le=4096)
    memory_mb: int = Field(default=256, ge=64, le=8192)
    max_tokens: int = Field(default=10000, ge=100, le=10000000)
    timeout_seconds: int = Field(default=300, ge=10, le=86400)


class NetworkPolicy(BaseModel):
    """Network egress policy for a sandbox."""

    allowed_hosts: list[str] = Field(default_factory=list)
    allowed_ports: list[int] = Field(default_factory=lambda: [443, 80])
    deny_all_egress: bool = True


class SandboxCreateRequest(BaseModel):
    """Request to create a new sandbox definition."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    agent_id: UUID | None = None
    image: str = Field(default="agentguard/sandbox-base:latest", max_length=512)
    capabilities: list[Capability] = Field(default_factory=list)
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)
    network_policy: NetworkPolicy = Field(default_factory=NetworkPolicy)
    environment: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] | None = None


class SandboxUpdateRequest(BaseModel):
    """Request to update an existing sandbox."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    agent_id: UUID | None = None
    image: str | None = Field(default=None, max_length=512)
    capabilities: list[Capability] | None = None
    resource_limits: ResourceLimits | None = None
    network_policy: NetworkPolicy | None = None
    environment: dict[str, str] | None = None
    metadata: dict[str, Any] | None = None


class SandboxResponse(BaseModel):
    """Sandbox details."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    description: str | None
    status: str
    agent_id: UUID | None = Field(serialization_alias="agentId")
    image: str
    is_active: bool = Field(serialization_alias="isActive")
    capabilities: list[dict[str, Any]]
    resource_limits: dict[str, Any] = Field(serialization_alias="resourceLimits")
    network_policy: dict[str, Any] = Field(serialization_alias="networkPolicy")
    environment: dict[str, Any]
    metadata_: dict[str, Any] = Field(alias="metadata_", serialization_alias="metadata")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class SandboxListResponse(BaseModel):
    """Paginated list of sandboxes."""

    items: list[SandboxResponse]
    total: int


class SandboxExecutionCreateRequest(BaseModel):
    """Request to start a sandbox execution."""

    trigger: str = Field(default="api", pattern="^(api|proxy|scheduled)$")


class SandboxExecutionResponse(BaseModel):
    """Sandbox execution details."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    sandbox_id: UUID = Field(serialization_alias="sandboxId")
    status: str
    container_id: str | None = Field(serialization_alias="containerId")
    started_at: datetime | None = Field(serialization_alias="startedAt")
    finished_at: datetime | None = Field(serialization_alias="finishedAt")
    exit_code: int | None = Field(serialization_alias="exitCode")
    trigger: str
    error_message: str | None = Field(serialization_alias="errorMessage")
    resource_usage: dict[str, Any] = Field(serialization_alias="resourceUsage")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class SandboxExecutionListResponse(BaseModel):
    """Paginated list of executions."""

    items: list[SandboxExecutionResponse]
    total: int


class SandboxAuditLogResponse(BaseModel):
    """Sandbox audit log entry."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    execution_id: UUID = Field(serialization_alias="executionId")
    action_type: str = Field(serialization_alias="actionType")
    action_detail: dict[str, Any] = Field(serialization_alias="actionDetail")
    allowed: bool
    capability_matched: str | None = Field(serialization_alias="capabilityMatched")
    entry_hash: str | None = Field(serialization_alias="entryHash")
    timestamp: datetime


class SandboxAuditLogListResponse(BaseModel):
    """Paginated list of audit log entries."""

    items: list[SandboxAuditLogResponse]
    total: int


class CapabilityAddRequest(BaseModel):
    """Request to add a single capability to a sandbox."""

    type: str
    target: str = Field(max_length=512, description="Target pattern, e.g. '*.openai.com'")
    expires_at: datetime | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid = [t.value for t in CapabilityType]
        if v not in valid:
            raise ValueError(f"type must be one of: {', '.join(valid)}")
        return v


class SandboxStats(BaseModel):
    """Aggregate sandbox metrics for dashboard."""

    total_sandboxes: int = Field(serialization_alias="totalSandboxes")
    active_sandboxes: int = Field(serialization_alias="activeSandboxes")
    total_executions: int = Field(serialization_alias="totalExecutions")
    running_executions: int = Field(serialization_alias="runningExecutions")
    denied_actions: int = Field(serialization_alias="deniedActions")
    total_tokens_used: int = Field(serialization_alias="totalTokensUsed")

    model_config = ConfigDict(populate_by_name=True)
