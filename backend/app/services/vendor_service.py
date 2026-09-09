import uuid
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.vendor import Vendor
from app.models.invoice import Invoice, InvoiceStatus, PaymentStatus
from app.models.audit_log import AuditAction
from app.schemas.vendor import VendorCreate, VendorUpdate, VendorDetailResponse, VendorResponse
from app.services.audit_service import AuditService
from app.core.exceptions import NotFoundException, ConflictException, ValidationException
from app.core.logging import logger


class VendorService:
    @staticmethod
    def get_vendors(
        db: Session,
        search: Optional[str] = None,
        category: Optional[str] = None,
        active_only: bool = False,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Vendor], int]:
        """Retrieves paginated and filtered vendors."""
        query = select(Vendor)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Vendor.name.ilike(term),
                    Vendor.gstin.ilike(term),
                    Vendor.email.ilike(term)
                )
            )

        if category and category.strip():
            query = query.where(Vendor.category == category.strip())

        if active_only:
            query = query.where(Vendor.active == True)

        total = db.scalar(select(func.count()).select_from(query.subquery()))
        vendors = db.scalars(
            query.order_by(Vendor.name.asc()).offset(skip).limit(limit)
        ).all()

        return list(vendors), total

    @staticmethod
    def get_vendor_by_id(db: Session, vendor_id: uuid.UUID) -> VendorDetailResponse:
        """Fetches vendor details with aggregated financial metrics."""
        vendor = db.get(Vendor, vendor_id)
        if not vendor:
            raise NotFoundException("Vendor", str(vendor_id))

        # Compute invoice aggregation metrics
        stats = db.execute(
            select(
                func.count(Invoice.id).label("total_invoices"),
                func.coalesce(func.sum(Invoice.total_amount), Decimal("0.00")).label("total_invoiced"),
                func.coalesce(func.sum(Invoice.paid_amount), Decimal("0.00")).label("total_paid"),
                func.coalesce(func.sum(Invoice.remaining_amount), Decimal("0.00")).label("total_remaining"),
            ).where(
                Invoice.vendor_id == vendor_id,
                Invoice.status != InvoiceStatus.REJECTED
            )
        ).one()

        return VendorDetailResponse(
            id=vendor.id,
            name=vendor.name,
            email=vendor.email,
            phone=vendor.phone,
            gstin=vendor.gstin,
            address=vendor.address,
            category=vendor.category,
            payment_terms_days=vendor.payment_terms_days,
            active=vendor.active,
            created_at=vendor.created_at,
            updated_at=vendor.updated_at,
            total_invoices=stats.total_invoices or 0,
            total_invoiced_amount=Decimal(str(stats.total_invoiced or "0.00")),
            total_paid_amount=Decimal(str(stats.total_paid or "0.00")),
            outstanding_balance=Decimal(str(stats.total_remaining or "0.00"))
        )

    @staticmethod
    def create_vendor(db: Session, data: VendorCreate, user_id: uuid.UUID) -> Vendor:
        """Creates a new vendor with audit log recording."""
        # Check name or GSTIN duplicate if GSTIN provided
        if data.gstin and data.gstin.strip():
            existing = db.scalar(
                select(Vendor).where(
                    func.lower(Vendor.gstin) == data.gstin.strip().lower()
                )
            )
            if existing:
                raise ConflictException(f"A vendor with GSTIN '{data.gstin}' already exists: '{existing.name}'")

        vendor = Vendor(
            name=data.name.strip(),
            email=data.email.strip() if data.email else None,
            phone=data.phone.strip() if data.phone else None,
            gstin=data.gstin.strip() if data.gstin else None,
            address=data.address.strip() if data.address else None,
            category=data.category.strip() if data.category else "General",
            payment_terms_days=data.payment_terms_days,
            active=data.active
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.VENDOR_CREATED,
            entity="VENDOR",
            entity_id=vendor.id,
            details={"name": vendor.name, "category": vendor.category, "gstin": vendor.gstin}
        )

        logger.info(f"Vendor created: '{vendor.name}' (ID: {vendor.id}) by user {user_id}")
        return vendor

    @staticmethod
    def update_vendor(db: Session, vendor_id: uuid.UUID, data: VendorUpdate, user_id: uuid.UUID) -> Vendor:
        """Updates an existing vendor."""
        vendor = db.get(Vendor, vendor_id)
        if not vendor:
            raise NotFoundException("Vendor", str(vendor_id))

        update_dict = data.model_dump(exclude_unset=True)

        if "gstin" in update_dict and update_dict["gstin"]:
            gstin_val = update_dict["gstin"].strip().lower()
            existing = db.scalar(
                select(Vendor).where(
                    func.lower(Vendor.gstin) == gstin_val,
                    Vendor.id != vendor_id
                )
            )
            if existing:
                raise ConflictException(f"Another vendor with GSTIN '{update_dict['gstin']}' already exists: '{existing.name}'")

        for field, val in update_dict.items():
            if isinstance(val, str):
                val = val.strip()
            setattr(vendor, field, val)

        db.commit()
        db.refresh(vendor)

        AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.VENDOR_UPDATED,
            entity="VENDOR",
            entity_id=vendor.id,
            details={"updated_fields": list(update_dict.keys())}
        )

        logger.info(f"Vendor updated: '{vendor.name}' (ID: {vendor.id}) by user {user_id}")
        return vendor

    @staticmethod
    def delete_vendor(db: Session, vendor_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Deletes or deactivates a vendor safely."""
        vendor = db.get(Vendor, vendor_id)
        if not vendor:
            raise NotFoundException("Vendor", str(vendor_id))

        # Check if linked to invoices
        invoice_count = db.scalar(
            select(func.count(Invoice.id)).where(Invoice.vendor_id == vendor_id)
        )
        if invoice_count and invoice_count > 0:
            # Cannot hard-delete; deactivate instead
            vendor.active = False
            db.commit()
            AuditService.log_action(
                db=db,
                user_id=user_id,
                action=AuditAction.VENDOR_DELETED,
                entity="VENDOR",
                entity_id=vendor.id,
                details={"deactivated": True, "reason": f"Linked to {invoice_count} existing invoices"}
            )
            logger.info(f"Vendor deactivated (has {invoice_count} invoices): '{vendor.name}' (ID: {vendor.id})")
            return True

        db.delete(vendor)
        db.commit()

        AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.VENDOR_DELETED,
            entity="VENDOR",
            entity_id=vendor_id,
            details={"hard_deleted": True, "vendor_name": vendor.name}
        )

        logger.info(f"Vendor hard deleted: '{vendor.name}' (ID: {vendor_id}) by user {user_id}")
        return True
