from fastapi import APIRouter, Depends
from app.domains.qr_generation.models import QRGenerationResult
from app.domains.qr_generation.services.qr_processor import qr_processor
from app.core.infrastructure.lark_service import lark_service

router = APIRouter(prefix="/qr", tags=["QR Generation"])

@router.post("/process/{instance_code}", response_model=QRGenerationResult)
async def manual_process_qr(instance_code: str):
    """Enhanced manual QR processing với domain models"""
    try:
        access_token = await lark_service.get_access_token()
        if not access_token:
            return QRGenerationResult(
                success=False,
                error="Cannot get access token"
            )
        
        # Process the instance
        result = await qr_processor.process_approval_with_qr_comment(instance_code, access_token)
        
        return QRGenerationResult(
            success=result,
            processing_info={
                "instance_code": instance_code,
                "processed": result
            }
        )
            
    except Exception as e:
        return QRGenerationResult(
            success=False,
            error=str(e)
        )

@router.get("/cache/status")
async def get_qr_cache_status():
    """Xem trạng thái QR cache"""
    from app.core.infrastructure.cache_service import cache_service
    cache_status = cache_service.get_cache_status()
    return cache_status.get('qr_cache', {})

@router.post("/cache/clear")
async def clear_qr_cache():
    """Clear QR cache"""
    from app.core.infrastructure.cache_service import cache_service
    result = cache_service.clear_cache()
    return {
        "message": "QR cache cleared",
        "details": result
    }
