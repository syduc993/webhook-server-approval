from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class FormField(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    value: Optional[Any] = None

class TaskInfo(BaseModel):
    node_id: Optional[str] = None
    status: Optional[str] = None
    task_id: Optional[str] = None
    node_name: Optional[str] = None

class ApprovalInstance(BaseModel):
    instance_code: str
    status: Optional[str] = None
    form: Optional[str] = None
    task_list: Optional[List[TaskInfo]] = None

class AmountDetectionResult(BaseModel):
    advance_amount: Optional[float] = None
    payment_amount: Optional[float] = None
    advance_field_found: bool = False
    payment_field_found: bool = False
    all_amount_fields: Dict[str, Any] = {}
    fields_used: Dict[str, Optional[str]] = {}

class QRTypeResult(BaseModel):
    qr_type: str  # 'advance', 'payment', 'none'
    amount: Optional[float] = None
    field_used: Optional[str] = None
    reason: str

class NodeProcessingResult(BaseModel):
    success: bool
    qr_type: str = 'none'
    amount: Optional[float] = None
    field_used: Optional[str] = None
    node_strategy: Optional[str] = None
    reason: Optional[str] = None
    error: Optional[str] = None
    field_detection: Optional[AmountDetectionResult] = None

class ValidationResult(BaseModel):
    """Model for validation results - extensible for future validations"""
    is_valid: bool
    validation_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
