import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from app.ai.provider import BaseAIProvider, ExtractedInvoiceSchema, ExtractedItemSchema
from app.core.logging import logger


class MockAIProvider(BaseAIProvider):
    """Deterministic Mock AI Provider for local development, demo mode, and offline testing.
    Uses regex patterns and rule-based heuristics to extract structured financial data.
    """

    async def extract_invoice(self, text_content: str, metadata: Optional[Dict[str, Any]] = None) -> ExtractedInvoiceSchema:
        logger.info("[MockAIProvider] Parsing invoice text using advanced deterministic heuristic engine...")

        text = text_content or ""
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # 1. Vendor Name Heuristic
        vendor_name = "Unassigned Vendor"
        # Check for prominent vendor headers in first 10 lines
        for l in lines[:10]:
            clean_l = re.sub(r"--- PAGE BREAK ---|^\W+", "", l).strip()
            if not clean_l:
                continue
            # If line looks like a company name
            if re.search(r"\b(?:interiors|pvt\s*ltd|ltd|solutions|enterprises|technologies|services|logistics|packaging|furnishing|motors|industries|store|corp|llp)\b", clean_l, re.IGNORECASE):
                vendor_name = clean_l
                break
            elif clean_l.isupper() and len(clean_l) > 4 and not re.search(r"invoice|tax|gst|bill|credit|cash|original|duplicate|phone|email|address", clean_l, re.IGNORECASE):
                vendor_name = clean_l
                break

        if vendor_name == "Unassigned Vendor":
            vendor_match = re.search(r"(?:vendor|supplier|seller|billed\s*by|from)\s*[:.]?\s*([A-Za-z0-9\s&.,'-]+)", text, re.IGNORECASE)
            if vendor_match:
                v_cand = vendor_match.group(1).split("\n")[0].strip()
                if len(v_cand) > 3 and not re.search(r"invoice|tax|total|date", v_cand, re.IGNORECASE):
                    vendor_name = v_cand
            elif lines:
                first_line = re.sub(r"^(?:vendor|seller|from)\s*[:.]?\s*", "", lines[0].replace("--- PAGE BREAK ---", ""), flags=re.IGNORECASE).strip()
                if first_line and len(first_line) < 60 and not re.search(r"invoice|bill|tax|receipt", first_line, re.IGNORECASE):
                    vendor_name = first_line

        # 2. Invoice Number Regex
        invoice_number = "INV-UNKNOWN"
        direct_inv = re.search(r"\b(INV-[A-Za-z0-9\-_/]+)\b", text, re.IGNORECASE)
        if direct_inv:
            invoice_number = direct_inv.group(1).strip()
        else:
            inv_label = re.search(r"(?:invoice\s*(?:number|no\.?|num|#)\s*[:#]?|invoice\s*[:#]|inv\s*no\.?)\s*([A-Za-z0-9\-_/]+)", text, re.IGNORECASE)
            if inv_label:
                candidate = inv_label.group(1).strip()
                if candidate.upper() not in ("NUMBER", "NO", "NUM", "DATE", "TAX", "VENDOR", "OICE", "VALUE"):
                    invoice_number = candidate

        # 3. Currency Detection
        currency = "INR"
        if re.search(r"\$|USD", text):
            currency = "USD"
        elif re.search(r"€|EUR", text):
            currency = "EUR"
        elif re.search(r"£|GBP", text):
            currency = "GBP"

        # 4. Amounts Detection
        subtotal = Decimal("0.00")
        tax_amount = Decimal("0.00")
        total_amount = Decimal("0.00")

        # Extract Total / Grand Total / Total Due Amount / Total Invoice Value
        total_patterns = [
            r"(?:total\s*due\s*amount|total\s*due|total\s*invoice\s*value|grand\s*total|net\s*payable|amount\s*payable|total\s*amount|final\s*amount)\s*[:.]?\s*(?:INR|USD|EUR|GBP|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
            r"\btotal\s*[:.]?\s*(?:INR|USD|EUR|GBP|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)"
        ]
        for pat in total_patterns:
            total_match = re.search(pat, text, re.IGNORECASE)
            if total_match:
                try:
                    parsed_total = total_match.group(1).replace(",", "")
                    val = Decimal(parsed_total)
                    if val > 0:
                        total_amount = val
                        break
                except Exception:
                    pass

        # Extract Subtotal / Taxable Value
        subtotal_match = re.search(
            r"(?:sub\s*total(?:\s*\([^)]*\))?|taxable\s*value|subtotal|net\s*amount|basic\s*amount)\s*[:.]?\s*(?:INR|USD|EUR|GBP|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
            text,
            re.IGNORECASE
        )
        if subtotal_match:
            try:
                parsed_sub = subtotal_match.group(1).replace(",", "")
                subtotal = Decimal(parsed_sub)
            except Exception:
                pass

        # Extract CGST + SGST or IGST or generic Tax
        cgst_match = re.search(r"cgst(?:\s*@\s*[\d.]+%)?\s*[:.]?\s*(?:INR|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
        sgst_match = re.search(r"sgst(?:\s*@\s*[\d.]+%)?\s*[:.]?\s*(?:INR|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
        igst_match = re.search(r"igst(?:\s*@\s*[\d.]+%)?\s*[:.]?\s*(?:INR|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)

        if cgst_match and sgst_match:
            try:
                c_tax = Decimal(cgst_match.group(1).replace(",", ""))
                s_tax = Decimal(sgst_match.group(1).replace(",", ""))
                tax_amount = c_tax + s_tax
            except Exception:
                pass
        elif igst_match:
            try:
                tax_amount = Decimal(igst_match.group(1).replace(",", ""))
            except Exception:
                pass
        else:
            tax_match = re.search(r"\b(?:tax|gst|vat|tax\s*amount)(?:\s*\([^)]*\))?\s*[:.]?\s*(?:INR|USD|EUR|GBP|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
            if tax_match:
                try:
                    tax_amount = Decimal(tax_match.group(1).replace(",", ""))
                except Exception:
                    pass

        # Fallback math reconciliation
        if total_amount > 0 and subtotal == 0:
            if tax_amount > 0:
                subtotal = total_amount - tax_amount
            else:
                subtotal = (total_amount / Decimal("1.18")).quantize(Decimal("0.01"))
                tax_amount = total_amount - subtotal
        elif subtotal > 0 and total_amount == 0:
            if tax_amount > 0:
                total_amount = subtotal + tax_amount
            else:
                tax_amount = (subtotal * Decimal("0.18")).quantize(Decimal("0.01"))
                total_amount = subtotal + tax_amount
        elif total_amount == 0 and subtotal == 0:
            total_amount = Decimal("300000.00")
            subtotal = Decimal("254237.29")
            tax_amount = Decimal("45762.71")

        # 5. Date Parsing / Defaults
        today = date.today()
        invoice_date_str = today.strftime("%Y-%m-%d")
        due_date_str = (today + timedelta(days=30)).strftime("%Y-%m-%d")

        date_match = re.search(r"(?:date|invoice\s*date)\s*[:.]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
        if date_match:
            raw_date = date_match.group(1)
            if "/" in raw_date or (len(raw_date) == 10 and raw_date[2] == "-"):
                parts = re.split(r"[/-]", raw_date)
                if len(parts) == 3 and len(parts[2]) == 4:
                    invoice_date_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:
                invoice_date_str = raw_date

        due_match = re.search(r"(?:due\s*date|payment\s*due)\s*[:.]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
        if due_match:
            raw_due = due_match.group(1)
            if "/" in raw_due or (len(raw_due) == 10 and raw_due[2] == "-"):
                parts = re.split(r"[/-]", raw_due)
                if len(parts) == 3 and len(parts[2]) == 4:
                    due_date_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:
                due_date_str = raw_due

        # 6. Items Extraction
        items = [
            ExtractedItemSchema(
                description="Furnishing & Custom Interior Items",
                quantity=Decimal("1.000"),
                unit_price=subtotal,
                amount=subtotal
            )
        ]

        # Calculate simulated confidence
        confidence = Decimal("98.50") if (total_amount > 0 and subtotal > 0) else Decimal("85.00")

        return ExtractedInvoiceSchema(
            vendor_name=vendor_name,
            invoice_number=invoice_number,
            invoice_date=invoice_date_str,
            due_date=due_date_str,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency=currency,
            items=items,
            confidence_score=confidence,
            raw_response={"mock_engine": "regex_heuristic_v2", "source_char_count": len(text)},
            is_mock=True
        )
