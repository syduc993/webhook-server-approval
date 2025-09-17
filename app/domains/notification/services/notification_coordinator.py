"""
Notification Coordinator - Bộ điều phối trung tâm cho tất cả kênh thông báo
"""
from typing import List, Dict, Any
from app.domains.notification.models import (
    NotificationRequest, NotificationResult, NotificationType, 
    NotificationChannel, ValidationAlertRequest, CustomAlertRequest
)
from app.domains.notification.services.lark_webhook_service import lark_webhook_service
from app.core.infrastructure.cache_service import cache_service


class NotificationCoordinator:
    """
    Bộ điều phối trung tâm cho tất cả các kênh thông báo.
    
    Class này hoạt động như một central hub để:
    1. Quản lý và điều phối các kênh thông báo khác nhau (Lark, Email, SMS, etc.)
    2. Ngăn chặn duplicate notifications thông qua caching mechanism
    3. Route notifications đến đúng service dựa trên channel và type
    4. Cung cấp interface thống nhất cho việc gửi thông báo
    5. Track và log kết quả gửi thông báo
    
    Supported channels:
    - LARK_WEBHOOK: Gửi thông báo qua Lark webhook
    - Có thể mở rộng thêm EMAIL, SMS, SLACK, etc.
    
    Supported notification types:
    - VALIDATION_ALERT: Cảnh báo validation errors
    - CUSTOM_ALERT: Cảnh báo tùy chỉnh
    - QR_GENERATION: Thông báo tạo QR (tương lai)
    
    Attributes:
        channels (Dict): Map từ notification channel đến service implementation
    """
    
    def __init__(self):
        """Khởi tạo NotificationCoordinator với các kênh thông báo được hỗ trợ."""
        # Mapping từ notification channel đến service implementation
        # Dễ dàng mở rộng thêm channels mới trong tương lai
        self.channels = {
            NotificationChannel.LARK_WEBHOOK: lark_webhook_service
            # Có thể thêm:
            # NotificationChannel.EMAIL: email_service,
            # NotificationChannel.SMS: sms_service,
            # NotificationChannel.SLACK: slack_service,
        }
    
    async def send_notification(self, request: NotificationRequest) -> NotificationResult:
        """
        Gửi thông báo qua kênh được chỉ định với tính năng chống trùng lặp.
        
        Đây là method chính của coordinator, thực hiện:
        1. Kiểm tra duplicate notifications dựa trên cache
        2. Validate và route đến đúng channel service  
        3. Gọi method phù hợp dựa trên notification type
        4. Cache kết quả để tránh duplicate trong tương lai
        5. Trả về kết quả chi tiết cho monitoring
        
        Args:
            request (NotificationRequest): Request chứa thông tin notification cần gửi
            
        Returns:
            NotificationResult: Kết quả gửi thông báo bao gồm:
                - success (bool): Trạng thái gửi thành công
                - notification_type: Loại thông báo
                - channel: Kênh đã sử dụng
                - instance_code: Mã instance liên quan
                - cached (bool): Có được cache không
                - cache_hit (bool): Có bị skip do cache không
                - error (str): Thông báo lỗi nếu có
                - metadata (Dict): Thông tin bổ sung
        """
        
        # Bước 1: Kiểm tra duplicate notifications dựa trên cache
        if request.instance_code:
            # Tạo cache key duy nhất cho combination của type và instance
            cache_key = f"{request.notification_type.value}_{request.instance_code}"
            
            print(f"🔍 Kiểm tra duplicate notification cho: {cache_key}")
            
            # Kiểm tra xem đã gửi notification tương tự gần đây chưa
            if cache_service.is_validation_alert_recently_sent(
                request.instance_code, 
                request.notification_type.value,
                cache_duration_minutes=10
            ):
                print(f"🔄 PHÁT HIỆN THÔNG BÁO TRÙNG LẶP: {cache_key}")
                print(f"   → BỎ QUA gửi thông báo để tránh spam")
                
                return NotificationResult(
                    success=True,  # Trả về success vì đã xử lý (cached)
                    notification_type=request.notification_type,
                    channel=request.channel,
                    instance_code=request.instance_code,
                    cached=True,
                    cache_hit=True,
                    metadata={
                        "reason": "duplicate_prevention",
                        "cache_key": cache_key,
                        "cache_duration_minutes": 10
                    }
                )
        
        # Bước 2: Validate và lấy channel service
        print(f"📡 Đang định tuyến đến kênh: {request.channel.value}")
        channel_service = self.channels.get(request.channel)
        
        if not channel_service:
            print(f"❌ Kênh không được hỗ trợ: {request.channel.value}")
            return NotificationResult(
                success=False,
                notification_type=request.notification_type,
                channel=request.channel,
                instance_code=request.instance_code,
                error=f"Kênh không được hỗ trợ: {request.channel.value}",
                metadata={
                    "available_channels": list(self.channels.keys())
                }
            )
        
        # Bước 3: Route đến method phù hợp dựa trên notification type
        print(f"🎯 Xử lý loại thông báo: {request.notification_type.value}")
        
        if request.notification_type == NotificationType.VALIDATION_ALERT:
            # Xử lý validation alert
            print(f"🔔 Tạo validation alert request...")
            alert_request = ValidationAlertRequest(
                instance_code=request.instance_code,
                validation_errors=[request.message],
                priority=request.priority
            )
            
            print(f"📤 Đang gửi validation alert qua {request.channel.value}...")
            result = await channel_service.send_validation_alert(alert_request)
        
        elif request.notification_type == NotificationType.CUSTOM_ALERT:
            # Xử lý custom alert
            print(f"🎨 Tạo custom alert request...")
            alert_request = CustomAlertRequest(
                title=request.title,
                message=request.message,
                instance_code=request.instance_code,
                priority=request.priority
            )
            
            print(f"📤 Đang gửi custom alert qua {request.channel.value}...")
            result = await channel_service.send_custom_alert(alert_request)
        
        else:
            # Notification type không được hỗ trợ
            print(f"❌ Loại thông báo không được hỗ trợ: {request.notification_type.value}")
            return NotificationResult(
                success=False,
                notification_type=request.notification_type,
                channel=request.channel,
                instance_code=request.instance_code,
                error=f"Loại thông báo không được hỗ trợ: {request.notification_type.value}",
                metadata={
                    "available_types": [nt.value for nt in NotificationType]
                }
            )
        
        # Bước 4: Xử lý kết quả và cache nếu thành công
        if result.success and request.instance_code:
            print(f"✅ Gửi thông báo thành công - đánh dấu cache")
            
            # Đánh dấu đã gửi trong cache để tránh duplicate
            cache_service.mark_validation_alert_as_sent(
                request.instance_code, 
                request.notification_type.value
            )
            
            print(f"💾 Đã lưu vào cache để tránh duplicate trong 10 phút")
        elif result.success:
            print(f"✅ Gửi thông báo thành công (không có instance_code để cache)")
        else:
            print(f"❌ Gửi thông báo thất bại: {getattr(result, 'error', 'Lỗi không xác định')}")
        
        return result


# Instance toàn cục của coordinator để sử dụng trong toàn bộ hệ thống
notification_coordinator = NotificationCoordinator()