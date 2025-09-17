import os
from typing import Optional


class Settings:
    """
    Cấu hình toàn bộ ứng dụng từ environment variables và default values.
    
    Settings class quản lý tất cả các cấu hình cần thiết cho ứng dụng bao gồm:
    - FastAPI server configuration
    - Lark/Feishu API credentials và endpoints
    - VietQR service configuration
    - Webhook và notification settings
    - Cache và performance settings
    - File storage settings
    - Validation và alert settings
    
    Tất cả settings có thể được override bằng environment variables.
    """
    
    # ===== FASTAPI SERVER SETTINGS =====
    # Cấu hình cho FastAPI web server
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"  # Bật/tắt debug mode
    PORT: int = int(os.getenv("PORT", "8000"))                   # Port để chạy server
    
    # ===== LARK/FEISHU API SETTINGS =====
    # Thông tin xác thực và endpoints cho Lark API
    LARK_APP_ID: str = os.getenv("LARK_APP_ID", "cli_a758ffaf41f8502f")
    LARK_APP_SECRET: str = os.getenv("LARK_APP_SECRET", "45Jsgm3TYfEwD2F67BH1LctlYEcCjZpH")
    
    # Base URL cho tất cả Lark API calls
    BASE_URL: str = "https://open.larksuite.com/open-apis"
    
    # Endpoint chuyên dụng cho upload file lên approval system
    APPROVAL_UPLOAD_URL: str = "https://www.larksuite.com/approval/openapi/v2/file/upload"
    
    # ===== VIETQR SERVICE SETTINGS =====
    # Cấu hình cho VietQR API để generate QR codes
    VIETQR_TEMPLATE: str = "compact2"                           # Template layout cho QR code
    VIETQR_BASE_URL: str = "https://img.vietqr.io/image"       # Base URL của VietQR service
    
    # ===== WEBHOOK & NOTIFICATION SETTINGS =====
    # Cấu hình webhook để gửi notifications
    LARK_WEBHOOK_URL: str = os.getenv(
        "LARK_WEBHOOK_URL", 
        "https://open.larksuite.com/open-apis/bot/v2/hook/6a53a060-40d7-4716-9a90-970a6cbdaf64"
    )
    
    # Bật/tắt validation alerts qua webhook
    ENABLE_VALIDATION_ALERTS: bool = os.getenv("ENABLE_VALIDATION_ALERTS", "true").lower() == "true"

    # ===== CACHE & PERFORMANCE SETTINGS =====
    # Cấu hình cache để tối ưu performance và tránh duplicate requests
    QR_CACHE_DURATION_MINUTES: int = 5      # Thời gian cache QR generation (phút)
    TOKEN_CACHE_BUFFER_SECONDS: int = 300   # Buffer time trước khi token hết hạn (5 phút)

    # ===== FILE STORAGE SETTINGS =====
    # Cấu hình file storage cho logging và data persistence
    EVENTS_FILE: str = "lark_events.csv"    # File lưu trữ event logs
    
    # ===== USER & AUTHENTICATION SETTINGS =====
    # User ID mặc định để tạo comments trong Lark approval
    DEFAULT_USER_ID: str = "cd11b141"
    
    # ===== VALIDATION & MONITORING SETTINGS =====
    # Cấu hình các tính năng validation và monitoring (cho future extensions)
    
    # Bật/tắt validation số tiền trong approval workflow
    ENABLE_AMOUNT_VALIDATION: bool = os.getenv("ENABLE_AMOUNT_VALIDATION", "true").lower() == "true"
    
    # Bật/tắt alerts cho workflow errors và anomalies
    ENABLE_WORKFLOW_ALERTS: bool = os.getenv("ENABLE_WORKFLOW_ALERTS", "true").lower() == "true"


# Global settings instance - sử dụng trong toàn bộ ứng dụng
# Import settings từ module này để truy cập tất cả configuration
settings = Settings()
