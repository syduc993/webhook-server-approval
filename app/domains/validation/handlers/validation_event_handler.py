"""
Validation Event Handler - Bộ xử lý sự kiện validation cho hệ thống phê duyệt
"""
from typing import Dict, List, Optional
import json
from app.domains.validation.services import validation_service
from app.core.infrastructure import lark_service
from app.domains.notification.services import lark_webhook_service
from app.core.infrastructure import cache_service

class ValidationEventHandler:
    """
    Bộ xử lý sự kiện validation cho hệ thống phê duyệt.
    
    Class này chịu trách nhiệm:
    1. Nhận và xử lý các sự kiện phê duyệt để validation
    2. Chạy các quy tắc validation trên dữ liệu form và workflow
    3. Gửi cảnh báo qua webhook khi phát hiện vấn đề
    4. Ngăn chặn duplicate alerts để tránh spam notification
    5. Xử lý lỗi và gửi error alerts khi cần thiết
    
    Attributes:
        name (str): Tên định danh của service
        webhook_service: Service gửi webhook notifications
    """
    
    def __init__(self):
        """Khởi tạo ValidationEventHandler với webhook service."""
        self.name = "Validation_Service"
        self.webhook_service = lark_webhook_service

    async def handle_approval_event(self, event_data: Dict) -> Dict:
        """
        Xử lý sự kiện phê duyệt để thực hiện validation với cơ chế anti-spam nâng cao.

        [NÂNG CẤP] Bổ sung logic nhận diện quy trình qua approval_code.
        """
        instance_code = event_data.get('instance_code')
        approval_code = event_data.get('approval_code')

        if not instance_code:
            return {"success": False, "message": "Không tìm thấy instance_code", "service": self.name}
        
        if not approval_code:
            return {
                "success": False, 
                "message": f"Không tìm thấy approval_code cho instance {instance_code}", 
                "service": self.name
            }

        try:

            FINAL_STATUSES = ['REJECTED', 'CANCELED', 'DELETED']
            raw_data = event_data.get('raw_data', {})
            instance_status = raw_data.get('event', {}).get('object', {}).get('status')
            event_body = raw_data.get('event', {})
            if not instance_status:
                instance_status = event_body.get('status')

            if instance_status and instance_status in FINAL_STATUSES:
                print(f"⏭️ [Validation Handler] Bỏ qua instance {instance_code} do có trạng thái cuối cùng: {instance_status}")
                return {
                    "success": True,
                    "message": f"Bỏ qua validation do trạng thái đơn là {instance_status}",
                    "instance_code": instance_code,
                    "webhook_sent": False,
                    "service": self.name
                }
            
            print(f"🔍 [Validation Handler] Dịch vụ Validation đang xử lý: {instance_code} (Workflow: {approval_code})")
            
            # Lấy dữ liệu từ Lark (giữ nguyên)
            access_token = await lark_service.get_access_token()
            if not access_token:
                return {"success": False, "message": "Không thể lấy access token", "service": self.name}

            api_response = await lark_service.get_approval_instance(instance_code, access_token)
            if not api_response or 'data' not in api_response:
                return {"success": False, "message": "Không thể lấy dữ liệu instance", "service": self.name}
            
            serial_number = api_response.get('data', {}).get('serial_number')
            form_data = json.loads(api_response['data'].get('form', '[]'))
            task_list = api_response['data'].get('task_list', [])
            
            validation_results = validation_service.run_all_validations(
                approval_code=approval_code, # <-- Tham số mới
                form_data=form_data, 
                task_list=task_list, 
                node_id="dummy_node_id" 
            )
            invalid_results = [r for r in validation_results if not r.is_valid]
            
            if not invalid_results:
                print("✅ [Validation Handler] Tất cả validation đều thành công.")
                return {
                    "success": True, "message": "Tất cả validation đều thành công",
                    "webhook_sent": False, "webhook_skipped_count": 0,
                    "service": self.name
                }
            
            alerts_to_send = []
            skipped_count = 0
            
            print(f"⚠️ [Validation Handler] Phát hiện {len(invalid_results)} vấn đề. Đang kiểm tra cache anti-spam...")
            for result in invalid_results:
                specific_error_key = f"{result.validation_type.value}_{hash(result.message)}"
                
                if cache_service.is_validation_alert_recently_sent(
                    instance_code, specific_error_key, cache_duration_minutes=10
                ):
                    print(f"  🔄 Bỏ qua (đã cache): {result.message[:80]}...")
                    skipped_count += 1
                else:
                    print(f"  🆕 Cần gửi cảnh báo cho: {result.message[:80]}...")
                    alerts_to_send.append(result)

            webhook_sent = False
            if alerts_to_send:
                error_messages = [r.message for r in alerts_to_send]
                print(f"📨 [Validation Handler] Đang gửi {len(error_messages)} cảnh báo mới qua webhook...")
                
                webhook_sent = await self._send_validation_alert(instance_code, error_messages, serial_number)
                
                if webhook_sent:
                    print("✅ [Validation Handler] Gửi webhook thành công. Đang cập nhật cache...")
                    for result in alerts_to_send:
                        specific_error_key = f"{result.validation_type.value}_{hash(result.message)}"
                        cache_service.mark_validation_alert_as_sent(instance_code, specific_error_key)
                        print(f"  🔒 Đã cache cho: {result.message[:80]}...")
                else:
                    print("❌ [Validation Handler] Gửi webhook thất bại.")
            else:
                print("✅ [Validation Handler] Không có cảnh báo mới nào cần gửi. Tất cả đã được cache.")

            return {
                "success": True,
                "message": f"Hoàn thành validation. {len(alerts_to_send)} cảnh báo mới đã được gửi. {skipped_count} cảnh báo bị bỏ qua do cache.",
                "alerts_sent_count": len(alerts_to_send),
                "webhook_sent": webhook_sent,
                "webhook_skipped_count": skipped_count,
                "validation_details": [r.dict() for r in validation_results],
                "service": self.name
            }
            
        except Exception as e:
            # Xử lý lỗi hệ thống (giữ nguyên)
            print(f"❌ [Validation Handler] Lỗi nghiêm trọng trong Validation Service: {str(e)}")
            return {
                "success": False,
                "message": f"Lỗi Validation Service: {str(e)}",
                "service": self.name
            }

    async def _send_validation_alert(self, instance_code: str, error_messages: List[str], serial_number: Optional[str]) -> bool:
        """Gửi cảnh báo validation qua webhook service."""
        try:
            from app.domains.notification.models import ValidationAlertRequest, NotificationPriority
            request = ValidationAlertRequest(
                instance_code=instance_code,
                serial_number=serial_number,
                validation_errors=error_messages,
                priority=NotificationPriority.HIGH
            )
            result = await self.webhook_service.send_validation_alert(request)
            return result.success
        except Exception as e:
            print(f"❌ Lỗi khi gửi validation alert: {e}")
            return False

    async def _send_error_alert(self, instance_code: str, error_message: str) -> bool:
        """Gửi cảnh báo lỗi hệ thống qua webhook service."""
        try:
            from app.domains.notification.models import CustomAlertRequest
            alert_request = CustomAlertRequest(
                 title="LỖI VALIDATION SERVICE",
                 message=f"Lỗi xử lý validation cho {instance_code}: {error_message}",
                 instance_code=instance_code
            )
            result = await self.webhook_service.send_custom_alert(alert_request)
            return result.success
        except Exception as e:
            print(f"❌ Lỗi khi gửi error alert: {e}")
            return False


validation_event_handler = ValidationEventHandler()