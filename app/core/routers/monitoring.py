from fastapi import APIRouter
from app.core.infrastructure.event_bus import event_bus
from app.core.bootstrap.application import app_bootstrap

router = APIRouter()

@router.get("/system/health")
async def get_system_health():
    """System health check với DDD architecture"""
    return {
        "status": "healthy" if app_bootstrap.is_initialized else "initializing",
        "application": app_bootstrap.get_startup_info(),
        "event_system": {
            "total_event_types": len(event_bus.handlers),
            "registered_events": list(event_bus.handlers.keys()),
            "total_handlers": sum(len(handlers) for handlers in event_bus.handlers.values())
        }
    }

@router.get("/events/history")
async def get_event_history(limit: int = 50):
    """Event processing history"""
    return {
        "recent_events": event_bus.get_event_history(limit),
        "handlers": {
            event_type: [handler.__name__ for handler in handlers]
            for event_type, handlers in event_bus.handlers.items()
        }
    }

@router.post("/events/test/{instance_code}")
async def test_event_processing(instance_code: str):
    """Test event processing system"""
    event_data = {
        "instance_code": instance_code,
        "event_type": "test_event",
        "timestamp": "manual_test"
    }
    
    results = await event_bus.publish("approval.instance.updated", event_data)
    
    return {
        "test_instance": instance_code,
        "handlers_executed": len(results),
        "results": results,
        "architecture": "DDD"
    }
