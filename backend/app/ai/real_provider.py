import os
import json
import re
import base64
from decimal import Decimal
from typing import Dict, Any, Optional, List
import httpx
from app.config import settings
from app.core.logging import logger
from app.ai.provider import BaseAIProvider, ExtractedInvoiceSchema, ExtractedItemSchema


def clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Robustly extracts and parses JSON from LLM responses even if wrapped in markdown or partial text."""
    text = (raw_text or "").strip()
    if not text:
        return {}

    # Strip markdown code blocks
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

    try:
        return json.loads(text)
    except Exception:
        # Try extracting innermost or outermost JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except Exception as e:
                logger.warning(f"[clean_json_response] Slice parse failed: {e}")
    return {}


class RealAIProvider(BaseAIProvider):
    """Production LLM & Vision AI Provider supporting Google Gemini, OpenAI, or OpenAI-compatible endpoints.
    Enforces strict zero-hallucination guidelines for financial documents.
    """

    def __init__(self, api_key: str = "", model_name: str = ""):
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("AI_API_KEY")
            or settings.AI_API_KEY
            or ""
        ).strip()
        self.model_name = model_name or settings.AI_MODEL_NAME or "gemini-1.5-flash"

    async def extract_invoice(self, text_content: str, metadata: Optional[Dict[str, Any]] = None) -> ExtractedInvoiceSchema:
        logger.info(f"[RealAIProvider] Invoking LLM text extraction with model '{self.model_name}'...")

        if not self.api_key:
            raise ValueError("AI API key is not configured. Set GEMINI_API_KEY or AI_API_KEY.")

        system_instruction = self._get_system_prompt()
        parsed_json: Dict[str, Any] = {}

        is_gemini = self.api_key.startswith("AIza") or "gemini" in self.model_name.lower()

        if is_gemini:
            candidate_models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
            if "gemini" in self.model_name and self.model_name not in candidate_models:
                candidate_models.insert(0, self.model_name)

            last_err = None
            for model in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": f"{system_instruction}\n\nDOCUMENT TEXT TO PARSE:\n{text_content[:15000]}"}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.0,
                        "responseMimeType": "application/json"
                    }
                }

                try:
                    async with httpx.AsyncClient(timeout=45.0) as client:
                        res = await client.post(url, json=payload)
                        res.raise_for_status()
                        res_data = res.json()
                        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed_json = clean_json_response(raw_text)
                        if parsed_json:
                            logger.info(f"[RealAIProvider] Text extraction succeeded with model '{model}'")
                            break
                except Exception as model_err:
                    last_err = model_err
                    logger.warning(f"[RealAIProvider] Gemini model '{model}' failed: {model_err}")

            if not parsed_json and last_err:
                raise last_err

        else:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": f"Document Text:\n{text_content[:12000]}"}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }

            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                res.raise_for_status()
                res_data = res.json()
                raw_content = res_data["choices"][0]["message"]["content"]
                parsed_json = clean_json_response(raw_content)

        return self._build_schema_response(parsed_json)

    async def extract_from_image(self, image_path: str, mime_type: str = "image/jpeg", metadata: Optional[Dict[str, Any]] = None) -> ExtractedInvoiceSchema:
        """Directly parses images via Gemini Vision or OpenAI Vision without needing system Tesseract."""
        logger.info(f"[RealAIProvider] Invoking Multimodal Vision extraction on image: {image_path}...")

        if not self.api_key:
            raise ValueError("AI API key is not configured for image OCR. Set GEMINI_API_KEY or AI_API_KEY.")

        with open(image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")

        system_instruction = self._get_system_prompt()
        parsed_json: Dict[str, Any] = {}

        is_gemini = self.api_key.startswith("AIza") or "gemini" in self.model_name.lower()

        if is_gemini:
            candidate_models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-2.5-flash", "gemini-1.5-flash-8b"]
            if "gemini" in self.model_name and self.model_name not in candidate_models:
                candidate_models.insert(0, self.model_name)

            last_err = None
            for model in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": f"{system_instruction}\n\nParse this financial invoice image and return exact structured JSON matching the schema:"},
                                {
                                    "inlineData": {
                                        "mimeType": mime_type,
                                        "data": b64_data
                                    }
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.0,
                        "responseMimeType": "application/json"
                    }
                }

                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        res = await client.post(url, json=payload)
                        res.raise_for_status()
                        res_data = res.json()
                        candidates = res_data.get("candidates", [])
                        if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
                            parts = candidates[0]["content"]["parts"]
                            raw_text = "".join([p.get("text", "") for p in parts if "text" in p])
                            parsed_json = clean_json_response(raw_text)
                            if parsed_json:
                                logger.info(f"[RealAIProvider] Gemini Vision extraction succeeded with model '{model}'")
                                break
                except Exception as model_err:
                    last_err = model_err
                    logger.warning(f"[RealAIProvider] Gemini Vision model '{model}' attempt failed: {model_err}")

            if not parsed_json and last_err:
                raise last_err

        else:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model_name if "gpt-4" in self.model_name else "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all structured fields from this invoice image:"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{b64_data}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                res.raise_for_status()
                res_data = res.json()
                raw_content = res_data["choices"][0]["message"]["content"]
                parsed_json = clean_json_response(raw_content)

        return self._build_schema_response(parsed_json)

    def _get_system_prompt(self) -> str:
        return (
            "You are a strict, audited financial document parser for SmartInvoice.\n"
            "Your task is to extract exact financial data from the document.\n"
            "CRITICAL INTEGRITY RULES:\n"
            "1. NEVER invent, hallucinate, or assume amounts or dates.\n"
            "2. If an amount (subtotal, tax, or total) cannot be found, return 0.00.\n"
            "3. Distinguish between Seller (vendor) and Buyer (client/customer).\n"
            "4. Return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "vendor_name": "string (seller/company name)",\n'
            '  "vendor_gstin": "string or null",\n'
            '  "vendor_email": "string or null",\n'
            '  "invoice_number": "string (exact invoice #)",\n'
            '  "invoice_date": "YYYY-MM-DD",\n'
            '  "due_date": "YYYY-MM-DD",\n'
            '  "subtotal": float,\n'
            '  "tax_amount": float,\n'
            '  "total_amount": float,\n'
            '  "currency": "INR|USD|EUR|GBP",\n'
            '  "items": [\n'
            '    {\n'
            '      "description": "string",\n'
            '      "quantity": float,\n'
            '      "unit_price": float,\n'
            '      "amount": float\n'
            '    }\n'
            '  ],\n'
            '  "confidence_score": float (0 to 100)\n'
            "}"
        )

    def _build_schema_response(self, parsed_json: Dict[str, Any]) -> ExtractedInvoiceSchema:
        items = [
            ExtractedItemSchema(
                description=it.get("description", "Item"),
                quantity=Decimal(str(it.get("quantity", 1))),
                unit_price=Decimal(str(it.get("unit_price", 0))),
                amount=Decimal(str(it.get("amount", 0)))
            )
            for it in parsed_json.get("items", [])
        ]

        total = Decimal(str(parsed_json.get("total_amount", 0)))
        subtotal = Decimal(str(parsed_json.get("subtotal", 0)))
        tax = Decimal(str(parsed_json.get("tax_amount", 0)))

        # Mathematical reconciliation if subtotal + tax ~ total
        if total > 0 and subtotal == 0 and tax > 0:
            subtotal = total - tax
        elif total > 0 and subtotal > 0 and tax == 0:
            tax = total - subtotal

        confidence = Decimal(str(parsed_json.get("confidence_score", 95.0))) if total > 0 else Decimal("0.00")

        return ExtractedInvoiceSchema(
            vendor_name=parsed_json.get("vendor_name", "Unknown Vendor"),
            vendor_gstin=parsed_json.get("vendor_gstin"),
            vendor_email=parsed_json.get("vendor_email"),
            invoice_number=parsed_json.get("invoice_number", "INV-UNKNOWN"),
            invoice_date=parsed_json.get("invoice_date", "2026-09-28"),
            due_date=parsed_json.get("due_date", "2026-10-28"),
            subtotal=subtotal,
            tax_amount=tax,
            total_amount=total,
            currency=parsed_json.get("currency", "INR"),
            items=items,
            confidence_score=confidence,
            raw_response=parsed_json,
            is_mock=False
        )

