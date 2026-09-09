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
        logger.info("[MockAIProvider] Parsing invoice text using deterministic heuristic engine...")

        text = text_content or ""
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # 1. Vendor Name Heuristic
        vendor_name = "Sharma Packaging Pvt Ltd"
        vendor_match = re.search(r"(?:vendor|supplier|seller|from)\s*[:.]?\s*([A-Za-z0-9\s&.,'-]+)", text, re.IGNORECASE)
        if vendor_match:
            v_cand = vendor_match.group(1).split("\n")[0].strip()
            if len(v_cand) > 3 and not re.search(r"invoice|tax|total|date", v_cand, re.IGNORECASE):
                vendor_name = v_cand
        elif "Apex Cloud" in text:
            vendor_name = "Apex Cloud & IT Services"
        elif "National Logistics" in text:
            vendor_name = "National Logistics Express"
        elif lines:
            first_line = re.sub(r"^(?:vendor|seller|from)\s*[:.]?\s*", "", lines[0].replace("--- PAGE BREAK ---", ""), flags=re.IGNORECASE).strip()
            if first_line and len(first_line) < 60 and not re.search(r"invoice|bill|tax|receipt", first_line, re.IGNORECASE):
                vendor_name = first_line

        # 2. Invoice Number Regex
        invoice_number = "INV-1045"
        direct_inv = re.search(r"\b(INV-[A-Za-z0-9\-_/]+)\b", text, re.IGNORECASE)
        if direct_inv:
            invoice_number = direct_inv.group(1).strip()
        else:
            inv_label = re.search(r"(?:invoice\s*(?:number|no\.?|num|#)\s*[:#]?|invoice\s*[:#])\s*([A-Za-z0-9\-_/]+)", text, re.IGNORECASE)
            if inv_label:
                candidate = inv_label.group(1).strip()
                if candidate.upper() not in ("NUMBER", "NO", "NUM", "DATE", "TAX", "VENDOR", "OICE"):
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
        subtotal = Decimal("10000.00")
        tax_amount = Decimal("1800.00")
        total_amount = Decimal("11800.00")

        # Extract Total / Grand Total
        total_match = re.search(r"\b(?:total(?:\s*amount)?|grand\s*total|amount\s*payable|net\s*payable)\s*[:.]?\s*(?:INR|USD|EUR|GBP|₹|\$)?\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
        if total_match:
            try:
                parsed_total = total_match.group(1).replace(",", "")
                total_amount = Decimal(parsed_total)
            except Exception:
                pass

        # Extract Subtotal
        subtotal_match = re.search(r"\b(?:subtotal|sub\s*total|net\s*amount|taxable\s*value)\s*[:.]?\s*(?:INR|USD|EUR|GBP|₹|\$)?\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
        if subtotal_match:
            try:
                parsed_sub = subtotal_match.group(1).replace(",", "")
                subtotal = Decimal(parsed_sub)
            except Exception:
                pass
        else:
            subtotal = (total_amount / Decimal("1.18")).quantize(Decimal("0.01"))

        # Extract Tax Amount (ignoring rate like GST 18% in parentheses)
        tax_match = re.search(r"\b(?:tax|gst|vat|tax\s*amount)(?:\s*\([^)]*\))?\s*[:.]?\s*(?:INR|USD|EUR|GBP|₹|\$)?\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
        if tax_match:
            try:
                parsed_tax = tax_match.group(1).replace(",", "")
                tax_amount = Decimal(parsed_tax)
            except Exception:
                pass
        else:
            tax_amount = (total_amount - subtotal).quantize(Decimal("0.01"))

        # 5. Date Parsing / Defaults
        today = date.today()
        invoice_date_str = today.strftime("%Y-%m-%d")
        due_date_str = (today + timedelta(days=30)).strftime("%Y-%m-%d")

        date_match = re.search(r"(?:date|invoice\s*date)\s*[:.]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
        if date_match:
            raw_date = date_match.group(1)
            # Normalize if DD/MM/YYYY
            if "/" in raw_date or (len(raw_date) == 10 and raw_date[2] == "-"):
                parts = re.split(r"[/-]", raw_date)
                if len(parts) == 3 and len(parts[2]) == 4:
                    invoice_date_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:
                invoice_date_str = raw_date

        # 6. Sample Line Items
        items = [
            ExtractedItemSchema(
                description="Packaging & Corrugated Boxes (Grade A)",
                quantity=Decimal("10.000"),
                unit_price=Decimal("1000.00"),
                amount=Decimal("10000.00")
            )
        ]

        # Calculate simulated confidence
        confidence = Decimal("94.50") if (invoice_number != "INV-UNKNOWN" and total_match) else Decimal("82.00")

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
            raw_response={"mock_engine": "regex_heuristic_v1", "source_char_count": len(text)},
            is_mock=True
        )
