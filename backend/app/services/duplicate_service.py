import uuid
from decimal import Decimal
from datetime import date
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.invoice import Invoice
from app.core.logging import logger


class DuplicateMatchReason:
    VENDOR_AND_INVOICE_NUMBER = "VENDOR_AND_INVOICE_NUMBER"
    DOCUMENT_HASH = "DOCUMENT_HASH"
    FUZZY_VENDOR_DATE_AMOUNT = "FUZZY_VENDOR_DATE_AMOUNT"


class DuplicateService:
    """Multi-tiered duplicate invoice detection engine."""

    @staticmethod
    def check_duplicate(
        db: Session,
        vendor_id: uuid.UUID,
        invoice_number: str,
        document_hash: str,
        invoice_date: Optional[date] = None,
        total_amount: Optional[Decimal] = None,
        exclude_invoice_id: Optional[uuid.UUID] = None
    ) -> Tuple[bool, Optional[str], Optional[uuid.UUID]]:
        """Checks for duplicate invoice against existing database records.

        Returns:
            Tuple[is_duplicate: bool, match_reason: Optional[str], duplicate_invoice_id: Optional[UUID]]
        """
        # 1. Primary Check: vendor_id + invoice_number
        if vendor_id and invoice_number:
            query = db.query(Invoice).filter(
                Invoice.vendor_id == vendor_id,
                Invoice.invoice_number.ilike(invoice_number.strip())
            )
            if exclude_invoice_id:
                query = query.filter(Invoice.id != exclude_invoice_id)

            match = query.first()
            if match:
                logger.warning(f"[Duplicate Detected] Primary Match: Vendor {vendor_id} + Invoice #{invoice_number} (Matched ID: {match.id})")
                return True, DuplicateMatchReason.VENDOR_AND_INVOICE_NUMBER, match.id

        # 2. Secondary Check: Exact SHA-256 document hash
        if document_hash:
            query = db.query(Invoice).filter(Invoice.document_hash == document_hash)
            if exclude_invoice_id:
                query = query.filter(Invoice.id != exclude_invoice_id)

            match = query.first()
            if match:
                logger.warning(f"[Duplicate Detected] Secondary Match: Document Hash {document_hash[:12]}... (Matched ID: {match.id})")
                return True, DuplicateMatchReason.DOCUMENT_HASH, match.id

        # 3. Tertiary / Fuzzy Check: vendor_id + invoice_date + total_amount
        if vendor_id and invoice_date and total_amount and total_amount > Decimal("0.00"):
            query = db.query(Invoice).filter(
                Invoice.vendor_id == vendor_id,
                Invoice.invoice_date == invoice_date,
                Invoice.total_amount == total_amount
            )
            if exclude_invoice_id:
                query = query.filter(Invoice.id != exclude_invoice_id)

            match = query.first()
            if match:
                logger.warning(f"[Duplicate Detected] Tertiary Match: Same Vendor, Date ({invoice_date}), and Amount ({total_amount}) (Matched ID: {match.id})")
                return True, DuplicateMatchReason.FUZZY_VENDOR_DATE_AMOUNT, match.id

        return False, None, None
