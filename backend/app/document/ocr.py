import os
from typing import Dict, Any, Optional
import fitz  # PyMuPDF
from PIL import Image
from app.core.logging import logger

try:
    from rapidocr_onnxruntime import RapidOCR
    RAPIDOCR_AVAILABLE = True
except ImportError:
    RAPIDOCR_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

_rapid_ocr_instance: Optional[Any] = None


def get_rapid_ocr() -> Optional[Any]:
    global _rapid_ocr_instance
    if _rapid_ocr_instance is None and RAPIDOCR_AVAILABLE:
        try:
            _rapid_ocr_instance = RapidOCR()
            logger.info("[OCREngine] RapidOCR ONNX runtime initialized successfully.")
        except Exception as e:
            logger.warning(f"[OCREngine] Failed to initialize RapidOCR: {e}")
    return _rapid_ocr_instance


class OCREngine:
    @staticmethod
    def run_ocr(file_path: str) -> Dict[str, Any]:
        """Runs Optical Character Recognition on scanned PDF pages or image files.
        Uses pure-Python ONNX RapidOCR as primary engine (no system C++ Tesseract binary needed).
        """
        result = {
            "text": "",
            "success": False,
            "engine": "rapidocr" if RAPIDOCR_AVAILABLE else ("pytesseract" if PYTESSERACT_AVAILABLE else "fallback_pymupdf"),
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

                rapid_engine = get_rapid_ocr()

                for i in range(len(doc)):
                    page = doc[i]
                    page_text = page.get_text("text").strip()

                    # If page text is sparse (scanned PDF), run OCR
                    if len(page_text) < 30:
                        ocr_candidate = ""
                        try:
                            pix = page.get_pixmap(dpi=200)
                            img_bytes = pix.tobytes("png")

                            if rapid_engine:
                                ocr_res, _ = rapid_engine(img_bytes)
                                if ocr_res:
                                    lines = [box[1] for box in ocr_res if box and len(box) > 1 and box[1]]
                                    ocr_candidate = "\n".join(lines).strip()

                            if not ocr_candidate and PYTESSERACT_AVAILABLE:
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                tess_res = pytesseract.image_to_string(img).strip()
                                if tess_res:
                                    ocr_candidate = tess_res

                            if len(ocr_candidate) > len(page_text):
                                page_text = ocr_candidate
                        except Exception as ocr_err:
                            logger.warning(f"[OCREngine] PDF Page {i+1} OCR scan warning: {ocr_err}")

                    extracted_pages.append(page_text)

                doc.close()
                combined = "\n--- PAGE BREAK ---\n".join(extracted_pages).strip()
                result["text"] = combined
                result["success"] = bool(combined)

            elif ext in ("png", "jpg", "jpeg", "webp", "bmp", "tiff"):
                result["is_image"] = True
                extracted_lines = []

                # 1. Primary: RapidOCR (no system tesseract dependency)
                rapid_engine = get_rapid_ocr()
                if rapid_engine:
                    try:
                        ocr_res, _ = rapid_engine(file_path)
                        if ocr_res:
                            for box in ocr_res:
                                if box and len(box) > 1 and box[1]:
                                    extracted_lines.append(box[1].strip())
                            
                            text_out = "\n".join(extracted_lines).strip()
                            if text_out:
                                result["text"] = text_out
                                result["success"] = True
                                result["engine"] = "rapidocr_onnx"
                                logger.info(f"[OCREngine] RapidOCR extracted {len(extracted_lines)} lines from {file_path}")
                                return result
                    except Exception as rap_err:
                        logger.warning(f"[OCREngine] RapidOCR failed on {file_path}: {rap_err}")

                # 2. Fallback: PyTesseract (if installed on host)
                if PYTESSERACT_AVAILABLE:
                    try:
                        with Image.open(file_path) as img:
                            tess_text = pytesseract.image_to_string(img).strip()
                            if tess_text:
                                result["text"] = tess_text
                                result["success"] = True
                                result["engine"] = "pytesseract"
                                return result
                    except Exception as tess_err:
                        logger.warning(f"[OCREngine] PyTesseract failed on {file_path}: {tess_err}")

                result["text"] = ""
                result["error"] = "Image OCR engines yielded no text"

        except Exception as e:
            logger.error(f"[OCREngine] OCR execution failed on {file_path}: {e}")
            result["error"] = str(e)

        return result

