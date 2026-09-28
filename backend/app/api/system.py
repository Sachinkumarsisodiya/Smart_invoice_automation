from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis

from app.config import settings
from app.database.session import get_db
from app.api.deps import get_current_user, require_admin
from app.models.user import User
from app.core.celery_app import celery_app
from app.tasks.invoice_tasks import check_overdue_invoices_task, send_payment_reminders_task
from app.core.logging import logger

router = APIRouter()


@router.get("/health")
def get_system_health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Comprehensive system health probe (Database, Redis, API, Email Mode). Zero secrets exposed."""
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    redis_status = "not_configured"
    if settings.REDIS_URL:
        try:
            r = redis.from_url(settings.REDIS_URL, socket_timeout=2)
            r.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "unreachable"

    overall_status = "healthy" if db_status == "healthy" else "degraded"

    return {
        "status": overall_status,
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": db_status,
        "redis": redis_status,
        "email_provider": settings.EMAIL_PROVIDER,
        "ai_provider": settings.AI_PROVIDER,
        "version": "1.0.0"
    }


@router.get("/celery-status")
def get_celery_status(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Inspects Celery worker configuration and periodic beat schedules."""
    beat_tasks = []
    if hasattr(celery_app.conf, "beat_schedule"):
        for name, conf in celery_app.conf.beat_schedule.items():
            beat_tasks.append({
                "name": name,
                "task": conf.get("task"),
                "schedule": str(conf.get("schedule"))
            })

    return {
        "broker_configured": bool(settings.CELERY_BROKER_URL),
        "timezone": settings.CELERY_TIMEZONE,
        "eager_mode": settings.CELERY_TASK_ALWAYS_EAGER,
        "registered_tasks": list(celery_app.tasks.keys()),
        "beat_schedule": beat_tasks
    }


@router.post("/trigger-due-date-scan")
def trigger_due_date_scan(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Manually triggers the overdue invoice scan task (Admin only)."""
    result = check_overdue_invoices_task(db=db)
    return {
        "message": "Overdue invoices scan executed successfully.",
        "details": result
    }


@router.post("/trigger-reminder-scan")
def trigger_reminder_scan(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Manually triggers the payment reminder scan task (Admin only)."""
    result = send_payment_reminders_task(db=db)
    return {
        "message": "Payment reminders scan executed successfully.",
        "details": result
    }


@router.post("/clean-database")
def clean_database_endpoint(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Wipes all dummy invoices, expenses, vendors and payments, keeping only real admin user."""
    from app.database.seed import clean_demo_data
    clean_demo_data(db)
    return {
        "status": "success",
        "message": "All demo invoices, expenses, vendors, and payments wiped. Clean workspace active."
    }
