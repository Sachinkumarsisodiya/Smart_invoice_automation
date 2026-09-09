from celery import Celery
from celery.schedules import crontab
from app.config import settings

# Initialize Celery Application
celery_app = Celery(
    "smartinvoice",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.invoice_tasks"]
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes maximum
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
)

# Celery Beat Periodic Automation Schedule
celery_app.conf.beat_schedule = {
    # 1. Daily Overdue Invoice Check at 00:05 UTC
    "check-overdue-invoices-daily": {
        "task": "app.tasks.invoice_tasks.check_overdue_invoices_task",
        "schedule": crontab(hour=0, minute=5),
        "options": {"expires": 3600},
    },
    # 2. Daily Payment Reminders Dispatch at 08:00 UTC
    "send-payment-reminders-daily": {
        "task": "app.tasks.invoice_tasks.send_payment_reminders_task",
        "schedule": crontab(hour=8, minute=0),
        "options": {"expires": 3600},
    },
    # 3. Fetch Invoices from Email every 15 minutes
    "fetch-invoices-from-email-every-15m": {
        "task": "app.tasks.invoice_tasks.fetch_invoices_from_email_task",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 600},
    },
}

