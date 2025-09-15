from datetime import datetime, timedelta
from typing import Dict, Optional

class CacheService:
    def __init__(self):
        self.qr_generation_cache: Dict[str, datetime] = {}
    
    def generate_cache_key(self, instance_code: str, node_id: str, qr_type: str) -> str:
        """
        Tạo cache key để detect duplicate
        
        Args:
            instance_code (str): Instance code
            node_id (str): Node ID (8 ký tự đầu)
            qr_type (str): 'advance' hoặc 'payment'
            
        Returns:
            str: Unique cache key
        """
        short_node_id = node_id[:8] if len(node_id) > 8 else node_id
        return f"{instance_code}_{short_node_id}_{qr_type}"

    def is_qr_recently_generated(self, instance_code: str, node_id: str, qr_type: str, 
                               cache_duration_minutes: int = 5) -> bool:
        """
        Check xem QR đã được tạo trong thời gian gần đây chưa
        
        Returns:
            bool: True nếu đã tạo gần đây, False nếu chưa hoặc đã hết hạn
        """
        try:
            cache_key = self.generate_cache_key(instance_code, node_id, qr_type)
            
            if cache_key not in self.qr_generation_cache:
                print(f"🆕 Cache miss: {cache_key} - chưa tạo QR")
                return False
            
            generated_time = self.qr_generation_cache[cache_key]
            current_time = datetime.now()
            time_diff = current_time - generated_time
            
            if time_diff > timedelta(minutes=cache_duration_minutes):
                del self.qr_generation_cache[cache_key] 
                print(f"⏰ Cache expired: {cache_key} ({time_diff.total_seconds()/60:.1f} minutes ago)")
                return False
            
            print(f"🔒 Cache hit: {cache_key} - QR đã tạo {time_diff.total_seconds()/60:.1f} phút trước")
            return True
            
        except Exception as e:
            print(f"❌ Error checking cache: {e}")
            return False

    def mark_qr_as_generated(self, instance_code: str, node_id: str, qr_type: str):
        """Đánh dấu QR đã được tạo"""
        try:
            cache_key = self.generate_cache_key(instance_code, node_id, qr_type)
            self.qr_generation_cache[cache_key] = datetime.now()
            
            print(f"🔒 Marked QR as generated: {cache_key}")
            print(f"📊 Cache size: {len(self.qr_generation_cache)} entries")
            
        except Exception as e:
            print(f"❌ Error marking cache: {e}")

    def get_cache_status(self) -> Dict:
        """Lấy trạng thái cache"""
        try:
            current_time = datetime.now()
            active_cache = {}
            
            for cache_key, generated_time in self.qr_generation_cache.items():
                time_diff = current_time - generated_time
                minutes_ago = time_diff.total_seconds() / 60
                
                active_cache[cache_key] = {
                    'generated_at': generated_time.isoformat(),
                    'minutes_ago': round(minutes_ago, 1),
                    'will_expire_in_minutes': max(0, 5 - minutes_ago)
                }
            
            return {
                'total_cached_qr': len(self.qr_generation_cache),
                'active_cache': active_cache,
                'cache_duration_minutes': 5,
                'current_time': current_time.isoformat()
            }
            
        except Exception as e:
            return {"error": str(e)}

    def clear_cache(self) -> Dict:
        """Clear tất cả cache"""
        try:
            old_count = len(self.qr_generation_cache)
            old_keys = list(self.qr_generation_cache.keys())
            
            self.qr_generation_cache.clear()
            
            return {
                'message': f'Successfully cleared {old_count} cache entries',
                'cleared_keys': old_keys,
                'current_cache_size': len(self.qr_generation_cache)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# Global cache instance
cache_service = CacheService()
