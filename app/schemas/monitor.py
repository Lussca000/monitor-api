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


class MonitorCheckResult(BaseModel):
    status_code: int | None
    response_time_ms: float
    success: bool
    error_type: str | None = None
    error_message: str | None = None


class MonitorCheckResponse(MonitorCheckResult):
    id: int
    monitor_id: int
    checked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonitorStatsResponse(BaseModel):
    monitor_id: int
    total_checks: int
    successful_checks: int
    failed_checks: int
    uptime_percentage: float
    average_response_time_ms: float | None


class MonitorCheckListResponse(BaseModel):
    items: list[MonitorCheckResponse]
    page: int
    page_size: int
    total: int
