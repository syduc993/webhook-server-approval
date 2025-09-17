import requests
import json
from datetime import datetime
from typing import Optional, Dict
from app.core.config.settings import settings


class LarkService:
    """
    Service tương tác với Lark/Feishu API để quản lý approval instances.
    
    LarkService cung cấp các chức năng chính:
    - Xác thực và quản lý access tokens với caching
    - Lấy thông tin approval instances
    - Upload hình ảnh lên Lark
    - Tạo comments với attachments
    
    Attributes:
        access_token_cache (Dict): Cache lưu trữ access token và thời gian hết hạn
    """
    
    def __init__(self):
        """Khởi tạo LarkService với token cache rỗng."""
        self.access_token_cache = {"token": None, "expires_at": None}
    
    async def get_access_token(self) -> Optional[str]:
        """
        Lấy access token từ LarkSuite API với caching mechanism.
        
        Method này sẽ sử dụng cached token nếu còn hiệu lực, otherwise
        sẽ gọi API để lấy token mới và cache lại.
        
        Returns:
            Optional[str]: Access token nếu thành công, None nếu thất bại
        """
        current_time = datetime.now().timestamp()
        
        # Kiểm tra xem token đã cache còn hiệu lực không
        if (self.access_token_cache["token"] and 
            self.access_token_cache["expires_at"] and 
            current_time < self.access_token_cache["expires_at"]):
            return self.access_token_cache["token"]
        
        try:
            # Gọi API để lấy tenant access token mới
            url = f"{settings.BASE_URL}/auth/v3/tenant_access_token/internal"
            payload = {
                "app_id": settings.LARK_APP_ID,
                "app_secret": settings.LARK_APP_SECRET
            }
            
            response = requests.post(url, json=payload, timeout=10)
            data = response.json()
            
            # Kiểm tra response từ API
            if data.get("code") == 0:
                token = data["tenant_access_token"]
                expires_in = data.get("expire", 7200)  # Mặc định 2 tiếng
                
                # Cache token với buffer time để tránh token hết hạn giữa chừng
                self.access_token_cache["token"] = token
                self.access_token_cache["expires_at"] = current_time + expires_in - settings.TOKEN_CACHE_BUFFER_SECONDS
                
                print(f"✅ Lấy access token thành công")
                return token
            else:
                print(f"❌ Lấy token thất bại: {data}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi khi lấy token: {e}")
            return None

    async def get_approval_instance(self, instance_code: str, access_token: str) -> Optional[Dict]:
        """
        Lấy thông tin chi tiết của approval instance từ Lark API.
        
        Args:
            instance_code (str): Mã định danh của approval instance
            access_token (str): Access token để xác thực API call
            
        Returns:
            Optional[Dict]: Thông tin instance nếu thành công, None nếu thất bại
        """
        try:
            url = f"{settings.BASE_URL}/approval/v4/instances/{instance_code}"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            print(f"🔍 Đang lấy thông tin instance: {instance_code}")
            response = requests.get(url, headers=headers, timeout=10)
            
            # Kiểm tra HTTP status code
            if response.status_code != 200:
                print(f"❌ Lỗi HTTP khi gọi API: {response.status_code}")
                return None
                
            api_response = response.json()
            
            # Kiểm tra Lark API response code
            if api_response.get("code") != 0:
                print(f"❌ Lỗi Lark API response: {api_response}")
                return None
                
            return api_response
            
        except Exception as e:
            print(f"❌ Lỗi khi lấy thông tin approval instance: {e}")
            return None

    async def upload_image_to_approval(self, image_buffer, filename: str, access_token: str) -> Dict:
        """
        Upload hình ảnh lên Lark Approval system để sử dụng trong comments.
        
        Args:
            image_buffer: Buffer chứa dữ liệu hình ảnh (bytes)
            filename (str): Tên file của hình ảnh
            access_token (str): Access token để xác thực API call
            
        Returns:
            Dict: Dictionary chứa:
                - success (bool): Trạng thái upload
                - file_code (str): Mã file từ Lark (nếu success)  
                - file_url (str): URL file từ Lark (nếu success)
                - error (str): Thông báo lỗi (nếu failed)
        """
        try:
            # Reset buffer position về đầu để đọc từ beginning
            image_buffer.seek(0)
            
            # Chuẩn bị multipart form data cho upload
            files = {
                'name': (None, filename),
                'type': (None, 'image'),
                'content': (filename, image_buffer, 'image/png')
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            print(f"📤 Đang upload hình ảnh: {filename}")
            response = requests.post(settings.APPROVAL_UPLOAD_URL, files=files, headers=headers)
            
            # Xử lý response từ upload API
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    file_code = data['data']['code']
                    file_url = data['data']['url']
                    print(f'✅ Upload hình ảnh thành công! File code: {file_code}')
                    return {
                        'success': True,
                        'file_code': file_code,
                        'file_url': file_url
                    }
                else:
                    error_msg = f"Lỗi API: {data.get('msg')} (code: {data.get('code')})"
                    print(f'❌ Upload thất bại: {error_msg}')
                    return {'success': False, 'error': error_msg}
            else:
                error_msg = f"Lỗi HTTP: {response.status_code}"
                print(f'❌ Upload thất bại: {error_msg}')
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"❌ Lỗi upload: {error_msg}")
            return {'success': False, 'error': error_msg}

    async def create_enhanced_comment_with_image(self, instance_code: str, file_url: str, file_code: str, 
                                               filename: str, qr_type: str, amount: int, node_name: str,
                                               access_token: str, user_id: str = None) -> Dict:
        """
        Tạo comment với hình ảnh QR code và thông tin chi tiết.
        
        Args:
            instance_code (str): Mã instance của approval workflow
            file_url (str): URL của file đã upload
            file_code (str): Code của file từ Lark system
            filename (str): Tên file hình ảnh
            qr_type (str): Loại QR ('advance' hoặc 'payment')
            amount (int): Số tiền của QR code
            node_name (str): Tên node trong workflow
            access_token (str): Access token để xác thực
            user_id (str, optional): User ID thực hiện comment
            
        Returns:
            Dict: Dictionary chứa:
                - success (bool): Trạng thái tạo comment
                - comment_id (str): ID của comment được tạo (nếu success)
                - error (str): Thông báo lỗi (nếu failed)
        """
        try:
            # Sử dụng default user ID nếu không được cung cấp
            if user_id is None:
                user_id = settings.DEFAULT_USER_ID
                
            create_comment_url = f'{settings.BASE_URL}/approval/v4/instances/{instance_code}/comments'
            
            # Parameters cho API call
            params = {
                "user_id": user_id,
                "user_id_type": "user_id"
            }
            
            # Tạo text hiển thị cho QR type
            qr_type_display = {
                'advance': 'TẠM ỨNG',
                'payment': 'THANH TOÁN'
            }
            
            # Tạo nội dung comment với thông tin chi tiết
            comment_text = f"""🏦 Mã VietQR {qr_type_display.get(qr_type, qr_type.upper())}
💰 Số tiền: {amount:,} VND"""

            # Ước tính kích thước file (rough estimate)
            try:
                file_size = len(filename) * 100  # Ước tính dựa trên độ dài filename
            except:
                file_size = 50000  # Giá trị mặc định

            # Tạo content data với text và file attachment
            content_data = {
                "text": comment_text,
                "files": [{
                    "url": file_url,
                    "fileSize": file_size,
                    "title": filename,
                    "type": "image",
                    "extra": file_code
                }]
            }
            
            # Request body với JSON content
            request_body = {
                "content": json.dumps(content_data, ensure_ascii=False)
            }
            
            headers_comment = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            print(f"📤 Đang tạo enhanced comment cho instance: {instance_code}")
            print(f"   Nội dung: {comment_text.replace(chr(10), ' | ')}")
            
            # Gọi API để tạo comment
            response = requests.post(
                create_comment_url, 
                params=params,
                json=request_body, 
                headers=headers_comment
            )
            
            # Xử lý response từ comment API
            if response.status_code == 200:
                comment_result = response.json()
                if comment_result.get('code') == 0:
                    comment_id = comment_result.get("data", {}).get("comment_id", "N/A")
                    print(f'✅ Tạo enhanced comment thành công! Comment ID: {comment_id}')
                    return {'success': True, 'comment_id': comment_id}
                else:
                    error_msg = f"Lỗi API: {comment_result.get('msg')} (code: {comment_result.get('code')})"
                    print(f'❌ Tạo comment thất bại: {error_msg}')
                    return {'success': False, 'error': error_msg}
            else:
                error_msg = f"Lỗi HTTP: {response.status_code}"
                print(f'❌ Tạo comment thất bại: {error_msg}')
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"❌ Lỗi tạo enhanced comment: {error_msg}")
            return {'success': False, 'error': error_msg}


lark_service = LarkService()
