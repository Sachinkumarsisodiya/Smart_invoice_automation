import os
import fitz  # PyMuPDF
from PIL import Image
from typing import Dict, Any
from app.core.logging import logger

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False


class OCREngine:
    @staticmethod
    def run_ocr(file_path: str) -> Dict[str, Any]:
        """Runs Optical Character Recognition on scanned PDF pages or image files."""
        result = {
            "text": "",
            "success": False,
            "engine": "pytesseract" if PYTESSERACT_AVAILABLE else "fallback_pymupdf",
            "page_count": 1,
            "is_image": False,
            "error": None
        }

        if not os.path.exists(file_path):
            result["error"] = f"File not found: {file_path}"
            return result

        ext = file_path.split(".")[-1].lower()

        try:
            if ext == "pdf":
                doc = fitz.open(file_path)
                result["page_count"] = len(doc)
                extracted_pages = []

                for i in range(len(doc)):
                    page = doc[i]
                    page_text = page.get_text("text").strip()

                    # If page text is sparse, try pixmap OCR if pytesseract is available
                    if len(page_text) < 30 and PYTESSERACT_AVAILABLE:
                        try:
                            pix = page.get_pixmap(dpi=200)
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            ocr_text = pytesseract.image_to_string(img)
                            if len(ocr_text.strip()) > len(page_text):
                                page_text = ocr_text.strip()
                        except Exception as ocr_err:
                            logger.warning(f"PyTesseract error on page {i+1}: {ocr_err}")

                    extracted_pages.append(page_text)

                doc.close()
                combined = "\n--- PAGE BREAK ---\n".join(extracted_pages).strip()
                result["text"] = combined
                result["success"] = bool(combined)

            elif ext in ("png", "jpg", "jpeg"):
                result["is_image"] = True
                if PYTESSERACT_AVAILABLE:
                    try:
                        with Image.open(file_path) as img:
                            ocr_text = pytesseract.image_to_string(img)
                            result["text"] = ocr_text.strip()
                            result["success"] = bool(result["text"])
                    except Exception as ocr_err:
                        logger.warning(f"PyTesseract image OCR warning: {ocr_err}")
                        result["error"] = str(ocr_err)
                else:
                    # Clean empty text; do NOT inject error text as raw document content
                    result["text"] = ""
                    result["error"] = "pytesseract_unavailable"

        except Exception as e:
            logger.error(f"OCR execution failed on {file_path}: {e}")
            result["error"] = str(e)

        return result
