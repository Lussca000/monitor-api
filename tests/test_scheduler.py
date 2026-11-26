from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Monitor, MonitorCheck
from app.schemas.monitor import MonitorCheckResult
from app.services import scheduler as scheduler_service


def test_is_check_due() -> None:
    now = datetime(2026, 1, 1, 12, 0, 0)

    assert scheduler_service.is_check_due(None, 60, now) is True
    assert scheduler_service.is_check_due(now - timedelta(seconds=60), 60, now) is True
    assert scheduler_service.is_check_due(now - timedelta(seconds=59), 60, now) is False


def test_scheduler_checks_active_monitor_once_per_interval(monkeypatch, tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'scheduler.db'}")
    testing_session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session()
    active_monitor = Monitor(
        name="Active API",
        url="https://example.com/active",
        interval_seconds=60,
    )
    inactive_monitor = Monitor(
        name="Inactive API",
        url="https://example.com/inactive",
        interval_seconds=60,
        is_active=False,
    )
    db.add_all([active_monitor, inactive_monitor])
    db.commit()

    checked_monitor_ids: list[int] = []

    def fake_check(monitor: Monitor) -> MonitorCheckResult:
        checked_monitor_ids.append(monitor.id)
        return MonitorCheckResult(
            status_code=200,
            response_time_ms=10.0,
            success=True,
        )

    monkeypatch.setattr(scheduler_service, "SessionLocal", testing_session)
    monkeypatch.setattr(scheduler_service, "check_monitor", fake_check)

    scheduler_service.run_scheduled_checks()
    scheduler_service.run_scheduled_checks()

    assert checked_monitor_ids == [active_monitor.id]
    assert db.query(MonitorCheck).count() == 1
    assert db.query(MonitorCheck).first().monitor_id == active_monitor.id

    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
