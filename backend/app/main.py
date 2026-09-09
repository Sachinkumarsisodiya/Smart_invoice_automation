import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.logging import logger
from app.core.exceptions import (
    SmartInvoiceException,
    smartinvoice_exception_handler,
    global_exception_handler,
)
from app.database.seed import seed_database
from app.api.auth import router as auth_router
from app.api.invoices import router as invoices_router
from app.api.vendors import router as vendors_router
from app.api.expenses import router as expenses_router
from app.api.payments import router as payments_router
from app.api.dashboard import router as dashboard_router
from app.api.reports import router as reports_router
from app.api.notifications import router as notifications_router
from app.api.audit_logs import router as audit_logs_router
from app.api.system import router as system_router


from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.rate_limiter import limiter
from app.core.middleware import SecurityHeadersMiddleware, RequestCorrelationMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    
    # Ensure storage directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Auto-seed demo database in development
    try:
        seed_database()
    except Exception as e:
        logger.error(f"Auto-seed during startup encountered error: {e}")
        
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="Automate invoices. Track expenses. Never miss a payment.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Set SlowAPI state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register Middlewares (RequestCorrelation -> SecurityHeaders -> SlowAPI -> CORS)
app.add_middleware(RequestCorrelationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Exception Handlers
app.add_exception_handler(SmartInvoiceException, smartinvoice_exception_handler)
if not settings.DEBUG:
    app.add_exception_handler(Exception, global_exception_handler)

# Include API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(invoices_router, prefix=settings.API_V1_STR)
app.include_router(vendors_router, prefix=settings.API_V1_STR)
app.include_router(expenses_router, prefix=settings.API_V1_STR)
app.include_router(payments_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["Dashboard"])
app.include_router(reports_router, prefix=f"{settings.API_V1_STR}/reports", tags=["Reports"])
app.include_router(notifications_router, prefix=f"{settings.API_V1_STR}/notifications", tags=["Notifications"])
app.include_router(audit_logs_router, prefix=f"{settings.API_V1_STR}/audit-logs", tags=["Audit Logs"])
app.include_router(system_router, prefix=f"{settings.API_V1_STR}/system", tags=["System"])


@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "env": settings.APP_ENV
    }


@app.get("/", tags=["System"])
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API. Visit /docs for documentation.",
        "docs": "/docs"
    }
