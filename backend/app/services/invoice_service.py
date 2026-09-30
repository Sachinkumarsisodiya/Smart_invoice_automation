import os
import uuid
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Tuple, List
from fastapi import UploadFile, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc, asc

from app.config import settings
from app.core.logging import logger
from app.core.exceptions import NotFoundException, ValidationException, ConflictException
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus, PaymentStatus, ExtractionStatus
from app.models.vendor import Vendor
from app.models.user import User
from app.models.audit_log import AuditAction
from app.document.validator import DocumentValidator
from app.document.extractor import DocumentExtractor
from app.services.audit_service import AuditService
from app.schemas.invoice import InvoiceUpdate


class InvoiceService:
    @staticmethod
    def handle_upload(
        file: UploadFile,
        db: Session,
        current_user: User,
        vendor_id: Optional[uuid.UUID] = None,
        request: Optional[Request] = None
    ) -> Tuple[Invoice, dict]:
        """Validates file, stores on disk, extracts text, and registers invoice record."""
        # 1. Read file content
        content = file.file.read()
        file.file.seek(0)

        # 2. Validate file integrity, extension, size, and compute SHA-256 hash
        ext, mime_type, sha256_hash = DocumentValidator.validate_file(file, content)

        # 3. Check for exact duplicate file hash in database
        existing_duplicate = db.query(Invoice).filter(Invoice.document_hash == sha256_hash).first()
        if existing_duplicate:
            logger.warning(f"Duplicate document hash detected: {sha256_hash} (Invoice #{existing_duplicate.invoice_number})")
            # Note: in Phase 3 full duplicate detection engine is activated, but we record warning here

        # 4. Save file to secure storage directory
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_id = uuid.uuid4()
        saved_filename = f"{file_id}.{ext}"
        saved_filepath = os.path.join(settings.UPLOAD_DIR, saved_filename)

        with open(saved_filepath, "wb") as f:
            f.write(content)

        logger.info(f"Saved document to private storage: {saved_filepath} (Size: {len(content)} bytes)")

        # 5. Extract text from document
        extraction_data = DocumentExtractor.extract_text(saved_filepath, ext)
        import base64
        extraction_data["b64_document"] = base64.b64encode(content).decode("utf-8")

        # 6. Assign or resolve vendor
        target_vendor = None
        if vendor_id:
            target_vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()

        if not target_vendor:
            # Fallback to dedicated "Unassigned Vendor" placeholder until AI extraction finishes
            target_vendor = db.query(Vendor).filter(Vendor.name == "Unassigned Vendor").first()
            if not target_vendor:
                target_vendor = Vendor(
                    name="Unassigned Vendor",
                    email=None,
                    category="General",
                    payment_terms_days=30,
                    active=True
                )
                db.add(target_vendor)
                db.flush()

        # 7. Generate default invoice number & dates for initial ingestion
        generated_invoice_num = f"INV-{uuid.uuid4().hex[:6].upper()}"
        today = date.today()
        due_date = today + timedelta(days=target_vendor.payment_terms_days or 30)

        invoice = Invoice(
            id=file_id,
            vendor_id=target_vendor.id,
            invoice_number=generated_invoice_num,
            invoice_date=today,
            due_date=due_date,
            subtotal=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("0.00"),
            paid_amount=Decimal("0.00"),
            remaining_amount=Decimal("0.00"),
            currency="INR",
            status=InvoiceStatus.PROCESSING if extraction_data.get("needs_ocr") else InvoiceStatus.PENDING_REVIEW,
            payment_status=PaymentStatus.PENDING,
            document_path=saved_filepath,
            document_hash=sha256_hash,
            extraction_status=ExtractionStatus.SUCCESS if extraction_data.get("is_digital") else ExtractionStatus.PENDING,
            extraction_confidence=Decimal("85.00") if extraction_data.get("is_digital") else Decimal("50.00"),
            raw_extracted_data=extraction_data,
            notes=f"Uploaded by {current_user.full_name} ({current_user.email})"
        )

        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        # 8. Record audit log
        AuditService.log_action(
            db=db,
            action=AuditAction.INVOICE_UPLOADED,
            entity="INVOICE",
            entity_id=str(invoice.id),
            user_id=current_user.id,
            changes={
                "filename": file.filename,
                "document_hash": sha256_hash,
                "is_digital": extraction_data.get("is_digital"),
                "char_count": extraction_data.get("char_count")
            },
            request=request
        )

        return invoice, extraction_data

    @staticmethod
    def list_invoices(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        payment_status: Optional[str] = None,
        vendor_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ):
        query = db.query(Invoice).options(joinedload(Invoice.vendor))

        if status:
            query = query.filter(Invoice.status == status.upper())
        if payment_status:
            query = query.filter(Invoice.payment_status == payment_status.upper())
        if vendor_id:
            query = query.filter(Invoice.vendor_id == vendor_id)
        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.join(Invoice.vendor).filter(
                or_(
                    Invoice.invoice_number.ilike(search_pattern),
                    Vendor.name.ilike(search_pattern),
                    Invoice.notes.ilike(search_pattern)
                )
            )

        total = query.count()

        # Sorting
        sort_column = getattr(Invoice, sort_by, Invoice.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        items = query.offset((page - 1) * page_size).limit(page_size).all()
        pages = math.ceil(total / page_size) if page_size > 0 else 1

        return items, total, page, page_size, pages

    @staticmethod
    def get_invoice(db: Session, invoice_id: uuid.UUID) -> Invoice:
        invoice = (
            db.query(Invoice)
            .options(
                joinedload(Invoice.vendor),
                joinedload(Invoice.items),
                joinedload(Invoice.payments)
            )
            .filter(Invoice.id == invoice_id)
            .first()
        )
        if not invoice:
            raise NotFoundException(f"Invoice with ID '{invoice_id}' not found")
        return invoice

    @staticmethod
    def update_invoice(
        db: Session,
        invoice_id: uuid.UUID,
        update_data: InvoiceUpdate,
        current_user: User,
        request: Optional[Request] = None
    ) -> Invoice:
        invoice = InvoiceService.get_invoice(db, invoice_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        changes = {}

        # Handle vendor update
        if "vendor_id" in update_dict and update_dict["vendor_id"]:
            new_vendor = db.query(Vendor).filter(Vendor.id == update_dict["vendor_id"]).first()
            if not new_vendor:
                raise NotFoundException(f"Vendor with ID '{update_dict['vendor_id']}' not found")
            changes["vendor_id"] = {"old": str(invoice.vendor_id), "new": str(update_dict["vendor_id"])}
            invoice.vendor_id = update_dict["vendor_id"]

        for key, value in update_dict.items():
            if key == "vendor_id":
                continue
            old_val = getattr(invoice, key, None)
            if old_val != value:
                changes[key] = {"old": str(old_val), "new": str(value)}
                setattr(invoice, key, value)

        # Recalculate remaining amount if total_amount is changed
        if "total_amount" in update_dict:
            invoice.remaining_amount = max(Decimal("0.00"), invoice.total_amount - invoice.paid_amount)
            if invoice.remaining_amount == Decimal("0.00") and invoice.total_amount > Decimal("0.00"):
                invoice.payment_status = PaymentStatus.PAID
                invoice.status = InvoiceStatus.PAID

        db.commit()
        db.refresh(invoice)

        if changes:
            AuditService.log_action(
                db=db,
                action=AuditAction.INVOICE_EDITED,
                entity="INVOICE",
                entity_id=str(invoice.id),
                user_id=current_user.id,
                changes=changes,
                request=request
            )

        return invoice

    @staticmethod
    def delete_invoice(
        db: Session,
        invoice_id: uuid.UUID,
        current_user: User,
        request: Optional[Request] = None
    ) -> bool:
        invoice = InvoiceService.get_invoice(db, invoice_id)

        doc_path = invoice.document_path
        inv_number = invoice.invoice_number

        db.delete(invoice)
        db.commit()

        # Clean up file on disk
        if doc_path and os.path.exists(doc_path):
            try:
                os.remove(doc_path)
                logger.info(f"Removed document file: {doc_path}")
            except Exception as e:
                logger.error(f"Failed to remove file from disk {doc_path}: {e}")

        AuditService.log_action(
            db=db,
            action=AuditAction.INVOICE_DELETED,
            entity="INVOICE",
            entity_id=str(invoice_id),
            user_id=current_user.id,
            changes={"invoice_number": inv_number},
            request=request
        )

        return True
