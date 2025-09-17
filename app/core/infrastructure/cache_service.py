from datetime import datetime, timedelta
from typing import Dict, Optional


class CacheService:
    """
    Service quản lý cache cho QR code generation và validation alerts.
    
    CacheService giúp tránh trùng lặp bằng cách cache thời điểm tạo QR codes
    và gửi validation alerts. Service này sử dụng in-memory cache với
    automatic expiration để tiết kiệm bộ nhớ.
    
    Attributes:
        qr_generation_cache (Dict[str, datetime]): Cache thời điểm tạo QR codes
        validation_alert_cache (Dict[str, datetime]): Cache thời điểm gửi validation alerts
    """
    
    def __init__(self):
        """Khởi tạo CacheService với các cache dictionary rỗng."""
        self.qr_generation_cache: Dict[str, datetime] = {}
        self.validation_alert_cache: Dict[str, datetime] = {}
    
    def generate_cache_key(self, instance_code: str, node_id: str, qr_type: str) -> str:
        """
        Tạo cache key unique cho QR code để detect duplicates.
        
        Args:
            instance_code (str): Mã instance của approval workflow
            node_id (str): ID của node trong workflow
            qr_type (str): Loại QR code (payment, advance, etc.)
            
        Returns:
            str: Cache key format: {instance_code}_{short_node_id}_{qr_type}
        """
        # Rút ngắn node_id để cache key không quá dài
        short_node_id = node_id[:8] if len(node_id) > 8 else node_id
        return f"{instance_code}_{short_node_id}_{qr_type}"

    def generate_validation_cache_key(self, instance_code: str, validation_type: str) -> str:
        """
        Tạo cache key cho validation alerts để tránh spam alerts.
        
        Args:
            instance_code (str): Mã instance của approval workflow
            validation_type (str): Loại validation (amount_mismatch, workflow_error, etc.)
            
        Returns:
            str: Cache key format: validation_{instance_code}_{validation_type}
        """
        return f"validation_{instance_code}_{validation_type}"

    def is_qr_recently_generated(self, instance_code: str, node_id: str, qr_type: str, 
                               cache_duration_minutes: int = 5) -> bool:
        """
        Kiểm tra xem QR code đã được tạo trong khoảng thời gian gần đây chưa.
        
        Args:
            instance_code (str): Mã instance của approval workflow
            node_id (str): ID của node trong workflow
            qr_type (str): Loại QR code
            cache_duration_minutes (int, optional): Thời gian cache tính bằng phút. Mặc định 5 phút.
            
        Returns:
            bool: True nếu QR đã được tạo gần đây, False nếu chưa hoặc đã hết hạn
        """
        try:
            cache_key = self.generate_cache_key(instance_code, node_id, qr_type)
            
            # Kiểm tra xem cache key có tồn tại không
            if cache_key not in self.qr_generation_cache:
                print(f"🆕 Cache miss: {cache_key} - chưa từng tạo QR")
                return False
            
            # Tính thời gian đã trải qua kể từ lần tạo QR cuối
            generated_time = self.qr_generation_cache[cache_key]
            current_time = datetime.now()
            time_diff = current_time - generated_time
            
            # Nếu đã quá thời gian cache thì xóa entry và return False
            if time_diff > timedelta(minutes=cache_duration_minutes):
                del self.qr_generation_cache[cache_key] 
                print(f"⏰ Cache đã hết hạn: {cache_key} ({time_diff.total_seconds()/60:.1f} phút trước)")
                return False
            
            print(f"🔒 Cache hit: {cache_key} - QR đã tạo {time_diff.total_seconds()/60:.1f} phút trước")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi khi kiểm tra cache: {e}")
            return False

    def is_validation_alert_recently_sent(self, instance_code: str, validation_type: str,
                                        cache_duration_minutes: int = 10) -> bool:
        """
        Kiểm tra xem validation alert đã được gửi trong khoảng thời gian gần đây chưa.
        
        Args:
            instance_code (str): Mã instance của approval workflow
            validation_type (str): Loại validation error
            cache_duration_minutes (int, optional): Thời gian cache tính bằng phút. Mặc định 10 phút.
            
        Returns:
            bool: True nếu alert đã được gửi gần đây, False nếu chưa hoặc đã hết hạn
        """
        try:
            cache_key = self.generate_validation_cache_key(instance_code, validation_type)
            
            # Kiểm tra xem cache key có tồn tại không
            if cache_key not in self.validation_alert_cache:
                print(f"🆕 Validation cache miss: {cache_key} - chưa từng gửi alert")
                return False
            
            # Tính thời gian đã trải qua kể từ lần gửi alert cuối
            sent_time = self.validation_alert_cache[cache_key]
            current_time = datetime.now()
            time_diff = current_time - sent_time
            
            # Nếu đã quá thời gian cache thì xóa entry và return False
            if time_diff > timedelta(minutes=cache_duration_minutes):
                del self.validation_alert_cache[cache_key]
                print(f"⏰ Validation cache đã hết hạn: {cache_key} ({time_diff.total_seconds()/60:.1f} phút trước)")
                return False
            
            print(f"🔒 Validation cache hit: {cache_key} - Alert đã gửi {time_diff.total_seconds()/60:.1f} phút trước")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi khi kiểm tra validation cache: {e}")
            return False

    def mark_qr_as_generated(self, instance_code: str, node_id: str, qr_type: str):
        """
        Đánh dấu QR code đã được tạo bằng cách lưu timestamp vào cache.
        
        Args:
            instance_code (str): Mã instance của approval workflow
            node_id (str): ID của node trong workflow
            qr_type (str): Loại QR code
        """
        try:
            cache_key = self.generate_cache_key(instance_code, node_id, qr_type)
            self.qr_generation_cache[cache_key] = datetime.now()
            
            print(f"🔒 Đã đánh dấu QR được tạo: {cache_key}")
            print(f"📊 Kích thước QR Cache: {len(self.qr_generation_cache)} entries")
            
        except Exception as e:
            print(f"❌ Lỗi khi đánh dấu cache: {e}")

    def mark_validation_alert_as_sent(self, instance_code: str, validation_type: str):
        """
        Đánh dấu validation alert đã được gửi bằng cách lưu timestamp vào cache.
        
        Args:
            instance_code (str): Mã instance của approval workflow
            validation_type (str): Loại validation error
        """
        try:
            cache_key = self.generate_validation_cache_key(instance_code, validation_type)
            self.validation_alert_cache[cache_key] = datetime.now()
            
            print(f"🔒 Đã đánh dấu validation alert được gửi: {cache_key}")
            print(f"📊 Kích thước Validation Cache: {len(self.validation_alert_cache)} entries")
            
        except Exception as e:
            print(f"❌ Lỗi khi đánh dấu validation cache: {e}")

    def get_cache_status(self) -> Dict:
        """
        Lấy trạng thái chi tiết của tất cả cache (QR và validation).
        
        Returns:
            Dict: Dictionary chứa thông tin chi tiết về:
                - qr_cache: Thông tin về QR generation cache
                - validation_cache: Thông tin về validation alert cache
                - current_time: Thời gian hiện tại
        """
        try:
            current_time = datetime.now()
            
            # Tính toán trạng thái QR Cache
            active_qr_cache = {}
            for cache_key, generated_time in self.qr_generation_cache.items():
                time_diff = current_time - generated_time
                minutes_ago = time_diff.total_seconds() / 60
                
                active_qr_cache[cache_key] = {
                    'generated_at': generated_time.isoformat(),
                    'minutes_ago': round(minutes_ago, 1),
                    'will_expire_in_minutes': max(0, 5 - minutes_ago)  # 5 phút cho QR
                }
            
            # Tính toán trạng thái Validation Cache
            active_validation_cache = {}
            for cache_key, sent_time in self.validation_alert_cache.items():
                time_diff = current_time - sent_time
                minutes_ago = time_diff.total_seconds() / 60
                
                active_validation_cache[cache_key] = {
                    'sent_at': sent_time.isoformat(),
                    'minutes_ago': round(minutes_ago, 1),
                    'will_expire_in_minutes': max(0, 10 - minutes_ago)  # 10 phút cho validation
                }
            
            return {
                'qr_cache': {
                    'total_cached_qr': len(self.qr_generation_cache),
                    'active_cache': active_qr_cache,
                    'cache_duration_minutes': 5
                },
                'validation_cache': {
                    'total_cached_alerts': len(self.validation_alert_cache),
                    'active_cache': active_validation_cache,
                    'cache_duration_minutes': 10
                },
                'current_time': current_time.isoformat()
            }
            
        except Exception as e:
            return {"error": str(e)}

    def clear_cache(self) -> Dict:
        """
        Xóa tất cả cache entries (cả QR và validation) và trả về thông tin chi tiết.
        
        Returns:
            Dict: Dictionary chứa:
                - message: Thông báo kết quả
                - cleared_qr_keys: Danh sách QR cache keys đã bị xóa
                - cleared_validation_keys: Danh sách validation cache keys đã bị xóa
                - current_cache_sizes: Kích thước cache hiện tại (sau khi clear)
        """
        try:
            # Lưu lại thông tin trước khi clear
            old_qr_count = len(self.qr_generation_cache)
            old_validation_count = len(self.validation_alert_cache)
            old_qr_keys = list(self.qr_generation_cache.keys())
            old_validation_keys = list(self.validation_alert_cache.keys())
            
            # Clear tất cả cache
            self.qr_generation_cache.clear()
            self.validation_alert_cache.clear()
            
            return {
                'message': f'Đã xóa thành công {old_qr_count} QR cache entries và {old_validation_count} validation cache entries',
                'cleared_qr_keys': old_qr_keys,
                'cleared_validation_keys': old_validation_keys,
                'current_qr_cache_size': len(self.qr_generation_cache),
                'current_validation_cache_size': len(self.validation_alert_cache)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


cache_service = CacheService()
