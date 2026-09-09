from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.core.logging import logger


class SmartInvoiceException(Exception):
    """Base application exception."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, error_code: str = "BAD_REQUEST"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class NotFoundException(SmartInvoiceException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND, error_code="NOT_FOUND")


class UnauthorizedException(SmartInvoiceException):
    def __init__(self, message: str = "Invalid authentication credentials"):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED, error_code="UNAUTHORIZED")


class ForbiddenException(SmartInvoiceException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN, error_code="FORBIDDEN")


class ConflictException(SmartInvoiceException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT, error_code="CONFLICT")


class ValidationException(SmartInvoiceException):
    def __init__(self, message: str = "Validation failed", details: dict | None = None):
        self.details = details or {}
        super().__init__(message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, error_code="VALIDATION_ERROR")


async def smartinvoice_exception_handler(request: Request, exc: SmartInvoiceException):
    logger.warning(f"Handled error [{exc.error_code}] on {request.method} {request.url.path}: {exc.message}")
    content = {
        "success": False,
        "error": {
            "code": exc.error_code,
            "message": exc.message
        }
    }
    if hasattr(exc, "details") and exc.details:
        content["error"]["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=content)


async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later."
            }
        }
    )
