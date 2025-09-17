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
    2. Trích xuất instance_code từ event data
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
        
        [NÂNG CẤP] Bổ sung logic kiểm tra trạng thái đơn. Sẽ bỏ qua xử lý
        nếu đơn ở trạng thái cuối cùng như REJECTED, CANCELED, DELETED.
        
        Đây là method chính của handler, hoạt động hoàn toàn độc lập
        và không phụ thuộc vào các service khác. Method sẽ:
        
        1. Validate dữ liệu đầu vào (instance_code)
        2. Lấy access token từ Lark service
        3. Gọi QRProcessor để xử lý business logic
        4. Trả về kết quả chi tiết cho monitoring
        
        Args:
            event_data (Dict): Dữ liệu sự kiện chứa thông tin phê duyệt.
                             Bắt buộc phải có 'instance_code'
        
        Returns:
            Dict: Kết quả xử lý bao gồm:
                - success (bool): Trạng thái xử lý thành công
                - message (str): Thông báo chi tiết kết quả
                - instance_code (str): Mã instance đã xử lý (nếu có)
                - service (str): Tên service thực hiện
        
        Raises:
            Exception: Các lỗi không xác định sẽ được bắt và trả về trong response
        """
        try:
            # Bước 1: Validate và trích xuất instance_code từ event data
            instance_code = event_data.get('instance_code')
            if not instance_code:
                print(f"❌ [QR Handler] Thiếu instance_code trong dữ liệu sự kiện")
                return {
                    "success": False,
                    "message": "Không tìm thấy instance_code trong dữ liệu sự kiện", 
                    "service": self.name
                }
            
            # [THÊM MỚI] Bắt đầu khối logic kiểm tra trạng thái
            FINAL_STATUSES = ['REJECTED', 'CANCELED', 'DELETED']

            # Trích xuất trạng thái từ dữ liệu gốc của sự kiện để tránh gọi API không cần thiết
            raw_data = event_data.get('raw_data', {})
            instance_status = raw_data.get('event', {}).get('object', {}).get('status')
            
            # Kiểm tra xem trạng thái của đơn có nằm trong danh sách cần bỏ qua không
            if instance_status and instance_status in FINAL_STATUSES:
                print(f"⏭️ [QR Handler] Bỏ qua instance {instance_code} do có trạng thái cuối cùng: {instance_status}")
                return {
                    "success": True, # Coi như thành công vì đã xử lý đúng (bỏ qua)
                    "message": f"Bỏ qua xử lý do trạng thái đơn là {instance_status}",
                    "instance_code": instance_code,
                    "service": self.name
                }
            # [THÊM MỚI] Kết thúc khối logic kiểm tra trạng thái
            
            print(f"🏦 [QR Handler] Dịch vụ QR đang xử lý instance: {instance_code} (Trạng thái: {instance_status or 'N/A'})")
            
            # Bước 2: Lấy access token để gọi Lark API
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
            
            # Bước 3: Gửi đến QRProcessor để xử lý business logic chính
            print(f"⚙️ Bắt đầu xử lý tạo QR cho {instance_code}...")
            result = await qr_processor.process_approval_with_qr_comment(
                instance_code, access_token
            )
            
            # Bước 4: Tạo response với thông tin chi tiết
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
            # Bắt tất cả exception không xác định để tránh crash service
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