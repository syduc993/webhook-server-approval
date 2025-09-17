from fastapi import APIRouter
from app.domains.validation.models import ValidationRequest, ValidationResponse
from app.domains.validation.services.validation_service import validation_service

router = APIRouter(prefix="/validation", tags=["Validation"])

@router.post("/validate", response_model=ValidationResponse)
async def validate_instance(request: ValidationRequest):
    """Manual validation của một instance"""
    try:
        # Chạy validations
        validation_results = validation_service.run_all_validations(
            request.form_data, 
            request.task_list, 
            request.node_id or "manual_validation"
        )
        
        invalid_count = len([r for r in validation_results if not r.is_valid])
        
        return ValidationResponse(
            success=True,
            instance_code=request.instance_code,
            validation_results=validation_results,
            invalid_count=invalid_count,
            total_validations=len(validation_results),
            message=f"Completed {len(validation_results)} validations, {invalid_count} issues found"
        )
        
    except Exception as e:
        return ValidationResponse(
            success=False,
            instance_code=request.instance_code,
            validation_results=[],
            invalid_count=0,
            total_validations=0,
            message=f"Validation error: {str(e)}"
        )

@router.get("/rules")
async def get_validation_rules():
    """Xem danh sách validation rules"""
    from app.domains.validation.models import ValidationType
    return {
        "available_rules": [vt.value for vt in ValidationType],
        "total_rules": len(ValidationType)
    }
