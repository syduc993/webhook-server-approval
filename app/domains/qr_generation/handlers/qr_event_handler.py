from typing import Dict
from app.core.infrastructure.lark_service import lark_service
from app.domains.qr_generation.services.qr_processor import qr_processor

class QREventHandler:
    """
    Bộ xử lý sự kiện tạo mã QR cho hệ thống phê duyệt Lark.
    
    Class này hoạt động như một event handler độc lập, nhận và xử lý
    các sự kiện phê duyệt để tự động tạo mã VietQR tương ứng.
    
    Quy trình xử lý:
    1. Nhận sự kiện phê duyệt từ hệ thống
    2. Trích xuất instance_code và approval_code từ event data
    3. Lấy access token để gọi Lark API
    4. Gửi đến QRProcessor để xử lý tạo QR
    5. Trả về kết quả xử lý
    
    Attributes:
        name (str): Tên định danh của service ("QR_Generator")
    """
    
    def __init__(self):
        """Khởi tạo QREventHandler với tên service."""
        self.name = "QR_Generator"
    
    async def handle_approval_event(self, event_data: Dict) -> Dict:
        """
        Xử lý sự kiện phê duyệt để tạo mã QR tự động.
        
        [NÂNG CẤP] Bổ sung logic kiểm tra trạng thái đơn và nhận diện quy trình
        qua approval_code.
        
        Args:
            event_data (Dict): Dữ liệu sự kiện chứa thông tin phê duyệt.
                             Bắt buộc phải có 'instance_code' và 'approval_code'.
        
        Returns:
            Dict: Kết quả xử lý chi tiết.
        """
        try:
            # [THAY ĐỔI] Trích xuất cả instance_code và approval_code từ event
            instance_code = event_data.get('instance_code')
            approval_code = event_data.get('approval_code')

            if not instance_code:
                print(f"❌ [QR Handler] Thiếu instance_code trong dữ liệu sự kiện")
                return {
                    "success": False,
                    "message": "Không tìm thấy instance_code trong dữ liệu sự kiện", 
                    "service": self.name
                }
            
            # [THÊM MỚI] Kiểm tra sự tồn tại của approval_code
            if not approval_code:
                print(f"❌ [QR Handler] Thiếu approval_code trong dữ liệu sự kiện cho instance: {instance_code}")
                return {
                    "success": False,
                    "message": "Không tìm thấy approval_code trong dữ liệu sự kiện",
                    "instance_code": instance_code,
                    "service": self.name
                }

            # Logic kiểm tra trạng thái đơn (giữ nguyên)
            FINAL_STATUSES = ['REJECTED', 'CANCELED', 'DELETED']
            raw_data = event_data.get('raw_data', {})
            instance_status = raw_data.get('event', {}).get('object', {}).get('status')
            
            if instance_status and instance_status in FINAL_STATUSES:
                print(f"⏭️ [QR Handler] Bỏ qua instance {instance_code} do có trạng thái cuối cùng: {instance_status}")
                return {
                    "success": True,
                    "message": f"Bỏ qua xử lý do trạng thái đơn là {instance_status}",
                    "instance_code": instance_code,
                    "service": self.name
                }
            
            # [THAY ĐỔI] Cập nhật log để hiển thị cả approval_code
            print(f"🏦 [QR Handler] Dịch vụ QR đang xử lý instance: {instance_code} (Workflow: {approval_code})")
            
            # Lấy access token (giữ nguyên)
            print(f"🔑 Đang lấy access token từ Lark...")
            access_token = await lark_service.get_access_token()
            if not access_token:
                print(f"❌ Không thể lấy access token từ Lark")
                return {
                    "success": False,
                    "message": "Không thể lấy access token từ Lark",
                    "service": self.name
                }
            
            print(f"✅ Đã lấy access token thành công")
            
            # [THAY ĐỔI] Truyền approval_code vào service xử lý logic nghiệp vụ
            print(f"⚙️ Bắt đầu xử lý tạo QR cho {instance_code}...")
            result = await qr_processor.process_approval_with_qr_comment(
                instance_code, approval_code, access_token
            )
            
            # Xử lý kết quả trả về (giữ nguyên)
            if result:
                print(f"✅ [QR Handler] Hoàn thành xử lý QR cho {instance_code}")
                return {
                    "success": True,
                    "message": f"Xử lý QR hoàn thành thành công cho {instance_code}",
                    "instance_code": instance_code,
                    "service": self.name
                }
            else:
                print(f"❌ [QR Handler] Xử lý QR thất bại cho {instance_code}")
                return {
                    "success": False,
                    "message": f"Xử lý QR thất bại cho {instance_code}",
                    "instance_code": instance_code,
                    "service": self.name
                }
            
        except Exception as e:
            # Xử lý lỗi (giữ nguyên)
            print(f"❌ Lỗi không xác định trong QR Service: {str(e)}")
            import traceback
            print(f"📋 Chi tiết lỗi:\n{traceback.format_exc()}")
            
            return {
                "success": False,
                "message": f"Lỗi QR Service: {str(e)}",
                "service": self.name,
                "error_type": type(e).__name__
            }

qr_event_handler = QREventHandler()