import requests
from urllib.parse import quote
from PIL import Image
from io import BytesIO
from app.core.config.settings import settings
from app.domains.qr_generation.models import QRType


class VietQRService:
    """
    Dịch vụ tạo mã QR thanh toán VietQR.
    
    Class này cung cấp các chức năng để tạo mã QR VietQR thông qua API,
    xử lý hình ảnh và tạo mô tả phù hợp cho từng loại giao dịch.
    
    VietQR là hệ thống thanh toán QR code chuẩn của Việt Nam, cho phép
    tạo mã QR chứa thông tin ngân hàng, số tiền và nội dung chuyển khoản.
    
    Attributes:
        base_url (str): URL cơ sở của VietQR API từ settings
    """

    def __init__(self):
        """Khởi tạo VietQRService với URL API từ cấu hình."""
        self.base_url = settings.VIETQR_BASE_URL
    
    def create_qr_in_memory(self, bank_id: str, account_no: str, amount: int, 
                           description: str, account_name: str, 
                           template: str = None) -> BytesIO:
        """
        Tạo mã QR VietQR với thông tin thanh toán và trả về dữ liệu ảnh trong bộ nhớ.
        
        Phương thức này sẽ:
        1. Tạo URL request đến VietQR API với các tham số đã mã hóa
        2. Gửi HTTP request để lấy hình ảnh QR
        3. Xử lý hình ảnh bằng PIL (chuyển đổi format nếu cần)
        4. Trả về BytesIO object chứa dữ liệu PNG
        
        Args:
            bank_id (str): Mã ngân hàng (ví dụ: 970422 cho MB Bank)
            account_no (str): Số tài khoản thụ hưởng
            amount (int): Số tiền giao dịch (đơn vị: VND)
            description (str): Nội dung chuyển khoản (sẽ được mã hóa URL)
            account_name (str): Tên chủ tài khoản (sẽ được mã hóa URL)
            template (str, optional): Template QR. Defaults to settings.VIETQR_TEMPLATE
        
        Returns:
            BytesIO: Dữ liệu ảnh QR dạng PNG trong bộ nhớ, hoặc None nếu có lỗi
            
        Raises:
            requests.exceptions.RequestException: Lỗi khi gọi API
            PIL.UnidentifiedImageError: Lỗi khi xử lý hình ảnh
        """
        # Sử dụng template mặc định nếu không được chỉ định
        if template is None:
            template = settings.VIETQR_TEMPLATE
        
        # Mã hóa URL cho các tham số tiếng Việt để tránh lỗi encoding
        encoded_desc = quote(description)
        encoded_name = quote(account_name)
        
        # Tạo URL request theo format của VietQR API
        url = (f"{self.base_url}/{bank_id}-{account_no}-{template}.jpg?"
               f"amount={amount}&addInfo={encoded_desc}&accountName={encoded_name}")
        
        print(f"🌐 URL VietQR: {url}")
        
        try:
            # Gửi HTTP GET request với timeout để tránh treo
            print(f"📡 Đang gửi yêu cầu tạo QR đến VietQR API...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raise exception nếu HTTP status code không thành công
            
            print(f"✅ Nhận được dữ liệu QR từ API ({len(response.content)} bytes)")
            
            # Mở và xử lý hình ảnh từ response content
            image = Image.open(BytesIO(response.content))
            print(f"🖼️ Đã tải ảnh QR - Kích thước: {image.size}, Mode: {image.mode}")
            
            # Chuyển đổi sang RGB nếu ảnh có mode không tương thích với PNG
            # RGBA (có alpha channel), LA (grayscale + alpha), P (palette mode)
            if image.mode in ('RGBA', 'LA', 'P'):
                print(f"🔄 Chuyển đổi ảnh từ mode {image.mode} sang RGB")
                image = image.convert('RGB')
            
            # Tạo BytesIO buffer để lưu ảnh PNG
            img_buffer = BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)  # Reset con trở về đầu buffer để đọc từ đầu
            
            print(f"✅ Tạo mã VietQR thành công trong bộ nhớ")
            print(f"📦 Kích thước buffer: {img_buffer.getbuffer().nbytes} bytes")
            return img_buffer
            
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout khi gọi VietQR API (quá 10 giây)")
            return None
        except requests.exceptions.ConnectionError:
            print(f"🔌 Lỗi kết nối đến VietQR API")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"🚫 Lỗi HTTP từ VietQR API: {e}")
            print(f"    Status code: {response.status_code}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Lỗi request khi gọi VietQR API: {e}")
            return None
        except Exception as e:
            print(f"❌ Lỗi không xác định khi xử lý VietQR: {e}")
            return None

    def generate_qr_description(self, qr_type: str, instance_code: str) -> str:
        """
        Tạo mô tả (nội dung chuyển khoản) cho mã QR dựa trên loại giao dịch.
        
        Mô tả sẽ được hiển thị trong nội dung chuyển khoản của ngân hàng,
        giúp người nhận dễ dàng nhận biết mục đích giao dịch.
        
        Args:
            qr_type (str): Loại QR code ('advance', 'payment', hoặc giá trị khác)
            instance_code (str): Mã đơn phê duyệt để tham chiếu
            
        Returns:
            str: Nội dung mô tả cho QR code
            
        Examples:
            >>> generate_qr_description('advance', 'AP123456')
            'Tam ung don AP123456'
            
            >>> generate_qr_description('payment', 'AP123456') 
            'Thanh toan don AP123456'
            
            >>> generate_qr_description('other', 'AP123456')
            'Don AP123456'
        """
        # Xác định mô tả dựa trên loại QR
        if qr_type == 'advance':
            description = f"Tam ung don {instance_code}"
            print(f"📝 Tạo mô tả QR tạm ứng: {description}")
        elif qr_type == 'payment':
            description = f"Thanh toan don {instance_code}"
            print(f"📝 Tạo mô tả QR thanh toán: {description}")
        else:
            # Fallback cho các loại khác
            description = f"Don {instance_code}"
            print(f"📝 Tạo mô tả QR chung: {description}")
            
        return description

vietqr_service = VietQRService()