# FILE: app/api/main.py (Đã sửa lỗi)

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import bootstrap
from app.core.bootstrap.application import app_bootstrap

# Import all domain routers
from app.domains.qr_generation.routers.qr import router as qr_router
from app.domains.validation.routers.validation import router as validation_router
# ĐÃ SỬA: Đường dẫn import cho notification_router đã được sửa lại cho đúng
from app.domains.validation.routers.notification import router as notification_router

# Import core routers (legacy + system)
from app.core.routers.webhook import router as webhook_router
from app.core.routers.monitoring import router as monitoring_router
# ĐÃ XÓA: Các router không tồn tại đã bị xóa
# from app.core.routers.config import router as config_router
# from app.core.routers.debug import router as debug_router
# from app.core.routers.manual import router as manual_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with bootstrap"""
    try:
        # Startup
        print("🚀 Application startup...")
        await app_bootstrap.initialize()
        yield
    except Exception as e:
        print(f"❌ Application startup failed: {e}")
        raise
    finally:
        # Shutdown
        print("🔄 Application shutdown...")

app = FastAPI(
    title="Lark Approval System - DDD Architecture",
    description="Domain-driven design implementation with QR generation, validation, and notification domains",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include domain routers
app.include_router(qr_router, prefix="/api/v2")
app.include_router(validation_router, prefix="/api/v2")  
app.include_router(notification_router, prefix="/api/v2")

# Include core routers
app.include_router(webhook_router)  # Root level for webhook compatibility
app.include_router(monitoring_router, prefix="/system")
# ĐÃ XÓA: Xóa các dòng include_router cho các router không tồn tại
# app.include_router(config_router, prefix="/config")
# app.include_router(debug_router, prefix="/debug")
# app.include_router(manual_router, prefix="/manual")

# Root endpoints
@app.get("/")
async def root():
    """API root with system information"""
    return {
        "service": "Lark Approval System",
        "architecture": "DDD (Domain-Driven Design)",
        "version": "2.0.0",
        "domains": ["qr_generation", "validation", "notification"],
        "status": "healthy" if app_bootstrap.is_initialized else "initializing",
        "endpoints": {
            "api_v2": "/api/v2",
            "webhook": "/webhook",
            "system": "/system",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not app_bootstrap.is_initialized:
        raise HTTPException(status_code=503, detail="Application not fully initialized")
    
    return {
        "status": "healthy",
        "application": app_bootstrap.get_startup_info()
    }