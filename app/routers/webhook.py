from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.services.lark_service import lark_service
from app.services.qr_processor import qr_processor
from app.utils.helpers import save_event_to_csv, get_event_type, extract_instance_code
from app.config.settings import settings

router = APIRouter()

@router.post("/webhook")
async def handle_lark_webhook(request: Request):
    try:
        data = await request.json()
        print(f"📨 Received webhook: {get_event_type(data)}")
        
        # Handle URL verification
        if data.get("type") == "url_verification":
            return JSONResponse(content={"challenge": data.get("challenge")})
        
        # Lưu event vào CSV
        await save_event_to_csv(data, settings.EVENTS_FILE)
        
        # Xử lý approval event
        event_type = get_event_type(data)
        if "approval" in event_type.lower():
            instance_code = extract_instance_code(data)
            if instance_code:
                print(f"🔍 Processing approval instance: {instance_code}")
                
                # Lấy access token
                access_token = await lark_service.get_access_token()
                if access_token:
                    # Xử lý tự động: check node_id -> lấy thông tin -> tạo QR -> upload -> comment
                    await qr_processor.process_approval_with_qr_comment(instance_code, access_token)
                else:
                    print("❌ Không thể lấy access token")
        
        return JSONResponse(content={"status": "success"})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
