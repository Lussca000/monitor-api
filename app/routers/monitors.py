from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Monitor, MonitorCheck
from app.schemas.monitor import (
    MonitorCheckResponse,
    MonitorCheckListResponse,
    MonitorCreate,
    MonitorResponse,
    MonitorStatsResponse,
    MonitorUpdate,
)
from app.services.checker import check_monitor


router = APIRouter(prefix="/monitors", tags=["monitors"])


@router.get("", response_model=list[MonitorResponse])
def list_monitors(db: Session = Depends(get_db)) -> list[Monitor]:
    return db.query(Monitor).order_by(Monitor.id).all()


@router.get("/{monitor_id}", response_model=MonitorResponse)
def get_monitor(monitor_id: int, db: Session = Depends(get_db)) -> Monitor:
    monitor = db.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")
    return monitor


@router.post("/{monitor_id}/check", response_model=MonitorCheckResponse)
def run_monitor_check(
    monitor_id: int, db: Session = Depends(get_db)
) -> MonitorCheckResponse:
    monitor = db.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")
    result = check_monitor(monitor)
    monitor_check = MonitorCheck(
        monitor_id=monitor.id,
        **result.model_dump(),
    )
    db.add(monitor_check)
    db.commit()
    db.refresh(monitor_check)
    return monitor_check


@router.get("/{monitor_id}/checks", response_model=MonitorCheckListResponse)
def list_monitor_checks(
    monitor_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> MonitorCheckListResponse:
    if db.get(Monitor, monitor_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")

    query = db.query(MonitorCheck).filter(MonitorCheck.monitor_id == monitor_id)
    total = query.count()
    checks = (
        query
        .order_by(MonitorCheck.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return MonitorCheckListResponse(
        items=checks,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{monitor_id}/stats", response_model=MonitorStatsResponse)
def get_monitor_stats(
    monitor_id: int, db: Session = Depends(get_db)
) -> MonitorStatsResponse:
    if db.get(Monitor, monitor_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")

    checks = (
        db.query(MonitorCheck)
        .filter(MonitorCheck.monitor_id == monitor_id)
        .all()
    )
    total_checks = len(checks)
    successful_checks = sum(check.success for check in checks)
    failed_checks = total_checks - successful_checks
    average_response_time_ms = (
        round(sum(check.response_time_ms for check in checks) / total_checks, 2)
        if total_checks
        else None
    )

    return MonitorStatsResponse(
        monitor_id=monitor_id,
        total_checks=total_checks,
        successful_checks=successful_checks,
        failed_checks=failed_checks,
        uptime_percentage=round(successful_checks / total_checks * 100, 2)
        if total_checks
        else 0.0,
        average_response_time_ms=average_response_time_ms,
    )


@router.patch("/{monitor_id}", response_model=MonitorResponse)
def update_monitor(
    monitor_id: int,
    monitor_data: MonitorUpdate,
    db: Session = Depends(get_db),
) -> Monitor:
    monitor = db.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")

    for field, value in monitor_data.model_dump(exclude_unset=True).items():
        setattr(monitor, field, value)

    db.commit()
    db.refresh(monitor)
    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitor(monitor_id: int, db: Session = Depends(get_db)) -> Response:
    monitor = db.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")

    db.delete(monitor)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
def create_monitor(
    monitor_data: MonitorCreate,
    db: Session = Depends(get_db),
) -> Monitor:
    monitor = Monitor(**monitor_data.model_dump())
    db.add(monitor)
    db.commit()
    db.refresh(monitor)
    return monitor
