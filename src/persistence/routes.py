from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import get_db
from .models import AuditLog, CNMCRegistry, CodeMapping
from .schemas import AuditLogResponse, CNMCResponse


router = APIRouter(
    prefix="/api",
    tags=["Tier 4 Persistence"],
)


@router.get(
    "/cnmc",
    response_model=list[CNMCResponse],
)
def get_cnmc_registry(
    cpse: str | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = (
        select(CNMCRegistry)
        .options(selectinload(CNMCRegistry.mappings))
        .order_by(CNMCRegistry.created_at.desc())
    )

    if cpse:
        query = query.where(
            CNMCRegistry.mappings.any(
                CodeMapping.source_cpse == cpse
            )
        )

    if start_date:
        query = query.where(
            CNMCRegistry.created_at >= start_date
        )

    if end_date:
        query = query.where(
            CNMCRegistry.created_at <= end_date
        )

    return db.execute(query).scalars().unique().all()


@router.get(
    "/audit-log",
    response_model=list[AuditLogResponse],
)
def get_audit_log(
    action: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = (
        select(AuditLog)
        .order_by(AuditLog.timestamp.desc())
    )

    if action:
        query = query.where(
            AuditLog.action == action
        )

    return db.execute(query).scalars().all()