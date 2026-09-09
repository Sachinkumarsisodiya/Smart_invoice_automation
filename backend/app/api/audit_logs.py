import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.database.session import get_db
from app.api.deps import require_admin
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogResponse, AuditLogListResponse

router = APIRouter()


@router.get("", response_model=AuditLogListResponse)
def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[str] = Query(None),
    entity: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Retrieve immutable system audit logs (Admin only)."""
    query = (
        select(AuditLog, User.email.label("user_email"))
        .outerjoin(User, AuditLog.user_id == User.id)
    )

    if action:
        query = query.where(AuditLog.action == action)
    if entity:
        query = query.where(AuditLog.entity == entity)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)

    total_query = select(func.count(AuditLog.id))
    if action:
        total_query = total_query.where(AuditLog.action == action)
    if entity:
        total_query = total_query.where(AuditLog.entity == entity)
    if entity_id:
        total_query = total_query.where(AuditLog.entity_id == entity_id)

    total = db.scalar(total_query) or 0
    pages = math.ceil(total / page_size) if total > 0 else 1
    skip = (page - 1) * page_size

    rows = db.execute(
        query.order_by(desc(AuditLog.timestamp)).offset(skip).limit(page_size)
    ).all()

    items = []
    for log, email in rows:
        items.append(
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                user_email=email,
                action=log.action,
                entity=log.entity,
                entity_id=log.entity_id,
                changes=log.changes,
                ip_address=log.ip_address,
                timestamp=log.timestamp
            )
        )

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )
