import uuid
from decimal import Decimal
from datetime import date, datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_, desc
from app.models.invoice import Invoice, InvoiceStatus, PaymentStatus, ExtractionStatus
from app.models.payment import Payment
from app.models.expense import Expense
from app.models.vendor import Vendor
from app.schemas.analytics import (
    DashboardKPIsResponse,
    MonthlyCashflowItem,
    CategoryDistributionItem,
    StatusDistributionItem,
    TopVendorItem,
    RecentActivityItem
)
from app.core.logging import logger


class AnalyticsService:
    @staticmethod
    def get_dashboard_kpis(db: Session) -> DashboardKPIsResponse:
        """Calculates real-time financial and operational metrics for the executive dashboard."""
        today = date.today()

        # 1. Invoices Metrics (Excluding Rejected & Duplicate)
        inv_stats = db.execute(
            select(
                func.count(Invoice.id).label("total_count"),
                func.coalesce(func.sum(Invoice.total_amount), Decimal("0.00")).label("total_invoiced"),
                func.coalesce(func.sum(Invoice.paid_amount), Decimal("0.00")).label("total_paid"),
                func.coalesce(func.sum(Invoice.remaining_amount), Decimal("0.00")).label("total_remaining"),
                func.coalesce(func.avg(Invoice.extraction_confidence), Decimal("0.00")).label("avg_confidence"),
            ).where(
                Invoice.status != InvoiceStatus.REJECTED,
                Invoice.status != InvoiceStatus.DUPLICATE
            )
        ).one()

        # 2. Overdue Invoices
        overdue_stats = db.execute(
            select(
                func.count(Invoice.id).label("overdue_count"),
                func.coalesce(func.sum(Invoice.remaining_amount), Decimal("0.00")).label("overdue_amount")
            ).where(
                Invoice.due_date < today,
                Invoice.remaining_amount > Decimal("0.00"),
                Invoice.status != InvoiceStatus.REJECTED,
                Invoice.status != InvoiceStatus.DUPLICATE
            )
        ).one()

        # 3. Pending Review Count
        pending_review_count = db.scalar(
            select(func.count(Invoice.id)).where(
                Invoice.status.in_([InvoiceStatus.PENDING_REVIEW, InvoiceStatus.PROCESSING])
            )
        ) or 0

        # 4. Expenses Stats
        exp_stats = db.execute(
            select(
                func.count(Expense.id).label("exp_count"),
                func.coalesce(func.sum(Expense.amount), Decimal("0.00")).label("exp_amount")
            )
        ).one()

        # 5. Vendors & Payments Stats
        total_vendors_count = db.scalar(select(func.count(Vendor.id))) or 0
        total_payments_count = db.scalar(select(func.count(Payment.id))) or 0

        return DashboardKPIsResponse(
            total_invoices_count=inv_stats.total_count or 0,
            total_invoiced_amount=Decimal(str(inv_stats.total_invoiced or "0.00")),
            total_paid_amount=Decimal(str(inv_stats.total_paid or "0.00")),
            total_outstanding_amount=Decimal(str(inv_stats.total_remaining or "0.00")),
            overdue_invoices_count=overdue_stats.overdue_count or 0,
            overdue_amount=Decimal(str(overdue_stats.overdue_amount or "0.00")),
            pending_review_count=pending_review_count,
            total_expenses_amount=Decimal(str(exp_stats.exp_amount or "0.00")),
            total_expenses_count=exp_stats.exp_count or 0,
            total_vendors_count=total_vendors_count,
            average_ai_confidence=Decimal(str(round(float(inv_stats.avg_confidence or 0.0), 2))),
            total_settled_transactions=total_payments_count
        )

    @staticmethod
    def get_monthly_cashflow(db: Session, num_months: int = 6) -> List[MonthlyCashflowItem]:
        """Generates historical monthly trend comparing invoices, settlements, and expenses."""
        today = date.today()
        # Build month list for last num_months
        months: List[str] = []
        for i in range(num_months - 1, -1, -1):
            # Calculate Year-Month
            month_date = today.replace(day=1) - timedelta(days=i * 30)
            key = month_date.strftime("%Y-%m")
            if key not in months:
                months.append(key)

        results: List[MonthlyCashflowItem] = []

        for m_key in months:
            y, m = m_key.split("-")
            month_obj = datetime(int(y), int(m), 1)
            month_label = month_obj.strftime("%b %Y")

            # Next month start for range
            if int(m) == 12:
                next_month = datetime(int(y) + 1, 1, 1).date()
            else:
                next_month = datetime(int(y), int(m) + 1, 1).date()
            cur_month = month_obj.date()

            # Invoices in month
            inv_sum = db.scalar(
                select(func.coalesce(func.sum(Invoice.total_amount), Decimal("0.00")))
                .where(
                    Invoice.invoice_date >= cur_month,
                    Invoice.invoice_date < next_month,
                    Invoice.status != InvoiceStatus.REJECTED,
                    Invoice.status != InvoiceStatus.DUPLICATE
                )
            ) or Decimal("0.00")

            # Payments in month
            pay_sum = db.scalar(
                select(func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
                .where(
                    Payment.payment_date >= cur_month,
                    Payment.payment_date < next_month
                )
            ) or Decimal("0.00")

            # Expenses in month
            exp_sum = db.scalar(
                select(func.coalesce(func.sum(Expense.amount), Decimal("0.00")))
                .where(
                    Expense.expense_date >= cur_month,
                    Expense.expense_date < next_month
                )
            ) or Decimal("0.00")

            invoiced_d = Decimal(str(inv_sum))
            paid_d = Decimal(str(pay_sum))
            exp_d = Decimal(str(exp_sum))
            net_d = paid_d + exp_d  # Total cash outflows

            results.append(
                MonthlyCashflowItem(
                    month_key=m_key,
                    month_label=month_label,
                    invoiced_amount=invoiced_d,
                    paid_amount=paid_d,
                    expense_amount=exp_d,
                    net_cashflow=net_d
                )
            )

        return results

    @staticmethod
    def get_category_distribution(db: Session) -> List[CategoryDistributionItem]:
        """Aggregates total business spend distributed by categories."""
        # 1. Query Expenses by category
        exp_categories = db.execute(
            select(
                Expense.category,
                func.sum(Expense.amount).label("amount"),
                func.count(Expense.id).label("count")
            ).group_by(Expense.category)
        ).all()

        # 2. Query Invoices by vendor category
        inv_categories = db.execute(
            select(
                Vendor.category,
                func.sum(Invoice.total_amount).label("amount"),
                func.count(Invoice.id).label("count")
            )
            .join(Vendor, Invoice.vendor_id == Vendor.id)
            .where(
                Invoice.status != InvoiceStatus.REJECTED,
                Invoice.status != InvoiceStatus.DUPLICATE
            )
            .group_by(Vendor.category)
        ).all()

        cat_map: Dict[str, Dict[str, Any]] = {}

        for cat, amt, cnt in exp_categories:
            c_name = cat or "General"
            if c_name not in cat_map:
                cat_map[c_name] = {"amount": Decimal("0.00"), "count": 0}
            cat_map[c_name]["amount"] += Decimal(str(amt or "0.00"))
            cat_map[c_name]["count"] += cnt

        for cat, amt, cnt in inv_categories:
            c_name = cat or "General"
            if c_name not in cat_map:
                cat_map[c_name] = {"amount": Decimal("0.00"), "count": 0}
            cat_map[c_name]["amount"] += Decimal(str(amt or "0.00"))
            cat_map[c_name]["count"] += cnt

        total_spend = sum((data["amount"] for data in cat_map.values()), Decimal("0.00"))

        results: List[CategoryDistributionItem] = []
        for c_name, data in sorted(cat_map.items(), key=lambda x: x[1]["amount"], reverse=True):
            pct = float((data["amount"] / total_spend) * 100) if total_spend > Decimal("0.00") else 0.0
            results.append(
                CategoryDistributionItem(
                    category=c_name,
                    amount=data["amount"],
                    count=data["count"],
                    percentage=round(pct, 2)
                )
            )

        return results

    @staticmethod
    def get_status_distribution(db: Session) -> List[StatusDistributionItem]:
        """Calculates invoice counts and monetary value grouped by invoice status."""
        rows = db.execute(
            select(
                Invoice.status,
                func.count(Invoice.id).label("count"),
                func.coalesce(func.sum(Invoice.total_amount), Decimal("0.00")).label("amount")
            ).group_by(Invoice.status)
        ).all()

        return [
            StatusDistributionItem(
                status=status,
                count=count,
                amount=Decimal(str(amount or "0.00"))
            )
            for status, count, amount in rows
        ]

    @staticmethod
    def get_top_vendors(db: Session, limit: int = 5) -> List[TopVendorItem]:
        """Ranks top suppliers by total invoiced spend."""
        rows = db.execute(
            select(
                Vendor.id,
                Vendor.name,
                Vendor.category,
                func.coalesce(func.sum(Invoice.total_amount), Decimal("0.00")).label("total_invoiced"),
                func.coalesce(func.sum(Invoice.paid_amount), Decimal("0.00")).label("total_paid"),
                func.coalesce(func.sum(Invoice.remaining_amount), Decimal("0.00")).label("outstanding"),
                func.count(Invoice.id).label("invoice_count")
            )
            .join(Invoice, Vendor.id == Invoice.vendor_id)
            .where(
                Invoice.status != InvoiceStatus.REJECTED,
                Invoice.status != InvoiceStatus.DUPLICATE
            )
            .group_by(Vendor.id, Vendor.name, Vendor.category)
            .order_by(desc("total_invoiced"))
            .limit(limit)
        ).all()

        return [
            TopVendorItem(
                vendor_id=v_id,
                vendor_name=v_name,
                category=v_cat,
                total_invoiced=Decimal(str(t_inv or "0.00")),
                total_paid=Decimal(str(t_paid or "0.00")),
                outstanding_balance=Decimal(str(t_out or "0.00")),
                invoice_count=cnt
            )
            for v_id, v_name, v_cat, t_inv, t_paid, t_out, cnt in rows
        ]

    @staticmethod
    def get_recent_activity(db: Session, limit: int = 10) -> List[RecentActivityItem]:
        """Unified chronological timeline of recent invoices, payments, and expenses."""
        invoices = db.execute(
            select(Invoice, Vendor.name.label("vendor_name"))
            .join(Vendor, Invoice.vendor_id == Vendor.id)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        ).all()

        payments = db.execute(
            select(Payment, Invoice.invoice_number)
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
        ).all()

        expenses = db.execute(
            select(Expense)
            .order_by(Expense.created_at.desc())
            .limit(limit)
        ).scalars().all()

        feed: List[RecentActivityItem] = []

        for inv, v_name in invoices:
            feed.append(
                RecentActivityItem(
                    id=str(inv.id),
                    type="INVOICE",
                    title=f"Invoice #{inv.invoice_number}",
                    subtitle=f"{v_name} &bull; {inv.invoice_date}",
                    amount=inv.total_amount,
                    status=inv.status,
                    timestamp=inv.created_at
                )
            )

        for p, inv_num in payments:
            feed.append(
                RecentActivityItem(
                    id=str(p.id),
                    type="PAYMENT",
                    title=f"Settlement for #{inv_num}",
                    subtitle=f"Via {p.payment_method.replace('_', ' ')}",
                    amount=p.amount,
                    status="SETTLED",
                    timestamp=p.created_at
                )
            )

        for exp in expenses:
            feed.append(
                RecentActivityItem(
                    id=str(exp.id),
                    type="EXPENSE",
                    title=exp.description,
                    subtitle=f"Category: {exp.category}",
                    amount=exp.amount,
                    status="RECORDED",
                    timestamp=exp.created_at
                )
            )

        # Sort by timestamp descending
        feed.sort(key=lambda x: x.timestamp, reverse=True)
        return feed[:limit]
