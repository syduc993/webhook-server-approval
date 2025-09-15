import requests
from urllib.parse import quote
from PIL import Image
from io import BytesIO
from app.config.settings import settings

class VietQRService:
    def __init__(self):
        self.base_url = settings.VIETQR_BASE_URL
    
    def create_qr_in_memory(self, bank_id: str, account_no: str, amount: int, 
                           description: str, account_name: str, 
                           template: str = None) -> BytesIO:
        """
        Tạo QR code với số tiền và nội dung, trả về BytesIO object
        
        Args:
            bank_id (str): Mã ngân hàng
            account_no (str): Số tài khoản   
            amount (int): Số tiền (VND)
            description (str): Nội dung chuyển khoản
            account_name (str): Tên tài khoản
            template (str): Template (mặc định từ settings)
        
        Returns:
            BytesIO: QR code image data hoặc None nếu lỗi
        """
        if template is None:
            template = settings.VIETQR_TEMPLATE
            
        encoded_desc = quote(description)
        encoded_name = quote(account_name)
        
        url = (f"{self.base_url}/{bank_id}-{account_no}-{template}.jpg?"
               f"amount={amount}&addInfo={encoded_desc}&accountName={encoded_name}")
        
        print(f"VietQR URL: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Mở ảnh từ response
            image = Image.open(BytesIO(response.content))
            
            # Chuyển đổi sang RGB nếu cần
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Lưu vào BytesIO
            img_buffer = BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            print(f"✅ Tạo VietQR code thành công trong bộ nhớ")
            return img_buffer
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Lỗi khi tải VietQR code: {e}")
            return None
        except Exception as e:
            print(f"❌ Lỗi xử lý VietQR: {e}")
            return None

    def generate_qr_description(self, qr_type: str, instance_code: str) -> str:
        """
        Tạo description cho QR code dựa trên type
        
        Args:
            qr_type (str): 'advance' hoặc 'payment'
            instance_code (str): Instance code
            
        Returns:
            str: QR description
        """
        if qr_type == 'advance':
            return f"Tam ung don {instance_code}"
        elif qr_type == 'payment':
            return f"Thanh toan don {instance_code}"
        else:
            return f"Don {instance_code}"  # Fallback

# Global service instance
vietqr_service = VietQRService()
