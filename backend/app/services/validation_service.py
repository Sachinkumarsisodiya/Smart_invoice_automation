from decimal import Decimal
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Tuple
from app.ai.provider import ExtractedInvoiceSchema
from app.core.logging import logger

SUPPORTED_CURRENCIES = {"INR", "USD", "EUR", "GBP", "CAD", "AUD", "SGD", "AED"}

INVOICE_NUM_BLACKLIST = {
    "CONFIRMATION", "CORPORATE", "INVOICE", "ORIGINAL", "DUPLICATE", "TRIPLICATE",
    "TAX", "BILL", "RECEIPT", "STATEMENT", "PAYMENT", "SUMMARY", "MEMO", "REPORT",
    "ACKNOWLEDGEMENT", "VOUCHER", "PURCHASE", "ORDER", "DETAILS", "NUMBER", "NO",
    "NUM", "DATE", "PAGE", "VALUE", "AMOUNT", "TOTAL", "CLIENT", "SUPPLIER", "VENDOR",
    "INV-UNKNOWN", "UNKNOWN"
}


class ValidationService:
    """Strict zero-hallucination deterministic validation engine for AI extracted financial documents."""

    @staticmethod
    def validate_extracted_invoice(data: ExtractedInvoiceSchema) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Runs strict deterministic mathematical and schema validation rules.

        Returns:
            Tuple[is_valid: bool, errors: List[str], metadata: Dict[str, Any]]
        """
        errors: List[str] = []
        warnings: List[str] = []

        subtotal = data.subtotal or Decimal("0.00")
        tax_amount = data.tax_amount or Decimal("0.00")
        total_amount = data.total_amount or Decimal("0.00")

        # 1. Zero / Negative Financial Checks
        if total_amount <= Decimal("0.00"):
            errors.append("CRITICAL: Total invoice amount could not be verified (INR 0.00). Manual verification required to prevent financial error.")
        if subtotal < Decimal("0.00"):
            errors.append(f"Subtotal cannot be negative: {subtotal}")
        if tax_amount < Decimal("0.00"):
            errors.append(f"Tax amount cannot be negative: {tax_amount}")


        # 2. Mathematical Consistency: Subtotal + Tax = Total (tolerance ±1.00 for rounding)
        if total_amount > Decimal("0.00") and subtotal > Decimal("0.00"):
            expected_total = subtotal + tax_amount
            math_diff = abs(expected_total - total_amount)
            is_math_consistent = math_diff <= Decimal("1.00")

            if not is_math_consistent:
                errors.append(
                    f"Financial reconciliation discrepancy: Subtotal ({subtotal}) + Tax ({tax_amount}) = {expected_total}, but Total is {total_amount} (Diff: {math_diff})"
                )
        else:
            is_math_consistent = total_amount > 0

        # 3. Mandatory Identity Fields & Stopwords Check
        clean_inv_num = (data.invoice_number or "").strip().upper()
        if not clean_inv_num or clean_inv_num in INVOICE_NUM_BLACKLIST:
            errors.append(f"Invoice number is invalid or missing ('{data.invoice_number}')")

        clean_vendor = (data.vendor_name or "").strip()
        if not clean_vendor or clean_vendor in ("Unassigned Vendor", "Unknown Vendor"):
            warnings.append("Vendor / Seller name could not be definitively recognized.")

        # 4. Currency Check
        if data.currency.upper() not in SUPPORTED_CURRENCIES:
            warnings.append(f"Unrecognized or unsupported currency '{data.currency}'. Defaulted to INR.")

        # 5. Date Validity & Logical Timeline Check
        inv_date = None
        due_date = None

        try:
            inv_date = datetime.strptime(str(data.invoice_date).strip(), "%Y-%m-%d").date()
        except Exception:
            errors.append(f"Invalid invoice date format: '{data.invoice_date}'. Expected YYYY-MM-DD.")

        try:
            due_date = datetime.strptime(str(data.due_date).strip(), "%Y-%m-%d").date()
        except Exception:
            errors.append(f"Invalid due date format: '{data.due_date}'. Expected YYYY-MM-DD.")

        if inv_date and due_date:
            if due_date < inv_date:
                errors.append(f"Due date ({due_date}) cannot be earlier than invoice date ({inv_date})")

        is_valid = len(errors) == 0

        metadata = {
            "is_valid": is_valid,
            "math_consistent": is_math_consistent,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "validated_at": datetime.now(timezone.utc).isoformat()
        }

        if is_valid:
            logger.info(f"[Validation Passed] Invoice #{data.invoice_number} from '{data.vendor_name}' - Total: {total_amount}")
        else:
            logger.warning(f"[Validation Flagged] Invoice #{data.invoice_number} - {len(errors)} error(s): {'; '.join(errors)}")

        return is_valid, errors, metadata
