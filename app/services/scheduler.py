import logging
from datetime import datetime
from time import perf_counter

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.database import SessionLocal
from app.db.models import Monitor, MonitorCheck
from app.services.checker import check_monitor


logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def is_check_due(
    last_checked_at: datetime | None,
    interval_seconds: int,
    now: datetime | None = None,
) -> bool:
    if last_checked_at is None:
        return True

    current_time = now or datetime.now()
    return (current_time - last_checked_at).total_seconds() >= interval_seconds


def run_scheduled_checks() -> None:
    """Execute scheduled checks for all active monitors."""
    db = SessionLocal()
    start_time = perf_counter()
    
    try:
        monitors = db.query(Monitor).filter(Monitor.is_active.is_(True)).all()
        now = datetime.now()
        
        logger.info(
            "Scheduler cycle started",
            extra={
                "event": "scheduler_started",
                "total_active_monitors": len(monitors),
            }
        )
        
        checks_executed = 0
        checks_succeeded = 0
        checks_failed = 0

        for monitor in monitors:
            last_checked_at = (
                db.query(MonitorCheck.checked_at)
                .filter(MonitorCheck.monitor_id == monitor.id)
                .order_by(MonitorCheck.checked_at.desc())
                .scalar()
            )
            
            if not is_check_due(last_checked_at, monitor.interval_seconds, now):
                continue

            check_start = perf_counter()
            
            try:
                result = check_monitor(monitor)
                db.add(MonitorCheck(monitor_id=monitor.id, **result.model_dump()))
                
                checks_executed += 1
                if result.success:
                    checks_succeeded += 1
                else:
                    checks_failed += 1
                
                check_duration = round((perf_counter() - check_start) * 1000, 2)
                
                logger.info(
                    f"Monitor check completed",
                    extra={
                        "event": "monitor_check_completed",
                        "monitor_id": monitor.id,
                        "monitor_name": monitor.name,
                        "user_id": monitor.user_id,
                        "url": monitor.url,
                        "status": "success" if result.success else "failed",
                        "status_code": result.status_code,
                        "response_time_ms": result.response_time_ms,
                        "check_duration_ms": check_duration,
                        "error_type": result.error_type,
                    }
                )
                
            except Exception as e:
                checks_executed += 1
                checks_failed += 1
                
                logger.exception(
                    f"Scheduled check failed for monitor {monitor.id}",
                    extra={
                        "event": "monitor_check_error",
                        "monitor_id": monitor.id,
                        "monitor_name": monitor.name,
                        "user_id": monitor.user_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )

        db.commit()
        
        total_duration = round((perf_counter() - start_time) * 1000, 2)
        
        logger.info(
            "Scheduler cycle completed",
            extra={
                "event": "scheduler_completed",
                "total_monitors": len(monitors),
                "checks_executed": checks_executed,
                "checks_succeeded": checks_succeeded,
                "checks_failed": checks_failed,
                "duration_ms": total_duration,
            }
        )
        
    except Exception as e:
        db.rollback()
        logger.exception(
            "Scheduled monitor checks could not be completed",
            extra={
                "event": "scheduler_error",
                "error": str(e),
                "error_type": type(e).__name__,
            }
        )
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        logger.warning("Scheduler already running")
        return

    scheduler.add_job(
        run_scheduled_checks,
        trigger="interval",
        seconds=1,
        id="scheduled-monitor-checks",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    
    logger.info(
        "Scheduler started successfully",
        extra={"event": "scheduler_service_started"}
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info(
            "Scheduler stopped",
            extra={"event": "scheduler_service_stopped"}
        )
