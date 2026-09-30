import uuid
from decimal import Decimal
from datetime import date
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, or_
from app.models.payment import Payment, PaymentMethod
from app.models.invoice import Invoice, InvoiceStatus, PaymentStatus
from app.models.vendor import Vendor
from app.models.audit_log import AuditAction
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentWithInvoiceResponse
from app.services.audit_service import AuditService
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import logger


class PaymentService:
    @staticmethod
    def get_payments(
        db: Session,
        invoice_id: Optional[uuid.UUID] = None,
        payment_method: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[PaymentWithInvoiceResponse], int]:
        """Retrieves paginated payments with invoice and vendor context."""
        query = (
            select(Payment, Invoice, Vendor)
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .join(Vendor, Invoice.vendor_id == Vendor.id)
        )

        if invoice_id:
            query = query.where(Payment.invoice_id == invoice_id)

        if payment_method and payment_method.strip():
            query = query.where(Payment.payment_method == payment_method.strip())

        if start_date:
            query = query.where(Payment.payment_date >= start_date)

        if end_date:
            query = query.where(Payment.payment_date <= end_date)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Invoice.invoice_number.ilike(term),
                    Vendor.name.ilike(term),
                    Payment.reference_number.ilike(term),
                    Payment.notes.ilike(term)
                )
            )

        total = db.scalar(select(func.count()).select_from(query.subquery()))
        rows = db.execute(
            query.order_by(Payment.payment_date.desc(), Payment.created_at.desc()).offset(skip).limit(limit)
        ).all()

        results: List[PaymentWithInvoiceResponse] = []
        for p, inv, v in rows:
            results.append(
                PaymentWithInvoiceResponse(
                    id=p.id,
                    invoice_id=p.invoice_id,
                    amount=p.amount,
                    payment_date=p.payment_date,
                    payment_method=p.payment_method,
                    reference_number=p.reference_number,
                    notes=p.notes,
                    created_by=p.created_by,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                    invoice_number=inv.invoice_number,
                    vendor_name=v.name,
                    invoice_total=inv.total_amount,
                    invoice_remaining=inv.remaining_amount,
                    invoice_payment_status=inv.payment_status
                )
            )

        return results, total

    @staticmethod
    def get_payment_by_id(db: Session, payment_id: uuid.UUID) -> PaymentWithInvoiceResponse:
        """Retrieves single payment transaction details."""
        row = db.execute(
            select(Payment, Invoice, Vendor)
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .join(Vendor, Invoice.vendor_id == Vendor.id)
            .where(Payment.id == payment_id)
        ).first()

        if not row:
            raise NotFoundException("Payment", str(payment_id))

        p, inv, v = row
        return PaymentWithInvoiceResponse(
            id=p.id,
            invoice_id=p.invoice_id,
            amount=p.amount,
            payment_date=p.payment_date,
            payment_method=p.payment_method,
            reference_number=p.reference_number,
            notes=p.notes,
            created_by=p.created_by,
            created_at=p.created_at,
            updated_at=p.updated_at,
            invoice_number=inv.invoice_number,
            vendor_name=v.name,
            invoice_total=inv.total_amount,
            invoice_remaining=inv.remaining_amount,
            invoice_payment_status=inv.payment_status
        )

    @staticmethod
    def record_payment(db: Session, data: PaymentCreate, user_id: uuid.UUID) -> PaymentWithInvoiceResponse:
        """Executes an atomic payment settlement against an invoice."""
        if data.amount <= Decimal("0.00"):
            raise ValidationException("Payment amount must be strictly greater than 0.00")

        # Fetch invoice for update / check
        invoice = db.get(Invoice, data.invoice_id)
        if not invoice:
            raise NotFoundException("Invoice", str(data.invoice_id))

        if invoice.status == InvoiceStatus.REJECTED:
            raise ValidationException("Cannot record payment against a rejected invoice")

        if invoice.status == InvoiceStatus.PROCESSING:
            raise ValidationException("Cannot record payment against an invoice still in processing")

        # Check remaining balance (allowing a tiny 0.001 tolerance for decimal precision)
        current_remaining = invoice.remaining_amount
        if data.amount > (current_remaining + Decimal("0.009")):
            raise ValidationException(
                f"Payment amount ({data.amount}) exceeds remaining invoice balance ({current_remaining})"
            )

        # Create Payment Record
        payment = Payment(
            invoice_id=data.invoice_id,
            amount=data.amount,
            payment_date=data.payment_date,
            payment_method=data.payment_method.strip(),
            reference_number=data.reference_number.strip() if data.reference_number else None,
            notes=data.notes.strip() if data.notes else None,
            created_by=user_id
        )
        db.add(payment)
        db.flush()  # Ensure payment is visible in session

        # Calculate new total paid for this invoice
        all_payments_sum = db.scalar(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
            .where(Payment.invoice_id == invoice.id)
        ) or Decimal("0.00")

        new_paid_amount = Decimal(str(all_payments_sum))
        new_remaining_amount = max(Decimal("0.00"), invoice.total_amount - new_paid_amount)

        invoice.paid_amount = new_paid_amount
        invoice.remaining_amount = new_remaining_amount

        # Update payment status
        if new_remaining_amount <= Decimal("0.00"):
            invoice.payment_status = PaymentStatus.PAID
            invoice.status = InvoiceStatus.PAID
        elif new_paid_amount > Decimal("0.00"):
            invoice.payment_status = PaymentStatus.PARTIALLY_PAID
        else:
            invoice.payment_status = PaymentStatus.PENDING

        db.commit()
        db.refresh(payment)
        db.refresh(invoice)

        # Record Audit Log
        AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.PAYMENT_RECORDED,
            entity="PAYMENT",
            entity_id=payment.id,
            details={
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "amount": str(payment.amount),
                "method": payment.payment_method,
                "new_paid_amount": str(invoice.paid_amount),
                "new_remaining_amount": str(invoice.remaining_amount),
                "payment_status": invoice.payment_status
            }
        )

        vendor = db.get(Vendor, invoice.vendor_id)
        vendor_name = vendor.name if vendor else "Unknown Vendor"

        logger.info(
            f"Payment recorded: {payment.amount} for Invoice #{invoice.invoice_number} (Status: {invoice.payment_status}, Remaining: {invoice.remaining_amount})"
        )

        return PaymentWithInvoiceResponse(
            id=payment.id,
            invoice_id=payment.invoice_id,
            amount=payment.amount,
            payment_date=payment.payment_date,
            payment_method=payment.payment_method,
            reference_number=payment.reference_number,
            notes=payment.notes,
            created_by=payment.created_by,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            invoice_number=invoice.invoice_number,
            vendor_name=vendor_name,
            invoice_total=invoice.total_amount,
            invoice_remaining=invoice.remaining_amount,
            invoice_payment_status=invoice.payment_status
        )
