from pydantic import BaseModel, ConfigDict, Field


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