import asyncio
from datetime import datetime
from app.core.events.event_registry import event_registry
from app.core.config.settings import settings


class ApplicationBootstrap:
    """
    Bootstrap toàn bộ ứng dụng theo kiến trúc DDD (Domain-Driven Design).
    
    Lớp này chịu trách nhiệm khởi tạo và cấu hình tất cả các thành phần cần thiết
    của ứng dụng bao gồm event handlers, infrastructure services và kiểm tra
    sức khỏe hệ thống.
    
    Attributes:
        startup_time (datetime): Thời điểm bắt đầu khởi tạo ứng dụng
        is_initialized (bool): Trạng thái khởi tạo của ứng dụng
    """
    
    def __init__(self):
        """Khởi tạo ApplicationBootstrap với trạng thái ban đầu."""
        self.startup_time = None
        self.is_initialized = False
        
    async def initialize(self):
        """
        Khởi tạo toàn bộ ứng dụng theo thứ tự ưu tiên.
        
        Quá trình khởi tạo bao gồm:
        1. Đăng ký event handlers
        2. Khởi tạo infrastructure services  
        3. Kiểm tra sức khỏe hệ thống
        
        Raises:
            Exception: Khi có lỗi trong quá trình khởi tạo
        """
        print("🚀 Bắt đầu khởi tạo ứng dụng...")
        self.startup_time = datetime.now()
        
        try:
            # 1. Đăng ký các event handlers
            await self._register_event_handlers()
            
            # 2. Khởi tạo các infrastructure services
            await self._initialize_infrastructure()
            
            # 3. Kiểm tra sức khỏe hệ thống
            await self._validate_system_health()
            
            # Đánh dấu ứng dụng đã khởi tạo thành công
            self.is_initialized = True
            elapsed = (datetime.now() - self.startup_time).total_seconds()
            
            print(f"✅ Khởi tạo ứng dụng hoàn tất trong {elapsed:.2f}s")
            
        except Exception as e:
            print(f"❌ Khởi tạo ứng dụng thất bại: {e}")
            raise
    
    async def _register_event_handlers(self):
        """
        Đăng ký tất cả event handlers từ domain layer.
        
        Method này sử dụng event_registry để tự động đăng ký tất cả
        handlers được định nghĩa trong các domain modules.
        
        Raises:
            Exception: Khi không thể đăng ký event handlers
        """
        print("📝 Đang đăng ký event handlers...")
        
        try:
            # Gọi registry để đăng ký tất cả domain handlers
            event_registry.register_domain_handlers()
            
            # Lấy thông tin trạng thái đăng ký để log
            status = event_registry.get_registration_status()
            print(f"   • Đã đăng ký {status['total_handlers']} handlers cho {status['total_event_types']} loại event")
            
        except Exception as e:
            print(f"❌ Đăng ký event handlers thất bại: {e}")
            raise
    
    async def _initialize_infrastructure(self):
        """
        Khởi tạo và kiểm tra các infrastructure services.
        
        Bao gồm:
        - Lark API service (kết nối đến Lark/Feishu)
        - Cache service (Redis hoặc in-memory cache)
        - Notification service (webhook alerts)
        
        Raises:
            Exception: Khi không thể khởi tạo infrastructure services
        """
        print("🏗️ Đang khởi tạo infrastructure services...")
        
        try:
            # Kiểm tra kết nối Lark API
            from app.core.infrastructure.lark_service import lark_service
            
            print("   • Đang kiểm tra kết nối Lark API...")
            token = await lark_service.get_access_token()
            if token:
                print("   ✅ Kết nối Lark API thành công")
            else:
                print("   ⚠️ Kết nối Lark API thất bại - kiểm tra lại thông tin xác thực")
            
            # Khởi tạo cache service
            from app.core.infrastructure.cache_service import cache_service
            print("   • Cache service đã được khởi tạo")
            print(f"   • Thời gian cache QR code: {settings.QR_CACHE_DURATION_MINUTES} phút")
            
            # Kiểm tra notification service nếu được bật
            if settings.ENABLE_VALIDATION_ALERTS:
                print("   • Cảnh báo validation đã được bật")
                if settings.LARK_WEBHOOK_URL:
                    print("   ✅ Webhook URL đã được cấu hình")
                else:
                    print("   ⚠️ Chưa cấu hình webhook URL")
            else:
                print("   • Cảnh báo validation đã được tắt")
            
        except Exception as e:
            print(f"❌ Khởi tạo infrastructure thất bại: {e}")
            raise
    
    async def _validate_system_health(self):
        """
        Kiểm tra sức khỏe tổng thể của hệ thống.
        
        Validates:
        - Event bus hoạt động bình thường
        - Node configuration đã được load
        - Environment variables cần thiết đã được cấu hình
        
        Raises:
            Exception: Khi phát hiện vấn đề nghiêm trọng với hệ thống
        """
        print("🔍 Đang kiểm tra sức khỏe hệ thống...")
        
        try:
            # Kiểm tra event bus
            from app.core.infrastructure.event_bus import event_bus
            handler_count = len(event_bus.handlers.get("approval.instance.updated", []))
            print(f"   • Event bus: {handler_count} handlers đã đăng ký cho approval events")
            
            # Kiểm tra node configuration
            from app.core.config.node_config import APPROVAL_WORKFLOWS
            print(f"   • Cấu hình workflow: {len(APPROVAL_WORKFLOWS)} quy trình đã được cấu hình")
            
            # Kiểm tra các environment variables bắt buộc
            required_vars = ["LARK_APP_ID", "LARK_APP_SECRET"]
            missing_vars = []
            
            # Duyệt qua từng biến môi trường bắt buộc
            for var in required_vars:
                if not getattr(settings, var, None):
                    missing_vars.append(var)
            
            # Báo cáo kết quả kiểm tra environment variables
            if missing_vars:
                print(f"   ⚠️ Thiếu các biến môi trường: {', '.join(missing_vars)}")
            else:
                print("   ✅ Tất cả biến môi trường bắt buộc đều có")
            
            print("   ✅ Kiểm tra sức khỏe hệ thống hoàn tất")
            
        except Exception as e:
            print(f"❌ Kiểm tra sức khỏe hệ thống thất bại: {e}")
            raise
    
    def get_startup_info(self) -> dict:
        """
        Lấy thông tin chi tiết về quá trình khởi động ứng dụng.
        
        Returns:
            dict: Dictionary chứa thông tin startup bao gồm:
                - startup_time: Thời điểm bắt đầu khởi tạo
                - is_initialized: Trạng thái khởi tạo
                - uptime_seconds: Thời gian hoạt động (giây)
                - event_handlers: Thông tin về event handlers đã đăng ký
                - architecture: Loại kiến trúc được sử dụng
                - version: Phiên bản ứng dụng
        """
        return {
            "startup_time": self.startup_time.isoformat() if self.startup_time else None,
            "is_initialized": self.is_initialized,
            "uptime_seconds": (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0,
            "event_handlers": event_registry.get_registration_status(),
            "architecture": "DDD",
            "version": "2.0.0"
        }


app_bootstrap = ApplicationBootstrap()
