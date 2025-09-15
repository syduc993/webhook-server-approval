from fastapi import APIRouter
import json
from app.services.lark_service import lark_service
from app.services.qr_processor import qr_processor
from app.utils.amount_detector import AmountDetector
from app.config.node_config import NODE_CONFIG

router = APIRouter()
amount_detector = AmountDetector()

@router.get("/instance/{instance_code}")
async def debug_instance(instance_code: str):
    """Debug instance với NODE_CONFIG"""
    try:
        access_token = await lark_service.get_access_token()
        if not access_token:
            return {"error": "Cannot get access token"}
        
        api_response = await lark_service.get_approval_instance(instance_code, access_token)
        if not api_response:
            return {"error": "Cannot get instance data"}
        
        # Sử dụng function với NODE_CONFIG
        check_result = qr_processor.check_pending_allowed_node_in_task_list(api_response)
        
        return {
            "instance_code": instance_code,
            "node_check_result": check_result,
            "node_config": NODE_CONFIG,
            "will_generate_qr": check_result['found'],
            "reason": f"Found {check_result.get('strategy', 'unknown')} node with required status" if check_result['found'] else "No matching configured nodes found"
        }
            
    except Exception as e:
        return {"error": str(e)}

@router.get("/instance/{instance_code}/fields")
async def debug_instance_fields(instance_code: str):
    """Debug chi tiết về fields trong form của instance"""
    try:
        access_token = await lark_service.get_access_token()
        if not access_token:
            return {"error": "Cannot get access token"}
        
        api_response = await lark_service.get_approval_instance(instance_code, access_token)
        if not api_response:
            return {"error": "Cannot get instance data"}
            
        if 'data' not in api_response or 'form' not in api_response['data']:
            return {"error": "No form data found"}
            
        form_str = api_response['data']['form']
        form_data = json.loads(form_str)
        
        # Enhanced field detection
        field_detection = amount_detector.detect_available_amount_fields(form_data)
        
        # Test với tất cả configured nodes
        node_results = {}
        for node_id, config in NODE_CONFIG.items():
            node_result = amount_detector.get_amount_and_type_for_node(node_id, form_data)
            node_results[config['name']] = {
                'node_id': node_id[:8] + '...',
                'strategy': config['strategy'],
                'result': node_result
            }
        
        # Extract tất cả field names để debug
        all_fields = []
        for field in form_data:
            field_info = {
                'name': field.get('name'),
                'type': field.get('type'),
                'value': field.get('value')
            }
            all_fields.append(field_info)
        
        return {
            "instance_code": instance_code,
            "field_detection": field_detection,
            "node_processing_results": node_results,
            "all_form_fields": all_fields,
            "total_fields": len(all_fields)
        }
            
    except Exception as e:
        return {"error": str(e)}
