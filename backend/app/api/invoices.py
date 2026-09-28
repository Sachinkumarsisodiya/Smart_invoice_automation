import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, status, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user, require_staff_or_admin, require_admin
from app.models.user import User
from app.schemas.invoice import (
    InvoiceResponse,
    InvoiceDetailResponse,
    InvoiceUpdate,
    InvoiceUploadResponse
)
from app.schemas.common import PaginatedResponse
from app.services.invoice_service import InvoiceService
from app.services.extraction_service import ExtractionService
from app.services.email_ingestion_service import EmailIngestionService
from app.models.invoice import InvoiceStatus
from app.models.audit_log import AuditAction
from app.services.audit_service import AuditService
from app.core.exceptions import NotFoundException, ForbiddenException
from app.core.rate_limiter import limiter
from app.tasks.invoice_tasks import send_manual_reminder_task
from fastapi import HTTPException

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("", response_model=PaginatedResponse[InvoiceResponse])
def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    vendor_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items, total, page, page_size, pages = InvoiceService.list_invoices(
        db=db,
        page=page,
        page_size=page_size,
        status=status,
        payment_status=payment_status,
        vendor_id=vendor_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order
    )

    return PaginatedResponse[InvoiceResponse](
        items=[InvoiceResponse.model_validate(inv) for inv in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.post("/upload", response_model=InvoiceUploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def upload_invoice(
    request: Request,
    file: UploadFile = File(...),
    vendor_id: Optional[uuid.UUID] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin)
):
    invoice, extraction_data = InvoiceService.handle_upload(
        file=file,
        db=db,
        current_user=current_user,
        vendor_id=vendor_id,
        request=request
    )

    # Immediately execute extraction pipeline (OCR/Vision AI -> Validation -> Vendor Matching)
    try:
        invoice = await ExtractionService.process_invoice_extraction(
            db=db,
            invoice_id=invoice.id,
            current_user=current_user,
            request=request
        )
    except Exception as ext_err:
        logger.warning(f"Auto-extraction during invoice upload encountered issue: {ext_err}")

    raw_data = invoice.raw_extracted_data if isinstance(invoice.raw_extracted_data, dict) else extraction_data
    raw_text = raw_data.get("text", "") if isinstance(raw_data, dict) else ""
    text_snippet = raw_text[:300]
    if len(raw_text) > 300:
        text_snippet += "..."

    return InvoiceUploadResponse(
        invoice=InvoiceDetailResponse.model_validate(invoice),
        extracted_text_snippet=text_snippet,
        char_count=len(raw_text),
        page_count=extraction_data.get("page_count", 1) if isinstance(extraction_data, dict) else 1,
        is_digital=True,
        needs_ocr=False,
        message="Invoice uploaded and processed successfully."
    )



@router.get("/{id}", response_model=InvoiceDetailResponse)
def get_invoice_detail(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = InvoiceService.get_invoice(db, id)
    return InvoiceDetailResponse.model_validate(invoice)


@router.put("/{id}", response_model=InvoiceDetailResponse)
def update_invoice(
    id: uuid.UUID,
    update_data: InvoiceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin)
):
    updated = InvoiceService.update_invoice(
        db=db,
        invoice_id=id,
        update_data=update_data,
        current_user=current_user,
        request=request
    )
    return InvoiceDetailResponse.model_validate(updated)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    InvoiceService.delete_invoice(
        db=db,
        invoice_id=id,
        current_user=current_user,
        request=request
    )
    return None


@router.post("/{id}/extract", response_model=InvoiceDetailResponse)
@limiter.limit("20/minute")
async def trigger_ai_extraction(
    id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin)
):
    """Triggers AI extraction and deterministic validation for an invoice."""
    invoice = await ExtractionService.process_invoice_extraction(
        db=db,
        invoice_id=id,
        current_user=current_user,
        request=request
    )
    return InvoiceDetailResponse.model_validate(invoice)


@router.post("/{id}/approve", response_model=InvoiceDetailResponse)
def approve_invoice(
    id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin)
):
    """Approves a reviewed invoice."""
    invoice = InvoiceService.get_invoice(db, id)
    old_status = invoice.status
    invoice.status = InvoiceStatus.APPROVED

    db.commit()
    db.refresh(invoice)

    AuditService.log_action(
        db=db,
        action=AuditAction.INVOICE_APPROVED,
        entity="INVOICE",
        entity_id=str(invoice.id),
        user_id=current_user.id,
        changes={"old_status": old_status, "new_status": InvoiceStatus.APPROVED},
        request=request
    )

    return InvoiceDetailResponse.model_validate(invoice)


@router.post("/{id}/reject", response_model=InvoiceDetailResponse)
def reject_invoice(
    id: uuid.UUID,
    request: Request,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin)
):
    """Rejects an invoice with an optional reason."""
    invoice = InvoiceService.get_invoice(db, id)
    old_status = invoice.status
    invoice.status = InvoiceStatus.REJECTED
    if reason:
        invoice.notes = f"{invoice.notes or ''} [Rejection Reason: {reason}]".strip()

    db.commit()
    db.refresh(invoice)

    AuditService.log_action(
        db=db,
        action=AuditAction.INVOICE_REJECTED,
        entity="INVOICE",
        entity_id=str(invoice.id),
        user_id=current_user.id,
        changes={"old_status": old_status, "new_status": InvoiceStatus.REJECTED, "reason": reason},
        request=request
    )

    return InvoiceDetailResponse.model_validate(invoice)


@router.get("/{id}/document")
def get_invoice_document(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Secure document streaming for authorized users."""
    invoice = InvoiceService.get_invoice(db, id)
    file_path = invoice.document_path

    if not file_path or not os.path.exists(file_path):
        raise NotFoundException("Physical document file not found on disk")

    ext = file_path.split(".")[-1].lower()
    media_type = "application/pdf" if ext == "pdf" else f"image/{ext}"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=f"invoice_{invoice.invoice_number}.{ext}",
        headers={"Content-Disposition": f"inline; filename=invoice_{invoice.invoice_number}.{ext}"}
    )


@router.post("/{id}/send-reminder")
def send_invoice_payment_reminder(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin)
):
    """Manually triggers a payment reminder for an unpaid invoice (Admin/Staff only)."""
    invoice = InvoiceService.get_invoice(db, id)
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send reminder for a fully settled invoice."
        )
    result = send_manual_reminder_task(invoice_id=str(invoice.id), sender_user_id=str(current_user.id), db=db)
    return {"message": "Payment reminder dispatched successfully", "details": result}


@router.post("/fetch-from-email")
async def fetch_invoices_from_email(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin)
):
    """Connects to the configured mailbox (e.g., sachinsisodiyaofc@gmail.com via IMAP)
    and fetches unread or recent invoice attachments into SmartInvoice.
    """
    result = await EmailIngestionService.sync_mailbox(db=db, user=current_user)
    return result


