from fastapi import APIRouter
from app.domains.notification.models import NotificationRequest, NotificationResult
from app.domains.notification.services.notification_coordinator import notification_coordinator

router = APIRouter(prefix="/notification", tags=["Notification"])

@router.post("/send", response_model=NotificationResult)
async def send_notification(request: NotificationRequest):
    """Manual gửi notification"""
    return await notification_coordinator.send_notification(request)

@router.get("/channels")
async def get_notification_channels():
    """Xem danh sách notification channels"""
    from app.domains.notification.models import NotificationChannel, NotificationType
    return {
        "channels": [ch.value for ch in NotificationChannel],
        "types": [nt.value for nt in NotificationType],
        "supported_combinations": {
            "lark_webhook": ["validation_alert", "custom_alert", "service_error"]
        }
    }

@router.get("/cache/status")
async def get_notification_cache_status():
    """Xem trạng thái notification cache"""
    from app.core.infrastructure.cache_service import cache_service
    cache_status = cache_service.get_cache_status()
    return cache_status.get('validation_cache', {})
