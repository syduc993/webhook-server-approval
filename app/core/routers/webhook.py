import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.core.infrastructure.event_bus import event_bus
from app.core.utils.helpers import get_event_type, extract_instance_code
from app.core.config.settings import settings

router = APIRouter()

@router.post("/webhook")
async def handle_lark_webhook(request: Request):
    """
    Xử lý webhook từ Lark với kiến trúc DDD

    Chức năng chính:
    - Nhận và xử lý các sự kiện webhook từ Lark
    - Xác thực URL verification cho webhook setup
    - Xử lý các sự kiện phê duyệt qua event bus pattern
    - Trả về response phù hợp cho từng loại event

    Args:
        request (Request): HTTP request chứa webhook data từ Lark

    Returns:
        JSONResponse: 
            - Đối với URL verification: {"challenge": "..."}
            - Đối với events thành công: {"status": "success", "architecture": "DDD"}
            - Đối với lỗi: {"error": "..."} với status 500
    """
    try:
        data = await request.json()

        # =================================================================
        # BẮT ĐẦU LOG DEBUG: In ra toàn bộ payload của webhook để kiểm tra
        # =================================================================
        #print("👇----- [DEBUG] BẮT ĐẦU PAYLOAD WEBHOOK THÔ -----👇")
        # Sử dụng json.dumps để in ra cấu trúc JSON đẹp mắt, dễ đọc
        #print(json.dumps(data, indent=2, ensure_ascii=False))
        #print("👆----- [DEBUG] KẾT THÚC PAYLOAD WEBHOOK THÔ -----👆")
        # =================================================================


        print(f"📨 Nhận được webhook: {get_event_type(data)}")

        # Xử lý xác thực URL khi setup webhook
        if data.get("type") == "url_verification":
            print("🔐 Đang xử lý URL verification")
            return JSONResponse(content={"challenge": data.get("challenge")})

        # Xử lý các sự kiện phê duyệt thông qua event bus
        event_type = get_event_type(data)
        if "approval" in event_type.lower():
            instance_code = extract_instance_code(data)
            if instance_code:
                # Trích xuất approval_code để xác định quy trình
                event_body = data.get("event", {})
                approval_code = event_body.get("approval_code")

                if approval_code:
                    print(f"🔍 Đang xử lý instance: {instance_code} cho quy trình: {approval_code}")

                    # Thêm approval_code vào payload của event bus
                    print("📡 Đang phát hành event qua event bus...")
                    await event_bus.publish("approval.instance.updated", {
                        "instance_code": instance_code,
                        "approval_code": approval_code,
                        "event_type": event_type,
                        "timestamp": data.get("header", {}).get("create_time"),
                        "raw_data": data
                    })
                    print("✅ Đã phát hành event thành công")
                else:
                    print(f"⚠️ Không tìm thấy 'approval_code' trong event cho instance: {instance_code}. Bỏ qua.")
            else:
                print("⚠️ Không tìm thấy 'instance_code' trong event phê duyệt.")

        print("🎉 Xử lý webhook hoàn tất")
        return JSONResponse(content={"status": "success", "architecture": "DDD"})

    except Exception as e:
        print(f"❌ Lỗi khi xử lý webhook: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)