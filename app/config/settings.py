import os
from typing import Optional

class Settings:
    # FastAPI settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Lark API settings
    LARK_APP_ID: str = os.getenv("LARK_APP_ID", "cli_a758ffaf41f8502f")
    LARK_APP_SECRET: str = os.getenv("LARK_APP_SECRET", "45Jsgm3TYfEwD2F67BH1LctlYEcCjZpH")
    BASE_URL: str = "https://open.larksuite.com/open-apis"
    APPROVAL_UPLOAD_URL: str = "https://www.larksuite.com/approval/openapi/v2/file/upload"
    
    # VietQR settings
    VIETQR_TEMPLATE: str = "compact2"
    VIETQR_BASE_URL: str = "https://img.vietqr.io/image"
    
    # Cache settings
    QR_CACHE_DURATION_MINUTES: int = 5
    TOKEN_CACHE_BUFFER_SECONDS: int = 300  # 5 minutes buffer
    
    # File settings
    EVENTS_FILE: str = "lark_events.csv"
    
    # Default user for comments
    DEFAULT_USER_ID: str = "cd11b141"
    
    # Validation settings (for future extensions)
    ENABLE_AMOUNT_VALIDATION: bool = os.getenv("ENABLE_AMOUNT_VALIDATION", "false").lower() == "true"
    ENABLE_WORKFLOW_ALERTS: bool = os.getenv("ENABLE_WORKFLOW_ALERTS", "false").lower() == "true"

# Global settings instance
settings = Settings()
