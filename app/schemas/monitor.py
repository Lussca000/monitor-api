from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MonitorBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=2048)
    method: str = Field(default="GET", min_length=1, max_length=10)
    interval_seconds: int = Field(default=60, ge=1)
    timeout_seconds: int = Field(default=5, ge=1)
    is_active: bool = True
    expected_status_code: int = Field(default=200, ge=100, le=599)


class MonitorCreate(MonitorBase):
    pass


class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    method: str | None = Field(default=None, min_length=1, max_length=10)
    interval_seconds: int | None = Field(default=None, ge=1)
    timeout_seconds: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    expected_status_code: int | None = Field(default=None, ge=100, le=599)


class MonitorResponse(MonitorBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
