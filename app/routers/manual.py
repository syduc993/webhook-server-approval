from fastapi import APIRouter
import json
from app.services.lark_service import lark_service
from app.services.qr_processor import qr_processor
from app.utils.amount_detector import AmountDetector
import os
import pandas as pd
from app.config.settings import settings

router = APIRouter()
amount_detector = AmountDetector()

@router.post("/process/{instance_code}")
async def manual_process_instance(instance_code: str):
    """Enhanced manual processing với detailed results"""
    try:
        access_token = await lark_service.get_access_token()
        if not access_token:
            return {"success": False, "error": "Cannot get access token"}
        
        # Get detailed processing info trước khi process
        api_response = await lark_service.get_approval_instance(instance_code, access_token)
        
        processing_info = {"instance_code": instance_code}
        
        if api_response:
            # Get node check info
            node_check = qr_processor.check_pending_allowed_node_in_task_list(api_response)
            processing_info["node_check"] = node_check
            
            # Get field detection info if node found
            if node_check['found'] and 'data' in api_response and 'form' in api_response['data']:
                form_str = api_response['data']['form']
                form_data = json.loads(form_str)
                
                node_id = node_check['node_id']
                amount_result = amount_detector.get_amount_and_type_for_node(node_id, form_data)
                processing_info["amount_detection"] = amount_result
        
        # Process the instance
        result = await qr_processor.process_approval_with_qr_comment(instance_code, access_token)
        
        return {
            "success": result,
            "message": f"{'Successfully processed' if result else 'Failed to process'} instance {instance_code}",
            "processing_info": processing_info
        }
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/events")
async def get_events():
    """Xem events đã nhận"""
    try:
        if os.path.exists(settings.EVENTS_FILE):
            df = pd.read_csv(settings.EVENTS_FILE, encoding='utf-8')
            return {
                "total_events": len(df),
                "latest_events": df.tail(20).to_dict('records')
            }
        return {"message": "No events found"}
    except Exception as e:
        return {"error": str(e)}
