import requests
import json
from datetime import datetime
from typing import Optional, Dict, Any
from app.config.settings import settings

class LarkService:
    def __init__(self):
        self.access_token_cache = {"token": None, "expires_at": None}
    
    async def get_access_token(self) -> Optional[str]:
        """Lấy access token từ LarkSuite với caching"""
        current_time = datetime.now().timestamp()
        
        if (self.access_token_cache["token"] and 
            self.access_token_cache["expires_at"] and 
            current_time < self.access_token_cache["expires_at"]):
            return self.access_token_cache["token"]
        
        try:
            url = f"{settings.BASE_URL}/auth/v3/tenant_access_token/internal"
            payload = {
                "app_id": settings.LARK_APP_ID,
                "app_secret": settings.LARK_APP_SECRET
            }
            
            response = requests.post(url, json=payload, timeout=10)
            data = response.json()
            
            if data.get("code") == 0:
                token = data["tenant_access_token"]
                expires_in = data.get("expire", 7200)
                
                self.access_token_cache["token"] = token
                self.access_token_cache["expires_at"] = current_time + expires_in - settings.TOKEN_CACHE_BUFFER_SECONDS
                
                print(f"✅ Got access token")
                return token
            else:
                print(f"❌ Failed to get token: {data}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting token: {e}")
            return None

    async def get_approval_instance(self, instance_code: str, access_token: str) -> Optional[Dict]:
        """Lấy thông tin approval instance"""
        try:
            url = f"{settings.BASE_URL}/approval/v4/instances/{instance_code}"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            print(f"🔍 Lấy thông tin instance: {instance_code}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Lỗi API call: {response.status_code}")
                return None
                
            api_response = response.json()
            
            if api_response.get("code") != 0:
                print(f"❌ API response error: {api_response}")
                return None
                
            return api_response
            
        except Exception as e:
            print(f"❌ Error getting approval instance: {e}")
            return None

    async def upload_image_to_approval(self, image_buffer, filename: str, access_token: str) -> Dict:
        """Upload ảnh lên Lark Approval API"""
        try:
            image_buffer.seek(0)
            
            files = {
                'name': (None, filename),
                'type': (None, 'image'),
                'content': (filename, image_buffer, 'image/png')
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            print(f"📤 Đang upload ảnh: {filename}")
            response = requests.post(settings.APPROVAL_UPLOAD_URL, files=files, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    file_code = data['data']['code']
                    file_url = data['data']['url']
                    print(f'✅ Upload ảnh thành công! File code: {file_code}')
                    return {
                        'success': True,
                        'file_code': file_code,
                        'file_url': file_url
                    }
                else:
                    error_msg = f"API error: {data.get('msg')} (code: {data.get('code')})"
                    print(f'❌ Upload thất bại: {error_msg}')
                    return {'success': False, 'error': error_msg}
            else:
                error_msg = f"HTTP error: {response.status_code}"
                print(f'❌ Upload thất bại: {error_msg}')
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"❌ Lỗi upload: {error_msg}")
            return {'success': False, 'error': error_msg}

    async def create_enhanced_comment_with_image(self, instance_code: str, file_url: str, file_code: str, 
                                               filename: str, qr_type: str, amount: int, node_name: str,
                                               access_token: str, user_id: str = None) -> Dict:
        """Tạo comment với ảnh và thông tin chi tiết"""
        try:
            if user_id is None:
                user_id = settings.DEFAULT_USER_ID
                
            create_comment_url = f'{settings.BASE_URL}/approval/v4/instances/{instance_code}/comments'
            
            params = {
                "user_id": user_id,
                "user_id_type": "user_id"
            }
            
            # Enhanced comment text với type info
            qr_type_display = {
                'advance': 'TẠM ỨNG',
                'payment': 'THANH TOÁN'
            }
            
            comment_text = f"""🏦 Mã VietQR {qr_type_display.get(qr_type, qr_type.upper())}
            💰 Số tiền: {amount:,} VND
            📋 Node: {node_name}
            📄 Instance: {instance_code}"""

            # Estimate file size
            try:
                file_size = len(filename) * 100  # Rough estimate
            except:
                file_size = 50000  # Default estimate
            
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
            
            request_body = {
                "content": json.dumps(content_data, ensure_ascii=False)
            }
            
            headers_comment = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            print(f"📤 Đang tạo enhanced comment cho instance: {instance_code}")
            print(f"   Comment: {comment_text.replace(chr(10), ' | ')}")
            
            response = requests.post(
                create_comment_url, 
                params=params,
                json=request_body, 
                headers=headers_comment
            )
            
            if response.status_code == 200:
                comment_result = response.json()
                if comment_result.get('code') == 0:
                    comment_id = comment_result.get("data", {}).get("comment_id", "N/A")
                    print(f'✅ Tạo enhanced comment thành công! Comment ID: {comment_id}')
                    return {'success': True, 'comment_id': comment_id}
                else:
                    error_msg = f"API error: {comment_result.get('msg')} (code: {comment_result.get('code')})"
                    print(f'❌ Tạo comment thất bại: {error_msg}')
                    return {'success': False, 'error': error_msg}
            else:
                error_msg = f"HTTP error: {response.status_code}"
                print(f'❌ Tạo comment thất bại: {error_msg}')
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"❌ Lỗi tạo enhanced comment: {error_msg}")
            return {'success': False, 'error': error_msg}

# Global service instance
lark_service = LarkService()
