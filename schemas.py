from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

class DeviceCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    name: str = Field(min_length=1, max_length=100)
    heartbeat_interval_seconds: int = Field(
        default=30,
        ge=5,
        le=3600,
        strict=True,
    )

class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    device_id: int = Field(strict=True, ge=1, le=9_223_372_036_854_775_807)
    event_type: Literal["heartbeat", "fault"]
    occurred_at: AwareDatetime

class IncidentAcknowledge(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    actor: str = Field(min_length=1, max_length=100)