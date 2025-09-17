import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Core imports
from app.core.bootstrap.application import app_bootstrap
from app.core.config.settings import settings

# Router imports
from app.core.routers.webhook import router as webhook_router
from app.core.routers.monitoring import router as monitoring_router
from app.domains.qr_generation.routers.qr import router as qr_router
from app.domains.validation.routers.notification import router as notification_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    # Startup
    print("🚀 Starting Lark Approval QR Generator (DDD Architecture)")
    await app_bootstrap.initialize()
    yield
    # Shutdown
    print("🛑 Shutting down application")

# Create FastAPI app
app = FastAPI(
    title="Lark Approval QR Generator", 
    description="Enhanced QR Generator với DDD Architecture",
    version="2.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(webhook_router, tags=["Webhook"])
app.include_router(monitoring_router, prefix="/monitoring", tags=["Monitoring"])
app.include_router(qr_router, prefix="/api", tags=["QR Generation"])  
app.include_router(notification_router, prefix="/api", tags=["Notification"])

@app.get("/")
async def root():
    """Root endpoint"""
    startup_info = app_bootstrap.get_startup_info()
    return {
        "message": "Lark Approval QR Generator API",
        "architecture": "Domain-Driven Design (DDD)",
        "version": "2.0.0",
        "status": "healthy" if startup_info["is_initialized"] else "initializing",
        "startup_info": startup_info
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
