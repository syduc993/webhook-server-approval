# app/services/event_bus.py
import asyncio
from typing import Dict, List, Callable, Any
from datetime import datetime


class EventBus:
    """
    Event Bus system để quản lý và phân phối events trong ứng dụng.
    
    EventBus cho phép các component đăng ký handlers cho các loại event khác nhau
    và publish events để thực thi tất cả handlers đã đăng ký một cách bất đồng bộ.
    
    Attributes:
        handlers (Dict[str, List[Callable]]): Dictionary chứa danh sách handlers cho từng event type
        event_history (List[Dict]): Lịch sử tất cả events đã được publish
    """
    
    def __init__(self):
        """Khởi tạo EventBus với handlers và event history rỗng."""
        self.handlers: Dict[str, List[Callable]] = {}
        self.event_history: List[Dict] = []
    
    def subscribe(self, event_type: str, handler: Callable):
        """
        Đăng ký handler cho một event type cụ thể.
        
        Args:
            event_type (str): Loại event cần lắng nghe
            handler (Callable): Hàm xử lý sẽ được gọi khi event được publish
            
        Note:
            Handler phải là async function và nhận event_data làm tham số
        """
        # Khởi tạo danh sách handlers cho event type nếu chưa tồn tại
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        
        # Thêm handler vào danh sách
        self.handlers[event_type].append(handler)
        print(f"📝 Đã đăng ký handler cho event: {event_type}")
    
    async def publish(self, event_type: str, event_data: Dict[str, Any]):
        """
        Publish event và thực thi tất cả handlers đã đăng ký song song.
        
        Args:
            event_type (str): Loại event cần publish
            event_data (Dict[str, Any]): Dữ liệu sẽ được truyền cho các handlers
            
        Returns:
            List: Danh sách kết quả từ tất cả handlers (bao gồm cả exceptions)
        """
        print(f"📢 Đang publish event: {event_type}")
        
        # Lưu lịch sử event
        event_record = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": event_data,
            "handlers_count": len(self.handlers.get(event_type, []))
        }
        self.event_history.append(event_record)
        
        # Thực thi tất cả handlers đồng thời
        if event_type in self.handlers:
            tasks = []
            
            # Tạo task cho mỗi handler
            for handler in self.handlers[event_type]:
                task = asyncio.create_task(
                    self._run_handler_safe(handler, event_data)
                )
                tasks.append(task)
            
            # Đợi tất cả handlers hoàn thành (kể cả khi có lỗi)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Ghi log kết quả từ mỗi handler
            for i, result in enumerate(results):
                handler_name = self.handlers[event_type][i].__name__
                if isinstance(result, Exception):
                    print(f"❌ Handler {handler_name} thất bại: {result}")
                else:
                    print(f"✅ Handler {handler_name} hoàn thành: {result}")
            
            return results
        else:
            print(f"⚠️ Không có handler nào được đăng ký cho event: {event_type}")
            return []
    
    async def _run_handler_safe(self, handler: Callable, event_data: Dict) -> Dict:
        """
        Thực thi handler với error handling và monitoring thời gian.
        
        Args:
            handler (Callable): Handler function cần thực thi
            event_data (Dict): Dữ liệu event được truyền cho handler
            
        Returns:
            Dict: Thông tin kết quả bao gồm success status, result/error, và thời gian thực thi
        """
        handler_name = handler.__name__
        try:
            print(f"🚀 Bắt đầu thực thi handler: {handler_name}")
            start_time = datetime.now()
            
            # Gọi handler (phải là async function)
            result = await handler(event_data)
            
            # Tính thời gian thực thi
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "handler": handler_name,
                "success": True,
                "result": result,
                "duration_seconds": duration
            }
            
        except Exception as e:
            print(f"❌ Handler {handler_name} gặp lỗi: {e}")
            return {
                "handler": handler_name,
                "success": False,
                "error": str(e),
                "duration_seconds": 0
            }
    
    def get_event_history(self, limit: int = 50) -> List[Dict]:
        """
        Lấy lịch sử các events đã được publish.
        
        Args:
            limit (int, optional): Số lượng events gần nhất cần lấy. Mặc định là 50.
            
        Returns:
            List[Dict]: Danh sách các event records theo thứ tự thời gian (mới nhất cuối)
        """
        return self.event_history[-limit:]


event_bus = EventBus()
