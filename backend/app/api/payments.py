import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentWithInvoiceResponse
from app.schemas.common import PaginatedResponse
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("", response_model=PaginatedResponse[PaymentWithInvoiceResponse])
def list_payments(
    invoice_id: Optional[uuid.UUID] = Query(None, description="Filter by invoice"),
    payment_method: Optional[str] = Query(None, description="Filter by payment method"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search by invoice number, vendor, reference or notes"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists payment transactions in chronological ledger order."""
    skip = (page - 1) * page_size
    payments, total = PaymentService.get_payments(
        db=db,
        invoice_id=invoice_id,
        payment_method=payment_method,
        start_date=start_date,
        end_date=end_date,
        search=search,
        skip=skip,
        limit=page_size
    )
    return PaginatedResponse.create(
        items=payments,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{payment_id}", response_model=PaymentWithInvoiceResponse)
def get_payment(
    payment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves payment transaction details."""
    return PaymentService.get_payment_by_id(db=db, payment_id=payment_id)


@router.post("", response_model=PaymentWithInvoiceResponse, status_code=status.HTTP_201_CREATED)
def record_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.STAFF]))
):
    """Records an atomic invoice settlement payment (Admin or Staff only)."""
    return PaymentService.record_payment(db=db, data=data, user_id=current_user.id)
