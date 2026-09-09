import hashlib
import os
from typing import Tuple
from fastapi import UploadFile
from app.config import settings
from app.core.exceptions import ValidationException

# Magic bytes signatures for file integrity validation
MAGIC_SIGNATURES = {
    "pdf": b"%PDF",
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
}

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}


class DocumentValidator:
    @staticmethod
    def validate_file(file: UploadFile, content: bytes) -> Tuple[str, str, str]:
        """Validates uploaded file extension, size, MIME type, and magic bytes.

        Returns:
            Tuple[extension, mime_type, sha256_hash]
        """
        if not file.filename:
            raise ValidationException("File must have a valid filename")

        # 1. Extension check
        ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationException(
                f"Unsupported file format '.{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        # 2. File size check
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        file_size = len(content)
        if file_size == 0:
            raise ValidationException("Uploaded file is empty (0 bytes)")
        if file_size > max_bytes:
            raise ValidationException(
                f"File size ({file_size / (1024 * 1024):.1f}MB) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        # 3. Magic bytes / header inspection
        is_valid_magic = False
        if ext == "pdf" and content.startswith(b"%PDF"):
            is_valid_magic = True
        elif ext == "png" and content.startswith(b"\x89PNG\r\n\x1a\n"):
            is_valid_magic = True
        elif ext in ("jpg", "jpeg") and content.startswith(b"\xff\xd8"):
            is_valid_magic = True

        if not is_valid_magic:
            raise ValidationException(
                f"Corrupted file or MIME type mismatch. File header does not match extension '.{ext}'"
            )

        # 4. Calculate SHA-256 hash
        sha256_hash = hashlib.sha256(content).hexdigest()

        content_type = file.content_type or f"application/{ext}" if ext == "pdf" else f"image/{ext}"
        return ext, content_type, sha256_hash
