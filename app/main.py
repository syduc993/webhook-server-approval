from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
import uvicorn

from app.config.settings import settings
from app.config.node_config import NODE_CONFIG, print_node_config_summary
from app.routers import webhook, debug, config, manual

app = FastAPI(
    title="Lark Approval QR Generator",
    description="Enhanced Auto QR Generator for Lark Approval Workflows",
    version="2.0.0"
)

# Include routers
app.include_router(webhook.router, prefix="", tags=["webhook"])
app.include_router(debug.router, prefix="/debug", tags=["debug"])
app.include_router(config.router, prefix="/config", tags=["config"])
app.include_router(manual.router, prefix="/manual", tags=["manual"])

@app.get("/")
async def root():
    return {
        "message": "Lark Webhook Server - Enhanced Auto QR with Validation", 
        "version": "2.0.0",
        "timestamp": datetime.now(),
        "node_config": {
            node_id: {
                "name": config["name"],
                "strategy": config["strategy"], 
                "advance_field": config["advance_field"],
                "payment_field": config["payment_field"]
            }
            for node_id, config in NODE_CONFIG.items()
        },
        "total_configured_nodes": len(NODE_CONFIG),
        "features": [
            "✨ Modular architecture for easy extension",
            "✨ Dual detection for advance/payment",
            "✨ Multiple node strategies support",
            "✨ Duplicate QR prevention (5-minute cache)",
            "✨ Validation service for amount checking",
            "✨ Alert system for workflow violations",
            "Auto generate VietQR based on node strategy",
            "Smart field detection per node type",
            "Upload QR image to Lark Approval API",
            "Create comment with QR image attachment"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy", "timestamp": datetime.now()}

if __name__ == "__main__":
    print("🚀 Starting Enhanced Lark Webhook Server...")
    print_node_config_summary()
    print("🎯 New Architecture Features:")
    print("   📁 Modular design for easy extension")
    print("   🔧 Validation service ready")
    print("   ⚠️  Alert system ready")
    print("   🚀 Cloud Run deployment ready")
    
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=settings.PORT,
        reload=settings.DEBUG
    )
