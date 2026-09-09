from decimal import Decimal
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Tuple
from app.ai.provider import ExtractedInvoiceSchema
from app.core.logging import logger

SUPPORTED_CURRENCIES = {"INR", "USD", "EUR", "GBP", "CAD", "AUD", "SGD", "AED"}


class ValidationService:
    """Deterministic validation engine for AI extracted financial documents."""

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

        # 1. Non-negative constraints
        if subtotal < Decimal("0.00"):
            errors.append(f"Subtotal cannot be negative: {subtotal}")
        if tax_amount < Decimal("0.00"):
            errors.append(f"Tax amount cannot be negative: {tax_amount}")
        if total_amount < Decimal("0.00"):
            errors.append(f"Total amount cannot be negative: {total_amount}")

        # 2. Mathematical Consistency: Subtotal + Tax = Total (tolerance ±0.02)
        expected_total = subtotal + tax_amount
        math_diff = abs(expected_total - total_amount)
        is_math_consistent = math_diff <= Decimal("0.02")

        if not is_math_consistent:
            errors.append(
                f"Mathematical inconsistency: Subtotal ({subtotal}) + Tax ({tax_amount}) = {expected_total}, but Total is {total_amount} (Diff: {math_diff})"
            )

        # 3. Line Item Summation Check
        if data.items:
            items_sum = Decimal("0.00")
            for idx, item in enumerate(data.items, start=1):
                if item.quantity < Decimal("0.00"):
                    errors.append(f"Item #{idx} quantity cannot be negative: {item.quantity}")
                if item.unit_price < Decimal("0.00"):
                    errors.append(f"Item #{idx} unit price cannot be negative: {item.unit_price}")
                
                # Check item line amount = quantity * unit_price
                expected_item_amt = (item.quantity * item.unit_price).quantize(Decimal("0.01"))
                if abs(expected_item_amt - item.amount) > Decimal("0.05"):
                    warnings.append(
                        f"Item #{idx} amount discrepancy: Qty ({item.quantity}) * Price ({item.unit_price}) = {expected_item_amt}, but line amount is {item.amount}"
                    )
                items_sum += item.amount

            # Compare items sum to subtotal if subtotal is greater than 0
            if subtotal > Decimal("0.00") and abs(items_sum - subtotal) > Decimal("0.05"):
                warnings.append(f"Sum of line items ({items_sum}) does not equal subtotal ({subtotal})")

        # 4. Mandatory Identity Fields
        if not data.vendor_name or not data.vendor_name.strip():
            errors.append("Vendor name is required and missing")

        if not data.invoice_number or not data.invoice_number.strip():
            errors.append("Invoice number is required and missing")

        # 5. Currency Check
        if data.currency.upper() not in SUPPORTED_CURRENCIES:
            warnings.append(f"Unrecognized or unsupported currency '{data.currency}'. Defaulted to INR.")

        # 6. Date Validity & Logical Timeline Check
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
            logger.warning(f"[Validation Failed] Invoice #{data.invoice_number} - {len(errors)} error(s): {'; '.join(errors)}")

        return is_valid, errors, metadata
