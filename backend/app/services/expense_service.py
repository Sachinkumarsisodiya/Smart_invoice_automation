import uuid
from decimal import Decimal
from datetime import date
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, or_
from app.models.expense import Expense, ExpenseCategory
from app.models.vendor import Vendor
from app.models.invoice import Invoice
from app.models.audit_log import AuditAction
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseSummaryResponse, ExpenseCategoryBreakdown
from app.services.audit_service import AuditService
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import logger


class ExpenseService:
    @staticmethod
    def get_expenses(
        db: Session,
        category: Optional[str] = None,
        vendor_id: Optional[uuid.UUID] = None,
        payment_method: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Expense], int]:
        """Retrieves paginated and filtered expenses."""
        query = select(Expense).options(joinedload(Expense.vendor))

        if category and category.strip():
            query = query.where(Expense.category == category.strip())

        if vendor_id:
            query = query.where(Expense.vendor_id == vendor_id)

        if payment_method and payment_method.strip():
            query = query.where(Expense.payment_method == payment_method.strip())

        if start_date:
            query = query.where(Expense.expense_date >= start_date)

        if end_date:
            query = query.where(Expense.expense_date <= end_date)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Expense.description.ilike(term),
                    Expense.category.ilike(term)
                )
            )

        total = db.scalar(select(func.count()).select_from(query.subquery()))
        expenses = db.scalars(
            query.order_by(Expense.expense_date.desc(), Expense.created_at.desc()).offset(skip).limit(limit)
        ).all()

        return list(expenses), total

    @staticmethod
    def get_expense_by_id(db: Session, expense_id: uuid.UUID) -> Expense:
        """Retrieves single expense by ID."""
        expense = db.scalars(
            select(Expense).options(joinedload(Expense.vendor)).where(Expense.id == expense_id)
        ).first()
        if not expense:
            raise NotFoundException("Expense", str(expense_id))
        return expense

    @staticmethod
    def create_expense(db: Session, data: ExpenseCreate, user_id: uuid.UUID) -> Expense:
        """Creates a new operational expense."""
        if data.amount <= Decimal("0.00"):
            raise ValidationException("Expense amount must be strictly greater than 0.00")

        if data.vendor_id:
            vendor = db.get(Vendor, data.vendor_id)
            if not vendor:
                raise NotFoundException("Vendor", str(data.vendor_id))

        if data.invoice_id:
            invoice = db.get(Invoice, data.invoice_id)
            if not invoice:
                raise NotFoundException("Invoice", str(data.invoice_id))

        expense = Expense(
            category=data.category.strip(),
            amount=data.amount,
            expense_date=data.expense_date,
            description=data.description.strip(),
            payment_method=data.payment_method.strip(),
            vendor_id=data.vendor_id,
            invoice_id=data.invoice_id,
            created_by=user_id
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)

        AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.EXPENSE_CREATED,
            entity="EXPENSE",
            entity_id=expense.id,
            details={"category": expense.category, "amount": str(expense.amount), "description": expense.description}
        )

        logger.info(f"Expense recorded: ID {expense.id} - {expense.category} - {expense.amount} by user {user_id}")
        return expense

    @staticmethod
    def update_expense(db: Session, expense_id: uuid.UUID, data: ExpenseUpdate, user_id: uuid.UUID) -> Expense:
        """Updates an expense record."""
        expense = db.get(Expense, expense_id)
        if not expense:
            raise NotFoundException("Expense", str(expense_id))

        update_dict = data.model_dump(exclude_unset=True)

        if "amount" in update_dict and update_dict["amount"] is not None:
            if update_dict["amount"] <= Decimal("0.00"):
                raise ValidationException("Expense amount must be strictly greater than 0.00")

        if "vendor_id" in update_dict and update_dict["vendor_id"] is not None:
            vendor = db.get(Vendor, update_dict["vendor_id"])
            if not vendor:
                raise NotFoundException("Vendor", str(update_dict["vendor_id"]))

        for field, val in update_dict.items():
            if isinstance(val, str):
                val = val.strip()
            setattr(expense, field, val)

        db.commit()
        db.refresh(expense)

        AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.EXPENSE_UPDATED,
            entity="EXPENSE",
            entity_id=expense.id,
            details={"updated_fields": list(update_dict.keys())}
        )

        logger.info(f"Expense updated: ID {expense.id} by user {user_id}")
        return expense

    @staticmethod
    def delete_expense(db: Session, expense_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Deletes an expense record."""
        expense = db.get(Expense, expense_id)
        if not expense:
            raise NotFoundException("Expense", str(expense_id))

        db.delete(expense)
        db.commit()

        AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.EXPENSE_DELETED,
            entity="EXPENSE",
            entity_id=expense_id,
            details={"amount": str(expense.amount), "category": expense.category}
        )

        logger.info(f"Expense deleted: ID {expense_id} by user {user_id}")
        return True

    @staticmethod
    def get_expense_summary(db: Session) -> ExpenseSummaryResponse:
        """Calculates total spend and category-wise percentage distribution."""
        total_stats = db.execute(
            select(
                func.coalesce(func.sum(Expense.amount), Decimal("0.00")).label("total_amount"),
                func.count(Expense.id).label("total_count")
            )
        ).one()

        total_amount = Decimal(str(total_stats.total_amount or "0.00"))
        total_count = total_stats.total_count or 0

        # Category group query
        category_rows = db.execute(
            select(
                Expense.category,
                func.sum(Expense.amount).label("cat_amount"),
                func.count(Expense.id).label("cat_count")
            ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc())
        ).all()

        by_category: List[ExpenseCategoryBreakdown] = []
        for cat, cat_amt, cat_cnt in category_rows:
            cat_decimal = Decimal(str(cat_amt or "0.00"))
            pct = float((cat_decimal / total_amount) * 100) if total_amount > Decimal("0.00") else 0.0
            by_category.append(
                ExpenseCategoryBreakdown(
                    category=cat,
                    total_amount=cat_decimal,
                    count=cat_cnt,
                    percentage=round(pct, 2)
                )
            )

        return ExpenseSummaryResponse(
            total_expenses_amount=total_amount,
            total_count=total_count,
            by_category=by_category
        )
