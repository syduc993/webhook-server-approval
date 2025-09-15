from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class APIResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class UploadResult(BaseModel):
    success: bool
    file_code: Optional[str] = None
    file_url: Optional[str] = None
    error: Optional[str] = None

class CommentResult(BaseModel):
    success: bool
    comment_id: Optional[str] = None
    error: Optional[str] = None

class QRGenerationResult(BaseModel):
    success: bool
    qr_type: Optional[str] = None
    amount: Optional[float] = None
    field_used: Optional[str] = None
    node_name: Optional[str] = None
    comment_id: Optional[str] = None
    error: Optional[str] = None
    processing_info: Optional[Dict[str, Any]] = None

class CacheStatus(BaseModel):
    total_cached_qr: int
    active_cache: Dict[str, Dict[str, Any]]
    cache_duration_minutes: int
    current_time: str
