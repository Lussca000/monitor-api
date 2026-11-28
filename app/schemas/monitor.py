from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


ALLOWED_HTTP_METHODS = {"DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"}


def validate_monitor_url(url: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("URL must use the HTTP or HTTPS protocol")
    return url


def normalize_http_method(method: str) -> str:
    normalized_method = method.upper()
    if normalized_method not in ALLOWED_HTTP_METHODS:
        raise ValueError(
            f"Method must be one of: {', '.join(sorted(ALLOWED_HTTP_METHODS))}"
        )
    return normalized_method


class MonitorBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=2048)
    method: str = Field(default="GET", min_length=1, max_length=10)
    interval_seconds: int = Field(default=60, ge=1)
    timeout_seconds: int = Field(default=5, ge=1)
    is_active: bool = True
    expected_status_code: int = Field(default=200, ge=100, le=599)
    webhook_url: str | None = Field(default=None, max_length=2048)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return validate_monitor_url(value)

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        return normalize_http_method(value)

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, value: str | None) -> str | None:
        return validate_monitor_url(value) if value is not None else value


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
    webhook_url: str | None = Field(default=None, max_length=2048)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        return validate_monitor_url(value) if value is not None else value

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str | None) -> str | None:
        return normalize_http_method(value) if value is not None else value

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, value: str | None) -> str | None:
        return validate_monitor_url(value) if value is not None else value


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


class MonitorListResponse(BaseModel):
    items: list[MonitorResponse]
    page: int
    page_size: int
    total: int


class MonitorCheckListResponse(BaseModel):
    items: list[MonitorCheckResponse]
    page: int
    page_size: int
    total: int
