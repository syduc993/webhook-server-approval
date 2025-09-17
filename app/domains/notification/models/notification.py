from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum

class NotificationType(str, Enum):
    VALIDATION_ALERT = "validation_alert"
    CUSTOM_ALERT = "custom_alert"
    SERVICE_ERROR = "service_error"
    SYSTEM_NOTIFICATION = "system_notification"

class NotificationChannel(str, Enum):
    LARK_WEBHOOK = "lark_webhook"
    EMAIL = "email"
    SMS = "sms"

class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class NotificationRequest(BaseModel):
    notification_type: NotificationType
    channel: NotificationChannel
    title: str
    message: str
    instance_code: Optional[str] = None
    priority: NotificationPriority = NotificationPriority.NORMAL
    metadata: Optional[Dict[str, Any]] = None

class NotificationResult(BaseModel):
    success: bool
    notification_type: NotificationType
    channel: NotificationChannel
    instance_code: Optional[str] = None
    sent_at: Optional[str] = None
    cached: bool = False
    cache_hit: bool = False
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ValidationAlertRequest(BaseModel):
    instance_code: str
    serial_number: Optional[str] = None
    validation_errors: List[str]
    priority: NotificationPriority = NotificationPriority.HIGH

class CustomAlertRequest(BaseModel):
    title: str
    message: str
    instance_code: Optional[str] = None
    priority: NotificationPriority = NotificationPriority.NORMAL
