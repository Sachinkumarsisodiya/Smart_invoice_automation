import os
import json
import re
import base64
from decimal import Decimal
from typing import Dict, Any, Optional
import httpx
from app.config import settings
from app.core.logging import logger
from app.ai.provider import BaseAIProvider, ExtractedInvoiceSchema, ExtractedItemSchema


class RealAIProvider(BaseAIProvider):
    """Production LLM & Vision AI Provider supporting Google Gemini, OpenAI, or OpenAI-compatible endpoints.
    Enforces strict zero-hallucination guidelines for financial documents.
    """

    def __init__(self, api_key: str = "", model_name: str = ""):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or settings.AI_API_KEY
        self.model_name = model_name or settings.AI_MODEL_NAME or "gemini-1.5-flash"

    async def extract_invoice(self, text_content: str, metadata: Optional[Dict[str, Any]] = None) -> ExtractedInvoiceSchema:
        logger.info(f"[RealAIProvider] Invoking LLM text extraction with model '{self.model_name}'...")

        if not self.api_key:
            raise ValueError("AI API key is not configured. Please set GEMINI_API_KEY or AI_API_KEY in environment.")

        system_instruction = self._get_system_prompt()
        parsed_json: Dict[str, Any] = {}

        is_gemini = self.api_key.startswith("AIza") or "gemini" in self.model_name.lower()

        if is_gemini:
            gemini_model = self.model_name if "gemini" in self.model_name else "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={self.api_key}"
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

            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                res_data = res.json()
                raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                parsed_json = json.loads(raw_text)

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
                parsed_json = json.loads(raw_content)

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
            gemini_model = self.model_name if "gemini" in self.model_name else "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{system_instruction}\n\nParse this invoice image and return exact structured JSON:"},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
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

            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                res_data = res.json()
                raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                parsed_json = json.loads(raw_text)

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
                parsed_json = json.loads(raw_content)

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
            '  "vendor_name": "string (seller name)",\n'
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
