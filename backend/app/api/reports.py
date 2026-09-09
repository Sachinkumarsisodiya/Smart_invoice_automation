import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.analytics import TaxSummaryResponse
from app.services.report_service import ReportService

router = APIRouter()


@router.get("/invoices/export")
def export_invoices_csv(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    vendor_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Download RFC 4180 CSV export of invoice records."""
    csv_content = ReportService.export_invoices_csv(
        db=db,
        start_date=start_date,
        end_date=end_date,
        vendor_id=vendor_id,
        status=status
    )
    filename = f"invoices_export_{date.today().isoformat()}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/expenses/export")
def export_expenses_csv(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Download RFC 4180 CSV export of operational expense records."""
    csv_content = ReportService.export_expenses_csv(
        db=db,
        start_date=start_date,
        end_date=end_date,
        category=category,
        payment_method=payment_method
    )
    filename = f"expenses_export_{date.today().isoformat()}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/payments/export")
def export_payments_csv(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    payment_method: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Download RFC 4180 CSV export of payment settlements."""
    csv_content = ReportService.export_payments_csv(
        db=db,
        start_date=start_date,
        end_date=end_date,
        payment_method=payment_method
    )
    filename = f"payments_export_{date.today().isoformat()}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/tax-summary", response_model=TaxSummaryResponse)
def get_tax_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve GST/Tax Input Credit breakdown grouped by vendor."""
    return ReportService.get_tax_summary(
        db=db,
        start_date=start_date,
        end_date=end_date
    )
