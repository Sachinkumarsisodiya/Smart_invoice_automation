import json
from decimal import Decimal
from typing import Dict, Any, Optional
import httpx
from app.config import settings
from app.core.logging import logger
from app.ai.provider import BaseAIProvider, ExtractedInvoiceSchema, ExtractedItemSchema


class RealAIProvider(BaseAIProvider):
    """Production LLM AI Provider supporting OpenAI, Gemini, or OpenAI-compatible endpoints."""

    def __init__(self, api_key: str = "", model_name: str = "gpt-4o-mini"):
        self.api_key = api_key or settings.AI_API_KEY
        self.model_name = model_name or settings.AI_MODEL_NAME

    async def extract_invoice(self, text_content: str, metadata: Optional[Dict[str, Any]] = None) -> ExtractedInvoiceSchema:
        logger.info(f"[RealAIProvider] Invoking LLM extraction with model '{self.model_name}'...")

        if not self.api_key:
            raise ValueError("AI_API_KEY is not configured. Please set AI_API_KEY in .env or switch AI_PROVIDER=mock.")

        system_prompt = (
            "You are an expert financial document extraction engine for SmartInvoice.\n"
            "Extract the invoice fields from the provided document text and return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "vendor_name": "string",\n'
            '  "vendor_gstin": "string or null",\n'
            '  "vendor_email": "string or null",\n'
            '  "invoice_number": "string",\n'
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
            "}\n"
            "Rules:\n"
            "- Normalize amounts (Subtotal, Tax, Total).\n"
            "- Never hallucinate fake numbers. If not found, use 0.00.\n"
            "- Return strictly raw JSON without markdown code blocks."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Document Text:\n{text_content[:8000]}"}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            res_data = response.json()
            raw_content = res_data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_content)

        items = [
            ExtractedItemSchema(
                description=it.get("description", "Item"),
                quantity=Decimal(str(it.get("quantity", 1))),
                unit_price=Decimal(str(it.get("unit_price", 0))),
                amount=Decimal(str(it.get("amount", 0)))
            )
            for it in parsed.get("items", [])
        ]

        return ExtractedInvoiceSchema(
            vendor_name=parsed.get("vendor_name", "Unknown Vendor"),
            vendor_gstin=parsed.get("vendor_gstin"),
            vendor_email=parsed.get("vendor_email"),
            invoice_number=parsed.get("invoice_number", "INV-UNKNOWN"),
            invoice_date=parsed.get("invoice_date", "2026-09-07"),
            due_date=parsed.get("due_date", "2026-09-30"),
            subtotal=Decimal(str(parsed.get("subtotal", 0))),
            tax_amount=Decimal(str(parsed.get("tax_amount", 0))),
            total_amount=Decimal(str(parsed.get("total_amount", 0))),
            currency=parsed.get("currency", "INR"),
            items=items,
            confidence_score=Decimal(str(parsed.get("confidence_score", 85.0))),
            raw_response=parsed,
            is_mock=False
        )
