import io
import csv
import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment
from app.models.expense import Expense
from app.models.vendor import Vendor
from app.schemas.analytics import TaxSummaryResponse, TaxVendorBreakdown


class ReportService:
    @staticmethod
    def export_invoices_csv(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        vendor_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None
    ) -> str:
        """Generates an RFC 4180 CSV export of filtered invoices."""
        query = (
            select(Invoice, Vendor)
            .join(Vendor, Invoice.vendor_id == Vendor.id)
            .order_by(Invoice.invoice_date.desc())
        )

        if start_date:
            query = query.where(Invoice.invoice_date >= start_date)
        if end_date:
            query = query.where(Invoice.invoice_date <= end_date)
        if vendor_id:
            query = query.where(Invoice.vendor_id == vendor_id)
        if status:
            query = query.where(Invoice.status == status)

        rows = db.execute(query).all()

        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")

        # Header
        writer.writerow([
            "Invoice ID",
            "Invoice Number",
            "Vendor Name",
            "Vendor GSTIN",
            "Invoice Date",
            "Due Date",
            "Subtotal",
            "Tax Amount",
            "Total Amount",
            "Paid Amount",
            "Remaining Amount",
            "Currency",
            "Status",
            "Payment Status",
            "Confidence Score",
            "Created At"
        ])

        for inv, v in rows:
            writer.writerow([
                str(inv.id),
                inv.invoice_number,
                v.name,
                v.gstin or "",
                inv.invoice_date.isoformat(),
                inv.due_date.isoformat(),
                str(inv.subtotal),
                str(inv.tax_amount),
                str(inv.total_amount),
                str(inv.paid_amount),
                str(inv.remaining_amount),
                inv.currency,
                inv.status,
                inv.payment_status,
                str(inv.extraction_confidence),
                inv.created_at.isoformat()
            ])

        return output.getvalue()

    @staticmethod
    def export_expenses_csv(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
        payment_method: Optional[str] = None
    ) -> str:
        """Generates an RFC 4180 CSV export of operational expenses."""
        query = (
            select(Expense, Vendor)
            .outerjoin(Vendor, Expense.vendor_id == Vendor.id)
            .order_by(Expense.expense_date.desc())
        )

        if start_date:
            query = query.where(Expense.expense_date >= start_date)
        if end_date:
            query = query.where(Expense.expense_date <= end_date)
        if category:
            query = query.where(Expense.category == category)
        if payment_method:
            query = query.where(Expense.payment_method == payment_method)

        rows = db.execute(query).all()

        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")

        writer.writerow([
            "Expense ID",
            "Expense Date",
            "Category",
            "Description",
            "Amount",
            "Payment Method",
            "Vendor / Supplier",
            "Created At"
        ])

        for exp, v in rows:
            writer.writerow([
                str(exp.id),
                exp.expense_date.isoformat(),
                exp.category,
                exp.description,
                str(exp.amount),
                exp.payment_method,
                v.name if v else "",
                exp.created_at.isoformat()
            ])

        return output.getvalue()

    @staticmethod
    def export_payments_csv(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        payment_method: Optional[str] = None
    ) -> str:
        """Generates an RFC 4180 CSV export of payment transactions."""
        query = (
            select(Payment, Invoice, Vendor)
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .join(Vendor, Invoice.vendor_id == Vendor.id)
            .order_by(Payment.payment_date.desc())
        )

        if start_date:
            query = query.where(Payment.payment_date >= start_date)
        if end_date:
            query = query.where(Payment.payment_date <= end_date)
        if payment_method:
            query = query.where(Payment.payment_method == payment_method)

        rows = db.execute(query).all()

        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")

        writer.writerow([
            "Payment ID",
            "Payment Date",
            "Invoice Number",
            "Vendor Name",
            "Amount Settled",
            "Payment Method",
            "Reference / UTR",
            "Notes",
            "Recorded At"
        ])

        for p, inv, v in rows:
            writer.writerow([
                str(p.id),
                p.payment_date.isoformat(),
                inv.invoice_number,
                v.name,
                str(p.amount),
                p.payment_method,
                p.reference_number or "",
                p.notes or "",
                p.created_at.isoformat()
            ])

        return output.getvalue()

    @staticmethod
    def get_tax_summary(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> TaxSummaryResponse:
        """Generates tax accounting summary with input tax credits grouped by supplier GSTIN."""
        query = (
            select(
                Vendor.id.label("vendor_id"),
                Vendor.name.label("vendor_name"),
                Vendor.gstin.label("vendor_gstin"),
                func.coalesce(func.sum(Invoice.subtotal), Decimal("0.00")).label("subtotal_sum"),
                func.coalesce(func.sum(Invoice.tax_amount), Decimal("0.00")).label("tax_sum"),
                func.coalesce(func.sum(Invoice.total_amount), Decimal("0.00")).label("gross_sum"),
                func.count(Invoice.id).label("inv_count")
            )
            .join(Invoice, Vendor.id == Invoice.vendor_id)
            .where(Invoice.status != InvoiceStatus.REJECTED)
        )

        if start_date:
            query = query.where(Invoice.invoice_date >= start_date)
        if end_date:
            query = query.where(Invoice.invoice_date <= end_date)

        vendor_rows = db.execute(
            query.group_by(Vendor.id, Vendor.name, Vendor.gstin).order_by(func.sum(Invoice.tax_amount).desc())
        ).all()

        total_subtotal = Decimal("0.00")
        total_tax = Decimal("0.00")
        total_gross = Decimal("0.00")
        total_invoices = 0

        breakdowns: List[TaxVendorBreakdown] = []
        for v_id, v_name, v_gstin, sub_sum, tx_sum, grs_sum, cnt in vendor_rows:
            s_dec = Decimal(str(sub_sum or "0.00"))
            t_dec = Decimal(str(tx_sum or "0.00"))
            g_dec = Decimal(str(grs_sum or "0.00"))

            total_subtotal += s_dec
            total_tax += t_dec
            total_gross += g_dec
            total_invoices += cnt

            breakdowns.append(
                TaxVendorBreakdown(
                    vendor_id=v_id,
                    vendor_name=v_name,
                    gstin=v_gstin,
                    subtotal=s_dec,
                    tax_amount=t_dec,
                    total_gross=g_dec,
                    invoice_count=cnt
                )
            )

        return TaxSummaryResponse(
            start_date=start_date,
            end_date=end_date,
            total_subtotal=total_subtotal,
            total_tax_amount=total_tax,
            total_gross_amount=total_gross,
            total_invoices=total_invoices,
            vendors_breakdown=breakdowns
        )
