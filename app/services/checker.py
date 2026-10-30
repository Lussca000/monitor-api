from time import perf_counter

import httpx

from app.db.models import Monitor
from app.schemas.monitor import MonitorCheckResult


def check_monitor(monitor: Monitor) -> MonitorCheckResult:
    started_at = perf_counter()

    try:
        response = httpx.request(
            method=monitor.method,
            url=monitor.url,
            timeout=monitor.timeout_seconds,
            follow_redirects=True,
        )
    except httpx.TimeoutException as error:
        return MonitorCheckResult(
            status_code=None,
            response_time_ms=round((perf_counter() - started_at) * 1000, 2),
            success=False,
            error_type="TIMEOUT",
            error_message=str(error),
        )
    except httpx.RequestError as error:
        return MonitorCheckResult(
            status_code=None,
            response_time_ms=round((perf_counter() - started_at) * 1000, 2),
            success=False,
            error_type="REQUEST_ERROR",
            error_message=str(error),
        )

    return MonitorCheckResult(
        status_code=response.status_code,
        response_time_ms=round((perf_counter() - started_at) * 1000, 2),
        success=response.status_code == monitor.expected_status_code,
    )
