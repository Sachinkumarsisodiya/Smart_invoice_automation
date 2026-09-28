import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from app.ai.provider import BaseAIProvider, ExtractedInvoiceSchema, ExtractedItemSchema
from app.core.logging import logger

INVOICE_NUM_BLACKLIST = {
    "CONFIRMATION", "CORPORATE", "INVOICE", "ORIGINAL", "DUPLICATE", "TRIPLICATE",
    "TAX", "BILL", "RECEIPT", "STATEMENT", "PAYMENT", "SUMMARY", "MEMO", "REPORT",
    "ACKNOWLEDGEMENT", "VOUCHER", "PURCHASE", "ORDER", "DETAILS", "NUMBER", "NO",
    "NUM", "DATE", "PAGE", "VALUE", "AMOUNT", "TOTAL", "CLIENT", "SUPPLIER", "VENDOR",
    "RECIPIENT", "CUSTOMER", "BUYER", "SELLER", "SUBTOTAL", "GST", "CGST", "SGST", "IGST"
}


class MockAIProvider(BaseAIProvider):
    """Zero-Hallucination Deterministic Heuristic Provider for local/offline processing.
    STRICT FINANCIAL INTEGRITY: Never invents, guesses, or fabricates financial figures.
    If an amount or invoice number cannot be reliably proven from document text,
    it returns 0.00 / UNKNOWN and assigns low confidence so it triggers manual review.
    """

    async def extract_invoice(self, text_content: str, metadata: Optional[Dict[str, Any]] = None) -> ExtractedInvoiceSchema:
        logger.info("[MockAIProvider] Parsing invoice text with zero-hallucination heuristic engine...")

        text = text_content or ""
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # 1. Vendor Extraction (Distinguish Seller vs Buyer)
        vendor_name = "Unassigned Vendor"
        
        # Check if seller is explicitly labeled
        seller_match = re.search(r"(?:supplier|seller|vendor|issued\s*by|from)\s*[:.]?\s*([A-Za-z0-9\s&.,'-]{3,60})", text, re.IGNORECASE)
        if seller_match:
            candidate = seller_match.group(1).split("\n")[0].strip()
            if not re.search(r"invoice|bill|tax|date|total|amount|customer|buyer|consignee", candidate, re.IGNORECASE):
                vendor_name = candidate

        # If not found via label, check top header lines (skipping Buyer/Consignee/Invoice title blocks)
        if vendor_name == "Unassigned Vendor" and lines:
            in_buyer_block = False
            for l in lines[:15]:
                clean_l = re.sub(r"--- PAGE BREAK ---|^\W+", "", l).strip()
                if not clean_l or len(clean_l) < 3:
                    continue
                # Skip buyer or consignee section
                if re.search(r"\b(?:billed\s*to|buyer|consignee|customer|client|ship\s*to|recipient)\b", clean_l, re.IGNORECASE):
                    in_buyer_block = True
                    continue
                if in_buyer_block:
                    if re.search(r"\b(?:gstin|pan|invoice|date|order)\b", clean_l, re.IGNORECASE):
                        in_buyer_block = False
                    continue

                # Skip obvious document header titles
                if re.match(r"^(?:tax\s*invoice|invoice|original\s*for\s*recipient|credit\s*note|bill\s*of\s*supply|purchase\s*order|e-way\s*bill)$", clean_l, re.IGNORECASE):
                    continue

                # Look for corporate / business entity keywords
                if re.search(r"\b(?:pvt\s*ltd|ltd|solutions|interiors|technologies|services|logistics|packaging|furnishing|motors|industries|store|corp|llp|traders|agency|hospitality|events)\b", clean_l, re.IGNORECASE):
                    vendor_name = clean_l
                    break
                elif clean_l.isupper() and len(clean_l) > 4 and not re.search(r"invoice|tax|gst|bill|credit|cash|original|duplicate|phone|email|address|date|total", clean_l, re.IGNORECASE):
                    vendor_name = clean_l
                    break

        # 2. Strict Invoice Number Extraction
        invoice_number = "INV-UNKNOWN"
        
        # Priority A: Standard structured patterns (e.g. SE-CR-2026-0372, INV/2026/012, INV-0894)
        structured_match = re.search(r"\b([A-Z]{2,6}[-_/][A-Z0-9]{2,6}[-_/][0-9]{4}[-_/][0-9]{2,6})\b", text)
        if not structured_match:
            structured_match = re.search(r"\b(INV[-_/][A-Za-z0-9\-_/]{3,20})\b", text, re.IGNORECASE)
            
        if structured_match:
            cand = structured_match.group(1).strip().upper()
            if cand not in INVOICE_NUM_BLACKLIST:
                invoice_number = cand
        else:
            # Priority B: Label-based search
            inv_label = re.search(r"(?:invoice\s*(?:number|no\.?|num|#)\s*[:#]?|inv\s*no\.?\s*[:#]?|bill\s*no\.?\s*[:#]?)\s*([A-Za-z0-9\-_/]+)", text, re.IGNORECASE)
            if inv_label:
                cand = inv_label.group(1).strip().upper()
                # Must not be a stopword and must contain at least 1 digit or valid separator
                if cand not in INVOICE_NUM_BLACKLIST and len(cand) >= 2 and (any(c.isdigit() for c in cand) or "-" in cand or "/" in cand):
                    invoice_number = cand

        # 3. Currency Detection
        currency = "INR"
        if re.search(r"\$|USD", text):
            currency = "USD"
        elif re.search(r"€|EUR", text):
            currency = "EUR"
        elif re.search(r"£|GBP", text):
            currency = "GBP"

        # 4. Strict Amount Extraction (NO FAKE / GUESS AMOUNTS)
        subtotal = Decimal("0.00")
        tax_amount = Decimal("0.00")
        total_amount = Decimal("0.00")

        # A. Total Amount Patterns
        total_patterns = [
            r"(?:total\s*due\s*amount|total\s*invoice\s*value|grand\s*total|net\s*payable|amount\s*payable|final\s*amount|total\s*payable)\s*[:.]?\s*(?:INR|USD|EUR|GBP|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
            r"(?:total\s*amount|total\s*due|invoice\s*total)\s*[:.]?\s*(?:INR|USD|EUR|GBP|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
            r"(?:^|\n)\s*total\s*[:.]?\s*(?:INR|USD|EUR|GBP|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)"
        ]
        for pat in total_patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in reversed(matches):  # check bottom matches first
                try:
                    cleaned_val = m.replace(",", "").strip()
                    val = Decimal(cleaned_val)
                    if val > 0:
                        total_amount = val
                        break
                except Exception:
                    continue
            if total_amount > 0:
                break

        # B. Subtotal / Taxable Value Patterns
        subtotal_patterns = [
            r"(?:taxable\s*value|sub\s*total(?:\s*\([^)]*\))?|subtotal|basic\s*amount|net\s*taxable\s*amount)\s*[:.]?\s*(?:INR|USD|EUR|GBP|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
            r"(?:taxable\s*amount|basic\s*value)\s*[:.]?\s*(?:INR|USD|EUR|GBP|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)"
        ]
        for pat in subtotal_patterns:
            sub_m = re.search(pat, text, re.IGNORECASE)
            if sub_m:
                try:
                    subtotal = Decimal(sub_m.group(1).replace(",", "").strip())
                    if subtotal > 0:
                        break
                except Exception:
                    pass

        # C. Tax Amount Patterns (CGST + SGST or IGST or generic Tax)
        cgst_match = re.search(r"cgst(?:\s*@\s*[\d.]+%)?\s*[:.]?\s*(?:INR|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
        sgst_match = re.search(r"sgst(?:\s*@\s*[\d.]+%)?\s*[:.]?\s*(?:INR|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
        igst_match = re.search(r"igst(?:\s*@\s*[\d.]+%)?\s*[:.]?\s*(?:INR|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)

        if cgst_match and sgst_match:
            try:
                c_tax = Decimal(cgst_match.group(1).replace(",", "").strip())
                s_tax = Decimal(sgst_match.group(1).replace(",", "").strip())
                tax_amount = c_tax + s_tax
            except Exception:
                pass
        elif igst_match:
            try:
                tax_amount = Decimal(igst_match.group(1).replace(",", "").strip())
            except Exception:
                pass
        else:
            tax_match = re.search(r"\b(?:total\s*tax|tax\s*amount|gst\s*amount|vat\s*amount)(?:\s*\([^)]*\))?\s*[:.]?\s*(?:INR|USD|EUR|GBP|₹|Rs\.?)?\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
            if tax_match:
                try:
                    tax_amount = Decimal(tax_match.group(1).replace(",", "").strip())
                except Exception:
                    pass

        # D. Mathematical Validation & Safety Reconciliation (NO GUESSING)
        # If total is found and subtotal is found, calculate tax if missing
        if total_amount > 0 and subtotal > 0 and tax_amount == 0:
            tax_amount = max(Decimal("0.00"), total_amount - subtotal)
        elif total_amount > 0 and subtotal == 0 and tax_amount > 0:
            subtotal = max(Decimal("0.00"), total_amount - tax_amount)
        elif total_amount == 0 and subtotal > 0 and tax_amount > 0:
            total_amount = subtotal + tax_amount

        # CRITICAL: If total_amount is STILL 0.00, we NEVER guess. It remains 0.00!

        # 5. Date Extraction
        today = date.today()
        invoice_date_str = today.strftime("%Y-%m-%d")
        due_date_str = (today + timedelta(days=30)).strftime("%Y-%m-%d")

        date_match = re.search(r"(?:invoice\s*date|dated|date\s*of\s*issue|date)\s*[:.]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
        if date_match:
            raw_date = date_match.group(1)
            if "/" in raw_date or (len(raw_date) == 10 and raw_date[2] == "-"):
                parts = re.split(r"[/-]", raw_date)
                if len(parts) == 3 and len(parts[2]) == 4:
                    invoice_date_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:
                invoice_date_str = raw_date

        due_match = re.search(r"(?:due\s*date|payment\s*due|pay\s*by)\s*[:.]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
        if due_match:
            raw_due = due_match.group(1)
            if "/" in raw_due or (len(raw_due) == 10 and raw_due[2] == "-"):
                parts = re.split(r"[/-]", raw_due)
                if len(parts) == 3 and len(parts[2]) == 4:
                    due_date_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:
                due_date_str = raw_due

        # 6. Items
        items = []
        if subtotal > 0 or total_amount > 0:
            line_amt = subtotal if subtotal > 0 else total_amount
            items.append(
                ExtractedItemSchema(
                    description="Invoice Goods / Services",
                    quantity=Decimal("1.000"),
                    unit_price=line_amt,
                    amount=line_amt
                )
            )

        # 7. Confidence Calculation
        # Zero confidence if total amount is 0 or invoice number is missing
        if total_amount <= 0 or invoice_number == "INV-UNKNOWN":
            confidence = Decimal("0.00")
        elif vendor_name != "Unassigned Vendor" and total_amount > 0:
            confidence = Decimal("95.00")
        else:
            confidence = Decimal("70.00")

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
            raw_response={"mock_engine": "zero_hallucination_v3", "source_char_count": len(text)},
            is_mock=True
        )
