from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from enum import Enum


class ValidationType(str, Enum):
    AMOUNT_SUM = "amount_sum_validation"

    ADVANCE_AMOUNT_MISMATCH = "advance_amount_mismatch"      # Tạm ứng
    PAYMENT_AMOUNT_MISMATCH = "payment_amount_mismatch"      # Thanh toán  
    TOTAL_AMOUNT_MISMATCH = "total_amount_mismatch"          # Tổng amount
    
    WORKFLOW_STATUS = "workflow_status_validation" 
    FIELD_CONSISTENCY = "field_consistency_validation"
    PAYMENT_CONSISTENCY = "payment_consistency_validation"
    TOTAL_PAYMENT_VALIDATION = "total_payment_validation"


class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    SKIPPED = "skipped"
    ERROR = "error"


class ValidationResult(BaseModel):
    """Enhanced validation result model with proper enums"""
    is_valid: bool
    validation_type: ValidationType
    status: ValidationStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    
    @classmethod
    def create_valid(cls, validation_type: ValidationType, message: str, details: Dict = None):
        return cls(
            is_valid=True,
            validation_type=validation_type,
            status=ValidationStatus.VALID,
            message=message,
            details=details or {}
        )
    
    @classmethod
    def create_invalid(cls, validation_type: ValidationType, message: str, details: Dict = None):
        return cls(
            is_valid=False,
            validation_type=validation_type,
            status=ValidationStatus.INVALID,
            message=message,
            details=details or {}
        )
    
    @classmethod
    def create_skipped(cls, validation_type: ValidationType, message: str, details: Dict = None):
        return cls(
            is_valid=True,  # Skipped is not a failure
            validation_type=validation_type,
            status=ValidationStatus.SKIPPED,
            message=message,
            details=details or {}
        )
    
    @classmethod
    def create_error(cls, validation_type: ValidationType, message: str, details: Dict = None):
        return cls(
            is_valid=False,
            validation_type=validation_type,
            status=ValidationStatus.ERROR,
            message=message,
            details=details or {}
        )


class ValidationRequest(BaseModel):
    instance_code: str
    form_data: List[Dict[str, Any]]
    task_list: List[Dict[str, Any]]
    node_id: Optional[str] = None


class ValidationResponse(BaseModel):
    success: bool
    instance_code: str
    validation_results: List[ValidationResult]
    invalid_count: int
    total_validations: int
    alerts_sent: bool = False
    webhook_sent: bool = False
    message: Optional[str] = None