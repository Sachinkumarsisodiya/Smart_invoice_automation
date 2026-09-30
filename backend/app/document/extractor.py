import os
from typing import Dict, Any
import fitz  # PyMuPDF
from PIL import Image
import io
from app.core.logging import logger


class DocumentExtractor:
    @staticmethod
    def extract_text(file_path: str, file_ext: str) -> Dict[str, Any]:
        """Extracts text content and metadata from PDF or Image files."""
        result = {
            "text": "",
            "page_count": 1,
            "char_count": 0,
            "is_digital": False,
            "needs_ocr": False,
            "pages": [],
            "metadata": {}
        }

        if not os.path.exists(file_path):
            logger.error(f"File not found for extraction: {file_path}")
            return result

        try:
            if file_ext.lower() == "pdf":
                doc = fitz.open(file_path)
                result["page_count"] = len(doc)
                result["metadata"] = doc.metadata or {}

                full_text = []
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    page_text = page.get_text("text")
                    full_text.append(page_text)
                    result["pages"].append({
                        "page_number": page_num + 1,
                        "text": page_text,
                        "char_count": len(page_text.strip())
                    })

                combined_text = "\n--- PAGE BREAK ---\n".join(full_text).strip()
                result["text"] = combined_text
                result["char_count"] = len(combined_text)

                # If text density is sufficient (e.g. > 40 non-whitespace chars), consider digital PDF
                if result["char_count"] > 40:
                    result["is_digital"] = True
                    result["needs_ocr"] = False
                else:
                    result["is_digital"] = False
                    result["needs_ocr"] = True
                
                doc.close()

            elif file_ext.lower() in ("png", "jpg", "jpeg", "webp", "bmp", "tiff"):
                with Image.open(file_path) as img:
                    result["metadata"] = {
                        "format": img.format,
                        "width": img.width,
                        "height": img.height,
                        "mode": img.mode,
                    }
                result["is_digital"] = False
                
                # Execute OCR directly on image
                from app.document.ocr import OCREngine
                ocr_data = OCREngine.run_ocr(file_path)
                extracted_text = (ocr_data.get("text") or "").strip()
                
                if extracted_text:
                    result["text"] = extracted_text
                    result["char_count"] = len(extracted_text)
                    result["needs_ocr"] = False
                    result["ocr_engine"] = ocr_data.get("engine")
                else:
                    result["text"] = "[Image Document - OCR in Progress]"
                    result["char_count"] = 0
                    result["needs_ocr"] = True

        except Exception as e:
            logger.error(f"Error during document extraction on {file_path}: {str(e)}")
            result["error"] = str(e)
            result["needs_ocr"] = True

        return result
