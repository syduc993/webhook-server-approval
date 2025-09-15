from fastapi import APIRouter
from app.config.node_config import NODE_CONFIG, get_node_config, get_configured_node_ids
from app.services.cache_service import cache_service

router = APIRouter()

@router.get("/node-ids")
async def get_allowed_node_ids():
    """Xem danh sách allowed node IDs hiện tại"""
    return {
        "allowed_node_ids": get_configured_node_ids(),
        "total_allowed": len(NODE_CONFIG)
    }

@router.get("/nodes")
async def get_node_configuration():
    """Xem chi tiết NODE_CONFIG"""
    return {
        "node_config": NODE_CONFIG,
        "total_nodes": len(NODE_CONFIG),
        "configured_node_ids": list(NODE_CONFIG.keys()),
        "strategies": {
            node_id: config["strategy"] 
            for node_id, config in NODE_CONFIG.items()
        }
    }

@router.get("/nodes/{node_id}")
async def get_specific_node_config(node_id: str):
    """Xem config của một node cụ thể"""
    config = get_node_config(node_id)
    if config:
        return {
            "node_id": node_id,
            "config": config,
            "short_id": node_id[:8] + "..."
        }
    else:
        return {
            "error": f"Node ID {node_id} not found in configuration",
            "available_nodes": list(NODE_CONFIG.keys())
        }

@router.get("/cache/qr-status")
async def get_qr_cache_status():
    """Xem trạng thái cache QR generation"""
    return cache_service.get_cache_status()

@router.post("/cache/clear")
async def clear_qr_cache():
    """Clear cache QR generation manually"""
    return cache_service.clear_cache()
