import uuid
from typing import Any
from fastapi import Request
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.core.logging import logger


class AuditService:
    @staticmethod
    def log_action(
        db: Session,
        action: str,
        entity: str,
        entity_id: str | uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        changes: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        request: Request | None = None,
    ) -> AuditLog:
        ip_address = None
        if request and request.client:
            ip_address = request.client.host

        payload = changes if changes is not None else details

        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id else None,
            changes=payload,
            ip_address=ip_address
        )
        db.add(audit_entry)
        try:
            db.commit()
            db.refresh(audit_entry)
            logger.info(f"Audit Log: [{action}] on {entity}:{entity_id} by user:{user_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to write audit log: {str(e)}")
        return audit_entry
