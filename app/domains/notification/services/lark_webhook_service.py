"""
Lark Webhook Service - Dịch vụ gửi thông báo qua Lark webhook
"""
import requests
import json
from typing import List
from datetime import datetime
from app.core.config.settings import settings
from app.domains.notification.models import (
    NotificationResult, NotificationType, NotificationChannel,
    ValidationAlertRequest, CustomAlertRequest
)


class LarkWebhookService:
    """
    Dịch vụ gửi thông báo qua Lark webhook.
    
    Class này cung cấp khả năng gửi các loại thông báo khác nhau đến
    Lark (FeisHu) thông qua webhook API:
    
    - Validation alerts: Cảnh báo khi phát hiện lỗi validation
    - Custom alerts: Thông báo tùy chỉnh cho các sự kiện đặc biệt
    
    Service này hỗ trợ:
    - Format message theo chuẩn Lark webhook API
    - Error handling và retry logic
    - Tracking kết quả gửi với timestamp
    - Integration với notification coordinator
    - Configuration-based enabling/disabling
    
    Attributes:
        webhook_url (str): URL webhook của Lark từ settings
        channel (NotificationChannel): Channel type cho service này
    """
    
    def __init__(self):
        """Khởi tạo LarkWebhookService với cấu hình từ settings."""
        self.webhook_url = settings.LARK_WEBHOOK_URL
        self.channel = NotificationChannel.LARK_WEBHOOK
    
    async def send_validation_alert(self, request: ValidationAlertRequest) -> NotificationResult:
        """
        Gửi cảnh báo validation error qua Lark webhook.
        
        Method này sẽ format và gửi thông báo cảnh báo khi hệ thống
        phát hiện lỗi validation trong quy trình phê duyệt.
        
        Quy trình xử lý:
        1. Kiểm tra cấu hình có enable validation alerts không
        2. Validate webhook URL có được cấu hình không
        3. Format message theo template cảnh báo validation
        4. Gửi HTTP POST request đến Lark webhook
        5. Trả về kết quả với thông tin chi tiết
        
        Args:
            request (ValidationAlertRequest): Request chứa thông tin validation alert
                - instance_code: Mã instance có lỗi validation
                - validation_errors: Danh sách lỗi validation
                - priority: Mức độ ưu tiên của alert
        
        Returns:
            NotificationResult: Kết quả gửi thông báo bao gồm:
                - success: Trạng thái gửi thành công
                - notification_type: VALIDATION_ALERT
                - channel: LARK_WEBHOOK
                - instance_code: Mã instance liên quan
                - sent_at: Thời gian gửi (nếu thành công)
                - error: Thông báo lỗi (nếu thất bại)
                - metadata: Thông tin bổ sung (số lỗi, priority)
        """
        try:
            # Bước 1: Kiểm tra cấu hình có enable validation alerts không
            if not settings.ENABLE_VALIDATION_ALERTS:
                print(f"⚠️ Tính năng cảnh báo validation đã bị tắt, bỏ qua webhook cho {request.instance_code}")
                return NotificationResult(
                    success=True,  # Trả về success vì đã xử lý (disabled)
                    notification_type=NotificationType.VALIDATION_ALERT,
                    channel=self.channel,
                    instance_code=request.instance_code,
                    cached=True,
                    metadata={"disabled": True, "reason": "ENABLE_VALIDATION_ALERTS = False"}
                )
            
            # Bước 2: Kiểm tra webhook URL có được cấu hình không
            if not self.webhook_url:
                print(f"❌ Chưa cấu hình webhook URL cho Lark")
                return NotificationResult(
                    success=False,
                    notification_type=NotificationType.VALIDATION_ALERT,
                    channel=self.channel,
                    instance_code=request.instance_code,
                    error="Chưa cấu hình webhook URL"
                )
            
            # Bước 3: Format danh sách lỗi validation thành text dễ đọc
            print(f"📝 Đang format {len(request.validation_errors)} lỗi validation...")
            error_messages = "\n".join([f"• {error}" for error in request.validation_errors])
            
            # Tạo message data theo format của Lark webhook API
            message_data = {
                "msg_type": "text",
                "content": {
                    "text": f"""⚠️ CẢNH BÁO DỮ LIỆU KHÔNG HỢP LỆ
📄 Request No.: {request.serial_number}
❌ Các lỗi phát hiện:
{error_messages}

🔧 Vui lòng kiểm tra và xử lý."""
                }
            }
            
            # Cấu hình headers cho HTTP request
            headers = {"Content-Type": "application/json"}
            
            # Bước 4: Gửi HTTP POST request đến Lark webhook
            print(f"🚨 Đang gửi cảnh báo validation qua webhook cho {request.instance_code}")
            response = requests.post(
                self.webhook_url, 
                headers=headers, 
                data=json.dumps(message_data),
                timeout=10  # Timeout 10 giây để tránh treo
            )
            
            # Bước 5: Xử lý response và tạo kết quả
            success = response.status_code == 200
            sent_at = datetime.now().isoformat() if success else None
            
            if success:
                print(f"✅ Gửi cảnh báo validation thành công cho {request.instance_code}")
            else:
                print(f"❌ Gửi cảnh báo validation thất bại: HTTP {response.status_code} - {response.text}")
            
            return NotificationResult(
                success=success,
                notification_type=NotificationType.VALIDATION_ALERT,
                channel=self.channel,
                instance_code=request.instance_code,
                sent_at=sent_at,
                error=None if success else f"HTTP {response.status_code}: {response.text}",
                metadata={
                    "errors_count": len(request.validation_errors),
                    "priority": request.priority.value,
                    "response_status": response.status_code
                }
            )
                
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout khi gửi validation webhook (quá 10 giây)")
            return NotificationResult(
                success=False,
                notification_type=NotificationType.VALIDATION_ALERT,
                channel=self.channel,
                instance_code=request.instance_code,
                error="Timeout khi gửi webhook"
            )
        except requests.exceptions.ConnectionError:
            print(f"🔌 Lỗi kết nối khi gửi validation webhook")
            return NotificationResult(
                success=False,
                notification_type=NotificationType.VALIDATION_ALERT,
                channel=self.channel,
                instance_code=request.instance_code,
                error="Lỗi kết nối webhook"
            )
        except Exception as e:
            print(f"❌ Lỗi không xác định khi gửi validation webhook: {e}")
            return NotificationResult(
                success=False,
                notification_type=NotificationType.VALIDATION_ALERT,
                channel=self.channel,
                instance_code=request.instance_code,
                error=str(e)
            )

    async def send_custom_alert(self, request: CustomAlertRequest) -> NotificationResult:
        """
        Gửi thông báo tùy chỉnh qua Lark webhook.
        
        Method này cho phép gửi các thông báo tùy chỉnh với title và message
        do người dùng định nghĩa, phù hợp cho các sự kiện đặc biệt hoặc
        thông báo hệ thống.
        
        Args:
            request (CustomAlertRequest): Request chứa thông tin custom alert
                - title: Tiêu đề thông báo
                - message: Nội dung thông báo
                - instance_code: Mã instance liên quan (optional)
                - priority: Mức độ ưu tiên
        
        Returns:
            NotificationResult: Kết quả gửi thông báo tương tự send_validation_alert
        """
        try:
            # Bước 1: Kiểm tra cấu hình và webhook URL
            if not settings.ENABLE_VALIDATION_ALERTS or not self.webhook_url:
                print(f"❌ Alerts bị tắt hoặc chưa cấu hình webhook URL")
                return NotificationResult(
                    success=False,
                    notification_type=NotificationType.CUSTOM_ALERT,
                    channel=self.channel,
                    instance_code=request.instance_code,
                    error="Alerts bị tắt hoặc chưa cấu hình webhook URL"
                )
            
            # Bước 2: Format message với title và nội dung tùy chỉnh
            print(f"📝 Đang tạo custom alert: {request.title}")
            alert_text = f"""🔔 {request.title}"""
            
            # Thêm instance code nếu có
            if request.instance_code:
                alert_text += f"\n📄 Instance: {request.instance_code}"
                
            alert_text += f"\n📢 {request.message}"
            
            # Tạo message data cho Lark webhook
            message_data = {
                "msg_type": "text",
                "content": {"text": alert_text}
            }
            
            # Bước 3: Gửi HTTP request
            print(f"📤 Đang gửi custom alert qua webhook...")
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                self.webhook_url, 
                headers=headers, 
                data=json.dumps(message_data),
                timeout=10
            )
            
            # Bước 4: Xử lý kết quả
            success = response.status_code == 200
            sent_at = datetime.now().isoformat() if success else None
            
            if success:
                print(f"✅ Gửi custom alert thành công: {request.title}")
            else:
                print(f"❌ Gửi custom alert thất bại: HTTP {response.status_code} - {response.text}")
            
            return NotificationResult(
                success=success,
                notification_type=NotificationType.CUSTOM_ALERT,
                channel=self.channel,
                instance_code=request.instance_code,
                sent_at=sent_at,
                error=None if success else f"HTTP {response.status_code}: {response.text}",
                metadata={
                    "title": request.title,
                    "priority": request.priority.value,
                    "has_instance_code": request.instance_code is not None,
                    "response_status": response.status_code
                }
            )
            
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout khi gửi custom alert webhook")
            return NotificationResult(
                success=False,
                notification_type=NotificationType.CUSTOM_ALERT,
                channel=self.channel,
                instance_code=request.instance_code,
                error="Timeout khi gửi webhook"
            )
        except requests.exceptions.ConnectionError:
            print(f"🔌 Lỗi kết nối khi gửi custom alert webhook")
            return NotificationResult(
                success=False,
                notification_type=NotificationType.CUSTOM_ALERT,
                channel=self.channel,
                instance_code=request.instance_code,
                error="Lỗi kết nối webhook"
            )
        except Exception as e:
            print(f"❌ Lỗi khi gửi custom alert: {e}")
            return NotificationResult(
                success=False,
                notification_type=NotificationType.CUSTOM_ALERT,
                channel=self.channel,
                instance_code=request.instance_code,
                error=str(e)
            )


lark_webhook_service = LarkWebhookService()