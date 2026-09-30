import os
from typing import Dict, Any, Optional
import fitz  # PyMuPDF
from PIL import Image
from app.core.logging import logger

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False


class OCREngine:
    @staticmethod
    def run_ocr(file_path: str) -> Dict[str, Any]:
        """Runs Optical Character Recognition on scanned PDF pages or image files using lightweight system PyTesseract."""
        result = {
            "text": "",
            "success": False,
            "engine": "pytesseract" if PYTESSERACT_AVAILABLE else "pymupdf",
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

                try:
                    for i in range(len(doc)):
                        page = doc[i]
                        page_text = page.get_text("text").strip()

                        # If page text is sparse (scanned PDF), run OCR via PyTesseract
                        if len(page_text) < 30 and PYTESSERACT_AVAILABLE:
                            try:
                                pix = page.get_pixmap(dpi=150)
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                tess_res = pytesseract.image_to_string(img).strip()
                                if tess_res and len(tess_res) > len(page_text):
                                    page_text = tess_res
                            except Exception as ocr_err:
                                logger.warning(f"[OCREngine] PDF Page {i+1} OCR scan warning: {ocr_err}")

                        extracted_pages.append(page_text)
                finally:
                    doc.close()
                    import gc
                    gc.collect()

                combined = "\n--- PAGE BREAK ---\n".join(extracted_pages).strip()
                result["text"] = combined
                result["success"] = bool(combined)

            elif ext in ("png", "jpg", "jpeg", "webp", "bmp", "tiff"):
                result["is_image"] = True

                temp_ocr_path = file_path
                clean_temp = False
                try:
                    with Image.open(file_path) as img:
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        
                        max_dim = 1400
                        if max(img.width, img.height) > max_dim:
                            ratio = max_dim / float(max(img.width, img.height))
                            new_size = (int(img.width * ratio), int(img.height * ratio))
                            img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
                            temp_ocr_path = f"{file_path}_ocr_temp.jpg"
                            img_resized.save(temp_ocr_path, format="JPEG", quality=85)
                            clean_temp = True

                    # 1. System PyTesseract OCR (<15MB RAM)
                    if PYTESSERACT_AVAILABLE:
                        try:
                            import shutil
                            tess_bin = shutil.which("tesseract") or "/usr/bin/tesseract"
                            if os.path.exists(tess_bin):
                                pytesseract.pytesseract.tesseract_cmd = tess_bin

                            with Image.open(temp_ocr_path) as ocr_img:
                                tess_text = pytesseract.image_to_string(ocr_img).strip()
                                if tess_text and len(tess_text) > 15:
                                    result["text"] = tess_text
                                    result["success"] = True
                                    result["engine"] = "pytesseract"
                                    logger.info(f"[OCREngine] PyTesseract extracted {len(tess_text)} chars from {file_path}")
                                    return result
                        except Exception as tess_err:
                            logger.warning(f"[OCREngine] PyTesseract failed on {file_path}: {tess_err}")

                finally:
                    if clean_temp and os.path.exists(temp_ocr_path):
                        try:
                            os.remove(temp_ocr_path)
                        except Exception:
                            pass
                    import gc
                    gc.collect()

                result["text"] = ""
                result["error"] = "Image OCR engine yielded no text"

        except Exception as e:
            logger.error(f"[OCREngine] OCR execution failed on {file_path}: {e}")
            result["error"] = str(e)

        return result

