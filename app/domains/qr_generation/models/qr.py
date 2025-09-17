from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum

class QRType(str, Enum):
    ADVANCE = "advance"
    PAYMENT = "payment"
    NONE = "none"

class BankInfo(BaseModel):
    bank_id: str
    account_no: str
    account_name: str

class AmountDetectionResult(BaseModel):
    advance_amount: Optional[float] = None
    payment_amount: Optional[float] = None
    advance_field_found: bool = False
    payment_field_found: bool = False
    all_amount_fields: Dict[str, Any] = {}
    fields_used: Dict[str, Optional[str]] = {}

class QRTypeResult(BaseModel):
    qr_type: QRType
    amount: Optional[float] = None
    field_used: Optional[str] = None
    reason: str

class NodeProcessingResult(BaseModel):
    success: bool
    qr_type: QRType = QRType.NONE
    amount: Optional[float] = None
    field_used: Optional[str] = None
    node_strategy: Optional[str] = None
    reason: Optional[str] = None
    error: Optional[str] = None
    field_detection: Optional[AmountDetectionResult] = None

class QRGenerationRequest(BaseModel):
    instance_code: str
    node_id: str
    qr_type: QRType
    amount: int
    bank_info: BankInfo
    description: str

class QRGenerationResult(BaseModel):
    success: bool
    qr_type: Optional[QRType] = None
    amount: Optional[float] = None
    field_used: Optional[str] = None
    node_name: Optional[str] = None
    comment_id: Optional[str] = None
    error: Optional[str] = None
    processing_info: Optional[Dict[str, Any]] = None
