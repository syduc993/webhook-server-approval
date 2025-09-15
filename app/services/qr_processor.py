"""
QR Processing Service - Main business logic for QR generation and processing
"""
import json
from typing import Dict, Optional, List
from app.config.settings import settings
from app.config.node_config import NODE_CONFIG, get_node_config
from app.services.lark_service import lark_service
from app.services.vietqr_service import vietqr_service
from app.services.cache_service import cache_service
from app.services.validation_service import validation_service
from app.utils.field_extractor import FieldExtractor
from app.utils.amount_detector import AmountDetector
from app.models.approval import NodeProcessingResult

class QRProcessor:
    def __init__(self):
        self.field_extractor = FieldExtractor()
        self.amount_detector = AmountDetector()
    
    def check_pending_allowed_node_in_task_list(self, api_response: dict, node_config: dict = None) -> dict:
        """
        Kiểm tra node có status phù hợp + additional conditions
        """
        if node_config is None:
            node_config = NODE_CONFIG
            
        try:
            data = api_response.get('data', {})
            task_list = data.get('task_list', [])
            configured_node_ids = list(node_config.keys())
            
            # Tạo dict để lookup status của tất cả nodes
            node_status_map = {}
            for task in task_list:
                node_id = task.get('node_id')
                status = task.get('status', 'UNKNOWN')
                if node_id:
                    node_status_map[node_id] = status
            
            print(f"🔍 Checking nodes with additional conditions:")
            for node_id, config in node_config.items():
                required_status = config.get('required_status', 'PENDING')
                additional_conditions = config.get('additional_conditions', [])
                print(f"   • {node_id[:8]}... - {config['name']} (requires: {required_status})")
                if additional_conditions:
                    for condition in additional_conditions:
                        print(f"     + Additional: {condition['node_id'][:8]}... must be {condition['required_status']}")
            
            print(f"📋 Task list contains {len(task_list)} tasks")
            
            matching_configured_nodes = []
            
            for node_id in configured_node_ids:
                config = node_config[node_id]
                required_status = config.get('required_status', 'PENDING')
                current_status = node_status_map.get(node_id, 'NOT_FOUND')
                
                # Check primary condition
                if current_status != required_status:
                    continue
                    
                # Check additional conditions
                additional_conditions = config.get('additional_conditions', [])
                all_conditions_met = True
                
                for condition in additional_conditions:
                    condition_node_id = condition['node_id']
                    condition_required_status = condition['required_status']
                    condition_current_status = node_status_map.get(condition_node_id, 'NOT_FOUND')
                    
                    print(f"🔍 Checking additional condition: {condition_node_id[:8]}... ")
                    print(f"   Required: {condition_required_status}, Current: {condition_current_status}")
                    
                    if condition_current_status != condition_required_status:
                        all_conditions_met = False
                        print(f"❌ Additional condition not met for {node_id[:8]}...")
                        break
                    else:
                        print(f"✅ Additional condition met")
                
                if all_conditions_met:
                    matching_configured_nodes.append({
                        'node_id': node_id,
                        'config': config,
                        'strategy': config['strategy'],
                        'matched_status': current_status,
                        'required_status': required_status,
                        'additional_conditions_met': True
                    })
                    print(f"✅ Full match found: {node_id[:8]}... ({config['name']}) - Status: {current_status}")
            
            # Return first matching configured node
            if matching_configured_nodes:
                first_matching = matching_configured_nodes[0]
                return {
                    'found': True,
                    'node_id': first_matching['node_id'],
                    'node_config': first_matching['config'],
                    'strategy': first_matching['strategy'],
                    'matched_status': first_matching['matched_status'],
                    'required_status': first_matching['required_status'],
                    'all_tasks': task_list,
                    'all_matching_configured': matching_configured_nodes,
                    'node_status_map': node_status_map
                }
            else:
                print(f"❌ No nodes matching all conditions found")
                return {
                    'found': False,
                    'node_id': None,
                    'node_config': None,
                    'strategy': None,
                    'matched_status': None,
                    'all_tasks': task_list,
                    'all_matching_configured': [],
                    'node_status_map': node_status_map
                }
            
        except Exception as e:
            print(f"❌ Error checking nodes: {e}")
            return {
                'found': False,
                'error': str(e),
                'all_tasks': [],
                'all_matching_configured': []
            }
    
    def validate_amount_value(self, amount_value) -> dict:
        """Validate và convert amount value"""
        try:
            if amount_value is None:
                return {'valid': False, 'amount': None, 'error': 'Amount is None'}
                
            # Convert to float first, then int
            amount_float = float(amount_value)
            amount_int = int(amount_float)
            
            if amount_int <= 0:
                return {'valid': False, 'amount': amount_int, 'error': 'Amount must be positive'}
                
            return {'valid': True, 'amount': amount_int, 'error': None}
            
        except (ValueError, TypeError) as e:
            return {'valid': False, 'amount': None, 'error': f'Invalid amount format: {str(e)}'}
    
    async def process_approval_with_qr_comment(self, instance_code: str, access_token: str) -> bool:
        """
        Enhanced version với duplicate detection và validation
        Xử lý approval với smart field detection, multiple node support và flexible status requirements
        """
        try:
            # Lấy instance details
            api_response = await lark_service.get_approval_instance(instance_code, access_token)
            if not api_response:
                return False
            
            # Check nodes với required status
            node_check_result = self.check_pending_allowed_node_in_task_list(api_response)
            
            if not node_check_result['found']:
                print(f"⏭️ Skipping QR generation - no matching configured nodes found")
                return True  # Return True vì không phải lỗi, chỉ là skip
            
            matching_node_id = node_check_result['node_id']
            node_config = node_check_result['node_config']
            node_strategy = node_check_result['strategy']
            matched_status = node_check_result.get('matched_status', 'UNKNOWN')
            required_status = node_check_result.get('required_status', 'PENDING')
            
            print(f"✅ Processing node: {node_config['name']} (strategy: {node_strategy})")
            print(f"   Status: {matched_status} (required: {required_status})")
            
            # Extract form data
            if 'data' not in api_response or 'form' not in api_response['data']:
                print("❌ Không tìm thấy form data")
                return False
                
            form_str = api_response['data']['form']
            form_data = json.loads(form_str)
            
            # NEW: Run validations if enabled
            if settings.ENABLE_AMOUNT_VALIDATION or settings.ENABLE_WORKFLOW_ALERTS:
                task_list = api_response.get('data', {}).get('task_list', [])
                validation_results = validation_service.run_all_validations(
                    form_data, task_list, matching_node_id
                )
                
                # Log validation results
                for result in validation_results:
                    print(f"🔍 Validation: {result.message}")
                    if not result.is_valid and settings.ENABLE_WORKFLOW_ALERTS:
                        # TODO: Implement alert system (email, Slack, etc.)
                        print(f"🚨 ALERT: {result.message}")
            
            # Smart field detection theo node strategy
            amount_result = self.amount_detector.get_amount_and_type_for_node(matching_node_id, form_data)
            
            if not amount_result['success']:
                print(f"❌ Cannot determine amount/type: {amount_result.get('reason', 'Unknown error')}")
                if 'error' in amount_result:
                    print(f"    Error details: {amount_result['error']}")
                return False
            
            qr_type = amount_result['qr_type']
            amount_value = amount_result['amount']
            field_used = amount_result['field_used']
            
            # Check duplicate TRƯỚC KHI tạo QR
            if cache_service.is_qr_recently_generated(
                instance_code, matching_node_id, qr_type, 
                settings.QR_CACHE_DURATION_MINUTES
            ):
                print(f"⚠️ DUPLICATE DETECTED: QR {qr_type.upper()} for node {node_config['name']} already generated recently")
                print(f"   → SKIPPING QR generation to prevent duplicate")
                return True  # Return success vì không phải lỗi, chỉ là skip duplicate
            
            print(f"💰 QR Generation Details:")
            print(f"   - Type: {qr_type}")
            print(f"   - Amount: {amount_value:,} VND")
            print(f"   - Field used: {field_used}")
            print(f"   - Node strategy: {node_strategy}")
            print(f"   - Trigger status: {matched_status}")
            
            # Validate amount
            amount_validation = self.validate_amount_value(amount_value)
            if not amount_validation['valid']:
                print(f"❌ Invalid amount: {amount_validation['error']}")
                return False
                
            amount_int = amount_validation['amount']
            
            # Extract thông tin ngân hàng
            bank_id = self.field_extractor.extract_field_value(form_data, 'Ngân hàng')
            account_no = self.field_extractor.extract_field_value(form_data, 'Số tài khoản ngân hàng')
            account_name = self.field_extractor.extract_field_value(form_data, 'Tên người thụ hưởng')
            
            # Kiểm tra thông tin ngân hàng
            if not all([bank_id, account_no, account_name]):
                missing_fields = []
                if not bank_id: missing_fields.append('Ngân hàng')
                if not account_no: missing_fields.append('Số tài khoản ngân hàng')
                if not account_name: missing_fields.append('Tên người thụ hưởng')
                
                print(f"❌ Thiếu thông tin ngân hàng: {', '.join(missing_fields)}")
                return False
            
            # Generate QR description theo type
            description = vietqr_service.generate_qr_description(qr_type, instance_code)
            
            print(f"🏦 Tạo VietQR với thông tin:")
            print(f"   - Ngân hàng: {bank_id}")
            print(f"   - Số TK: {account_no}")
            print(f"   - Tên: {account_name}")
            print(f"   - Số tiền: {amount_int:,} VND")
            print(f"   - Mô tả: {description}")
            
            # Tạo VietQR code trong bộ nhớ
            qr_image_buffer = vietqr_service.create_qr_in_memory(
                bank_id=bank_id,
                account_no=account_no,
                amount=amount_int,
                description=description,
                account_name=account_name
            )
            
            if not qr_image_buffer:
                print("❌ Không thể tạo VietQR code")
                return False
            
            # Upload ảnh lên Lark Approval
            filename = f"{instance_code}_{qr_type}_qr.png"
            upload_result = await lark_service.upload_image_to_approval(qr_image_buffer, filename, access_token)
            
            if not upload_result['success']:
                print(f"❌ Upload thất bại: {upload_result['error']}")
                return False
            
            # Đánh dấu đã tạo QR SAU KHI upload thành công
            cache_service.mark_qr_as_generated(instance_code, matching_node_id, qr_type)
            
            # Enhanced comment với type và status info
            comment_result = await lark_service.create_enhanced_comment_with_image(
                instance_code=instance_code,
                file_url=upload_result['file_url'],
                file_code=upload_result['file_code'],
                filename=filename,
                qr_type=qr_type,
                amount=amount_int,
                node_name=node_config['name'],
                access_token=access_token
            )
            
            if comment_result['success']:
                print(f"✅ Hoàn thành xử lý approval {instance_code}")
                print(f"💰 Loại: {qr_type.upper()} | Số tiền: {amount_int:,} VND")
                print(f"🏷️ Node: {node_config['name']} | Status: {matched_status}")
                print(f"📋 Field: {field_used} | Strategy: {node_strategy}")
                print(f"💬 Comment ID: {comment_result['comment_id']}")
                return True
            else:
                print(f"❌ Tạo comment thất bại: {comment_result['error']}")
                return False
                
        except Exception as e:
            print(f"❌ Lỗi xử lý approval: {e}")
            import traceback
            traceback.print_exc()
            return False

# Global processor instance
qr_processor = QRProcessor()
