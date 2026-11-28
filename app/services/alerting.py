import logging
from datetime import datetime

import httpx

from app.db.models import Monitor
from app.schemas.monitor import MonitorCheckResult


logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 5


def _build_payload(
    event: str,
    monitor: Monitor,
    result: MonitorCheckResult,
    checked_at: datetime,
) -> dict:
    return {
        "event": event,
        "monitor_id": monitor.id,
        "monitor_name": monitor.name,
        "url": monitor.url,
        "checked_at": checked_at.isoformat(),
        "status_code": result.status_code,
        "error_type": result.error_type,
    }


def send_webhook(
    event: str,
    monitor: Monitor,
    result: MonitorCheckResult,
    checked_at: datetime,
) -> None:
    """POST the alert payload to the monitor's webhook_url.

    Failures are logged and swallowed — a webhook error must never
    interrupt the scheduler cycle.
    """
    if not monitor.webhook_url:
        return

    payload = _build_payload(event, monitor, result, checked_at)

    try:
        response = httpx.post(
            monitor.webhook_url,
            json=payload,
            timeout=WEBHOOK_TIMEOUT_SECONDS,
        )
        logger.info(
            "Webhook delivered",
            extra={
                "event": "webhook_delivered",
                "monitor_id": monitor.id,
                "webhook_event": event,
                "webhook_url": monitor.webhook_url,
                "status_code": response.status_code,
            },
        )
    except httpx.TimeoutException:
        logger.warning(
            "Webhook timed out",
            extra={
                "event": "webhook_timeout",
                "monitor_id": monitor.id,
                "webhook_event": event,
                "webhook_url": monitor.webhook_url,
            },
        )
    except httpx.RequestError as exc:
        logger.warning(
            "Webhook request failed",
            extra={
                "event": "webhook_error",
                "monitor_id": monitor.id,
                "webhook_event": event,
                "webhook_url": monitor.webhook_url,
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        )


def resolve_alert_event(previous_success: bool | None, current_success: bool) -> str | None:
    """Return the alert event name for a state transition, or None if no alert is needed.

    previous_success=None means the monitor has never been checked before.
    A first-ever failing check fires monitor.down so the user is notified immediately.
    """
    if previous_success is None:
        return "monitor.down" if not current_success else None
    if previous_success and not current_success:
        return "monitor.down"
    if not previous_success and current_success:
        return "monitor.recovered"
    return None
