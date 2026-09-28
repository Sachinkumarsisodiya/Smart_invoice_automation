import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional
from fastapi import Request
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.core.exceptions import NotFoundException, ValidationException
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus, ExtractionStatus, PaymentStatus
from app.models.vendor import Vendor
from app.models.user import User
from app.models.audit_log import AuditAction
from app.ai.invoice_extractor import get_ai_provider
from app.document.ocr import OCREngine
from app.services.validation_service import ValidationService
from app.services.duplicate_service import DuplicateService
from app.services.audit_service import AuditService


class ExtractionService:
    @staticmethod
    async def process_invoice_extraction(
        db: Session,
        invoice_id: uuid.UUID,
        current_user: User,
        request: Optional[Request] = None
    ) -> Invoice:
        """Executes the full pipeline:
        Document OCR (if needed) -> AI Extraction -> Deterministic Python Validation ->
        Duplicate Detection -> Database Persistence -> Audit Trail.
        """
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise NotFoundException(f"Invoice with ID '{invoice_id}' not found")

        logger.info(f"Starting extraction pipeline for invoice #{invoice.invoice_number} (ID: {invoice.id})")

        # 1. Check if OCR is required
        raw_text = ""
        if invoice.raw_extracted_data and isinstance(invoice.raw_extracted_data, dict):
            raw_text = invoice.raw_extracted_data.get("text", "")

        if not raw_text or len(raw_text.strip()) < 30 or "[Image Document" in raw_text:
            logger.info(f"Invoice {invoice.id} requires OCR. Running OCREngine...")
            ocr_res = OCREngine.run_ocr(invoice.document_path)
            if ocr_res.get("text"):
                raw_text = ocr_res["text"]

        # 2. Invoke Switchable AI Provider
        ai_provider = get_ai_provider()
        extracted_data = await ai_provider.extract_invoice(raw_text, metadata={"invoice_id": str(invoice.id)})

        # 3. Deterministic Python Mathematical & Schema Validation
        is_valid, validation_errors, validation_meta = ValidationService.validate_extracted_invoice(extracted_data)

        # 4. Resolve or Match Vendor
        vendor = None
        if extracted_data.vendor_name:
            vendor = db.query(Vendor).filter(Vendor.name.ilike(extracted_data.vendor_name.strip())).first()
            if not vendor:
                # Create vendor record dynamically
                vendor = Vendor(
                    name=extracted_data.vendor_name.strip(),
                    email=extracted_data.vendor_email,
                    gstin=extracted_data.vendor_gstin,
                    category="General",
                    payment_terms_days=30
                )
                db.add(vendor)
                db.flush()
                logger.info(f"Created new vendor from AI extraction: '{vendor.name}'")

        if vendor:
            invoice.vendor_id = vendor.id

        # 5. Check Duplicate
        inv_date_parsed = None
        try:
            inv_date_parsed = datetime.strptime(extracted_data.invoice_date, "%Y-%m-%d").date()
        except Exception:
            inv_date_parsed = date.today()

        due_date_parsed = None
        try:
            due_date_parsed = datetime.strptime(extracted_data.due_date, "%Y-%m-%d").date()
        except Exception:
            due_date_parsed = inv_date_parsed + (date.today() - inv_date_parsed)

        is_duplicate, match_reason, dup_id = DuplicateService.check_duplicate(
            db=db,
            vendor_id=invoice.vendor_id,
            invoice_number=extracted_data.invoice_number,
            document_hash=invoice.document_hash,
            invoice_date=inv_date_parsed,
            total_amount=extracted_data.total_amount,
            exclude_invoice_id=invoice.id
        )

        if is_duplicate:
            validation_errors.append(f"Duplicate invoice detected ({match_reason}) matching Invoice ID: {dup_id}")
            validation_meta["is_duplicate"] = True
            validation_meta["duplicate_match_reason"] = match_reason
            validation_meta["duplicate_invoice_id"] = str(dup_id)
            is_valid = False

        # 6. Update Invoice Database Record
        invoice.invoice_number = extracted_data.invoice_number
        invoice.invoice_date = inv_date_parsed
        invoice.due_date = due_date_parsed
        invoice.subtotal = extracted_data.subtotal
        invoice.tax_amount = extracted_data.tax_amount
        invoice.total_amount = extracted_data.total_amount
        invoice.remaining_amount = max(Decimal("0.00"), extracted_data.total_amount - invoice.paid_amount)
        invoice.currency = extracted_data.currency
        invoice.extraction_confidence = extracted_data.confidence_score
        
        if not is_valid or extracted_data.total_amount <= Decimal("0.00"):
            invoice.extraction_status = ExtractionStatus.FAILED if extracted_data.total_amount <= Decimal("0.00") else ExtractionStatus.MANUAL
            invoice.status = InvoiceStatus.PENDING_REVIEW
            invoice.notes = f"⚠️ Financial Safety Flag: {'; '.join(validation_errors)}"
        else:
            invoice.extraction_status = ExtractionStatus.SUCCESS
            invoice.status = InvoiceStatus.PENDING_REVIEW
            
        invoice.raw_extracted_data = {
            "text": raw_text,
            "ai_extracted": extracted_data.model_dump(mode="json"),
            "is_mock": extracted_data.is_mock
        }
        invoice.validation_errors = validation_meta

        # 7. Replace / Populate Line Items
        db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).delete()
        if extracted_data.items:
            for item_data in extracted_data.items:
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=item_data.description,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    amount=item_data.amount
                )
                db.add(item)

        db.commit()
        db.refresh(invoice)

        # 8. Record Audit Log
        AuditService.log_action(
            db=db,
            action=AuditAction.INVOICE_EXTRACTED,
            entity="INVOICE",
            entity_id=str(invoice.id),
            user_id=current_user.id,
            changes={
                "invoice_number": invoice.invoice_number,
                "total_amount": str(invoice.total_amount),
                "is_valid": is_valid,
                "confidence_score": str(invoice.extraction_confidence),
                "is_mock": extracted_data.is_mock,
                "error_count": len(validation_errors)
            },
            request=request
        )

        return invoice
