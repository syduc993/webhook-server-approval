import json
from app.core.config.settings import settings
# [THAY ĐỔI] Import các hàm helper mới từ node_config
from app.core.config.node_config import get_workflow_config, get_field_mapping, get_qr_trigger_config
from app.core.infrastructure.lark_service import lark_service
from app.core.infrastructure.cache_service import cache_service
from app.core.utils.field_extractor import FieldExtractor
from app.domains.qr_generation.services.vietqr_service import vietqr_service
from app.domains.qr_generation.models import QRType, BankInfo
from typing import Dict, Any

class QRProcessor:
    """
    Bộ xử lý QR chính - Quản lý logic nghiệp vụ tạo và xử lý mã QR cho hệ thống phê duyệt.
    
    [NÂNG CẤP] Class này giờ đây đọc cấu hình động từ APPROVAL_WORKFLOWS để hỗ trợ
    nhiều quy trình phê duyệt khác nhau.
    
    Attributes:
        field_extractor (FieldExtractor): Bộ trích xuất trường dữ liệu từ form.
    """

    def __init__(self):
        """Khởi tạo QRProcessor với các service cần thiết."""
        self.field_extractor = FieldExtractor()

    def validate_amount_value(self, amount_value) -> dict:
        """
        Validate và chuyển đổi giá trị số tiền.
        """
        try:
            if amount_value is None:
                return {'valid': False, 'amount': None, 'error': 'Số tiền không được để trống'}
            
            amount_float = float(amount_value)
            amount_int = int(amount_float)
            
            if amount_int <= 0:
                return {'valid': False, 'amount': amount_int, 'error': 'Số tiền phải lớn hơn 0'}
                
            return {'valid': True, 'amount': amount_int, 'error': None}
            
        except (ValueError, TypeError) as e:
            return {'valid': False, 'amount': None, 'error': f'Định dạng số tiền không hợp lệ: {str(e)}'}

    def _find_active_qr_trigger(self, task_list: list, form_data: list, qr_trigger_configs: list) -> Dict[str, Any]:
        """
        [HÀM MỚI] Tìm kiếm node đang hoạt động khớp với các điều kiện trong cấu hình qr_trigger_nodes.
        """
        # Tạo một map để tra cứu các node theo tên
        nodes_by_name = {}
        for task in task_list:
            node_name = task.get('node_name', '')
            if node_name not in nodes_by_name:
                nodes_by_name[node_name] = []
            nodes_by_name[node_name].append(task)
            
        # Duyệt qua từng cấu hình trigger (ví dụ: một cho tạm ứng, một cho thanh toán)
        for trigger_config in qr_trigger_configs:
            node_name_contains = trigger_config.get("node_name_contains")
            required_status = trigger_config.get("status")

            # Tìm tất cả các node có tên khớp với cấu hình
            matching_nodes = []
            for name, nodes in nodes_by_name.items():
                if node_name_contains in name:
                    matching_nodes.extend(nodes)

            print(f"🔍 Tìm thấy {len(matching_nodes)} node có tên chứa '{node_name_contains}'.")

            # Lặp qua các node đã tìm thấy để kiểm tra điều kiện
            for i, node in enumerate(matching_nodes, 1):
                node_id = node.get('node_id')
                node_status = node.get('status')
                print(f"   - Kiểm tra lần {i} (Node ID: {node_id[:8]}..., Trạng thái: {node_status})...")

                if node_status == required_status:
                    # Lấy template từ config để tạo tên trường động
                    yes_no_field_template = trigger_config.get("yes_no_field_template")
                    amount_field_template = trigger_config.get("amount_field_template")

                    yes_no_field_name = yes_no_field_template.format(i=i)
                    amount_field_name = amount_field_template.format(i=i)

                    yes_no_value = self.field_extractor.extract_field_value(form_data, yes_no_field_name)
                    
                    if yes_no_value == "Yes":
                        print(f"     ✅ Điều kiện thỏa mãn: Node {required_status} và người dùng chọn 'Yes'.")
                        amount_value = self.field_extractor.extract_field_value(form_data, amount_field_name)
                        
                        return {
                            "amount": amount_value,
                            "node_id": node_id,
                            "node_name": node.get('node_name'),
                            "qr_type": trigger_config.get("qr_type", "unknown"),
                            "field_used": amount_field_name,
                            "trigger_round": i
                        }
                    else:
                        print(f"     - Bỏ qua: Người dùng không chọn 'Yes' cho lần {i} (Giá trị: {yes_no_value}).")
                else:
                    print(f"     - Bỏ qua: Trạng thái node không phải {required_status}.")

        return None # Không tìm thấy trigger nào hoạt động

    # [THAY ĐỔI] Signature của hàm đã thay đổi để nhận approval_code
    async def process_approval_with_qr_comment(self, instance_code: str, approval_code: str, access_token: str) -> bool:
        """
        [NÂNG CẤP] Xử lý phê duyệt bằng cách đọc cấu hình động dựa trên approval_code.
        """
        try:
            # Bước 1: Lấy cấu hình cho quy trình hiện tại
            workflow_config = get_workflow_config(approval_code)
            if not workflow_config:
                print(f"❌ Không tìm thấy cấu hình cho quy trình '{approval_code}'. Bỏ qua.")
                return True # Coi như thành công vì không có gì để làm

            print(f"⚙️ Áp dụng cấu hình cho quy trình: {workflow_config.get('name')}")

            # Bước 2: Lấy thông tin chi tiết của instance
            api_response = await lark_service.get_approval_instance(instance_code, access_token)
            if not api_response or 'data' not in api_response:
                print(f"❌ Không thể lấy thông tin instance {instance_code}")
                return False
            
            task_list = api_response['data'].get('task_list', [])
            form_data = json.loads(api_response['data'].get('form', '[]'))

            # Bước 3: [LOGIC MỚI] Tìm node đang hoạt động dựa trên cấu hình
            qr_trigger_configs = workflow_config.get('qr_trigger_nodes', [])
            active_trigger_info = self._find_active_qr_trigger(task_list, form_data, qr_trigger_configs)

            if not active_trigger_info:
                print(f"⏭️ Không có trigger tạo QR nào đang hoạt động cho instance {instance_code}. Bỏ qua.")
                return True

            # Bước 4: Trích xuất thông tin từ trigger đã tìm thấy
            matching_node_id = active_trigger_info['node_id']
            qr_type = active_trigger_info['qr_type']
            amount_value = active_trigger_info['amount']
            field_used = active_trigger_info['field_used']
            node_name = active_trigger_info['node_name']
            trigger_round = active_trigger_info['trigger_round']
            
            # Bước 5: Kiểm tra duplicate TRƯỚC KHI tạo QR
            if cache_service.is_qr_recently_generated(
                instance_code, matching_node_id, qr_type, 
                settings.QR_CACHE_DURATION_MINUTES
            ):
                print(f"⚠️ PHÁT HIỆN TRÙNG LẶP: QR {qr_type.upper()} cho node {node_name} đã được tạo gần đây.")
                return True
            
            print(f"💰 Chi tiết tạo QR cho lần {trigger_round}:")
            print(f"   - Loại: {qr_type}")
            print(f"   - Số tiền: {amount_value}")
            print(f"   - Trường sử dụng: {field_used}")
            print(f"   - Node kích hoạt: {node_name} ({matching_node_id[:8]}...)")
            
            # Bước 6: Validate số tiền
            amount_validation = self.validate_amount_value(amount_value)
            if not amount_validation['valid']:
                print(f"❌ Số tiền không hợp lệ: {amount_validation['error']}")
                return False
            amount_int = amount_validation['amount']

            # Bước 7: [LOGIC MỚI] Trích xuất thông tin ngân hàng từ field_mappings
            field_mappings = workflow_config.get('field_mappings', {})
            bank_id_field = field_mappings.get('bank_name')
            account_no_field = field_mappings.get('account_number')
            account_name_field = field_mappings.get('beneficiary_name')

            if not all([bank_id_field, account_no_field, account_name_field]):
                 print(f"❌ Lỗi cấu hình: Thiếu 'bank_name', 'account_number', hoặc 'beneficiary_name' trong field_mappings của quy trình {approval_code}.")
                 return False

            bank_id = self.field_extractor.extract_field_value(form_data, bank_id_field)
            account_no = self.field_extractor.extract_field_value(form_data, account_no_field)
            account_name = self.field_extractor.extract_field_value(form_data, account_name_field)

            if not all([bank_id, account_no, account_name]):
                missing = [f for f, v in {bank_id_field: bank_id, account_no_field: account_no, account_name_field: account_name}.items() if not v]
                print(f"❌ Thiếu thông tin ngân hàng trên form: {', '.join(missing)}")
                return False
            
            # Bước 8: Tạo mô tả QR
            description = vietqr_service.generate_qr_description(f"{qr_type}{trigger_round}", instance_code)
            
            # Bước 9: Tạo VietQR code
            qr_image_buffer = vietqr_service.create_qr_in_memory(
                bank_id, account_no, amount_int, description, account_name
            )
            if not qr_image_buffer:
                print("❌ Không thể tạo mã VietQR")
                return False
            
            # Bước 10: Upload ảnh lên Lark
            filename = f"{instance_code}_{qr_type}{trigger_round}_qr.png"
            upload_result = await lark_service.upload_image_to_approval(qr_image_buffer, filename, access_token)
            if not upload_result['success']:
                print(f"❌ Upload thất bại: {upload_result['error']}")
                return False
            
            # Bước 11: Đánh dấu đã tạo QR
            cache_service.mark_qr_as_generated(instance_code, matching_node_id, qr_type)
            
            # Bước 12: Tạo comment
            comment_result = await lark_service.create_enhanced_comment_with_image(
                instance_code=instance_code,
                file_url=upload_result['file_url'],
                file_code=upload_result['file_code'],
                filename=filename,
                qr_type=f"{qr_type.capitalize()} Lần {trigger_round}",
                amount=amount_int,
                node_name=node_name,
                access_token=access_token
            )
            
            if comment_result['success']:
                print(f"✅ Hoàn thành xử lý phê duyệt {instance_code}")
                return True
            else:
                print(f"❌ Tạo comment thất bại: {comment_result['error']}")
                return False
                
        except Exception as e:
            print(f"❌ Lỗi nghiêm trọng khi xử lý phê duyệt: {e}")
            import traceback
            traceback.print_exc()
            return False

qr_processor = QRProcessor()













# class QRProcessor:
#     """
#     Bộ xử lý QR chính - Quản lý logic nghiệp vụ tạo và xử lý mã QR cho hệ thống phê duyệt.
    
#     Class này xử lý toàn bộ quy trình từ việc kiểm tra node phê duyệt, trích xuất dữ liệu,
#     validate thông tin, tạo mã VietQR và upload lên hệ thống Lark.
    
#     Attributes:
#         field_extractor (FieldExtractor): Bộ trích xuất trường dữ liệu từ form
#     """

#     def __init__(self):
#         """Khởi tạo QRProcessor với các service cần thiết."""
#         self.field_extractor = FieldExtractor()
#         # self.amount_detector không còn cần thiết nữa
#         # self.amount_detector = AmountDetector()

#     # --- HÀM CŨ NÀY VẪN GIỮ LẠI NHƯNG KHÔNG ĐƯỢC GỌI TRONG HÀM CHÍNH ---
#     def check_pending_allowed_node_in_task_list(self, api_response: dict, node_config: dict = None) -> dict:
#         """
#         Kiểm tra node có trạng thái phù hợp và đáp ứng các điều kiện bổ sung.
#         (Hàm này không còn được sử dụng trong luồng chính tạo QR động)
#         """
#         if node_config is None:
#             node_config = NODE_CONFIG
#         # ... logic của hàm cũ giữ nguyên ...
#         try:
#             # Trích xuất dữ liệu từ API response
#             data = api_response.get('data', {})
#             task_list = data.get('task_list', [])
#             configured_node_ids = list(node_config.keys())
            
#             # Tạo map để tra cứu nhanh trạng thái của các node
#             node_status_map = {}
#             for task in task_list:
#                 node_id = task.get('node_id')
#                 status = task.get('status', 'UNKNOWN')
#                 if node_id:
#                     node_status_map[node_id] = status
            
#             print(f"🔍 Đang kiểm tra các node với điều kiện bổ sung:")
#             for node_id, config in node_config.items():
#                 required_status = config.get('required_status', 'PENDING')
#                 additional_conditions = config.get('additional_conditions', [])
#                 print(f"   • {node_id[:8]}... - {config['name']} (yêu cầu: {required_status})")
#                 if additional_conditions:
#                     for condition in additional_conditions:
#                         print(f"     + Điều kiện thêm: {condition['node_id'][:8]}... phải ở trạng thái {condition['required_status']}")
            
#             print(f"📋 Danh sách task chứa {len(task_list)} nhiệm vụ")
            
#             matching_configured_nodes = []
            
#             # Duyệt qua từng node đã cấu hình
#             for node_id in configured_node_ids:
#                 config = node_config[node_id]
#                 required_status = config.get('required_status', 'PENDING')
#                 current_status = node_status_map.get(node_id, 'NOT_FOUND')
                
#                 # Kiểm tra điều kiện chính
#                 if current_status != required_status:
#                     continue
                    
#                 # Kiểm tra các điều kiện bổ sung
#                 additional_conditions = config.get('additional_conditions', [])
#                 all_conditions_met = True
                
#                 for condition in additional_conditions:
#                     condition_node_id = condition['node_id']
#                     condition_required_status = condition['required_status']
#                     condition_current_status = node_status_map.get(condition_node_id, 'NOT_FOUND')
                    
#                     print(f"🔍 Kiểm tra điều kiện bổ sung: {condition_node_id[:8]}... ")
#                     print(f"   Yêu cầu: {condition_required_status}, Hiện tại: {condition_current_status}")
                    
#                     if condition_current_status != condition_required_status:
#                         all_conditions_met = False
#                         print(f"❌ Điều kiện bổ sung không đáp ứng cho {node_id[:8]}...")
#                         break
#                     else:
#                         print(f"✅ Điều kiện bổ sung đã đáp ứng")
                
#                 # Nếu tất cả điều kiện đều thỏa mãn
#                 if all_conditions_met:
#                     matching_configured_nodes.append({
#                         'node_id': node_id,
#                         'config': config,
#                         'strategy': config['strategy'],
#                         'matched_status': current_status,
#                         'required_status': required_status,
#                         'additional_conditions_met': True
#                     })
#                     print(f"✅ Tìm thấy node phù hợp: {node_id[:8]}... ({config['name']}) - Trạng thái: {current_status}")
            
#             # Trả về node phù hợp đầu tiên
#             if matching_configured_nodes:
#                 first_matching = matching_configured_nodes[0]
#                 return {
#                     'found': True,
#                     'node_id': first_matching['node_id'],
#                     'node_config': first_matching['config'],
#                     'strategy': first_matching['strategy'],
#                     'matched_status': first_matching['matched_status'],
#                     'required_status': first_matching['required_status'],
#                     'all_tasks': task_list,
#                     'all_matching_configured': matching_configured_nodes,
#                     'node_status_map': node_status_map
#                 }
#             else:
#                 print(f"❌ Không tìm thấy node nào đáp ứng tất cả điều kiện")
#                 return {
#                     'found': False,
#                     'node_id': None,
#                     'node_config': None,
#                     'strategy': None,
#                     'matched_status': None,
#                     'all_tasks': task_list,
#                     'all_matching_configured': [],
#                     'node_status_map': node_status_map
#                 }
            
#         except Exception as e:
#             print(f"❌ Lỗi khi kiểm tra node: {e}")
#             return {
#                 'found': False,
#                 'error': str(e),
#                 'all_tasks': [],
#                 'all_matching_configured': []
#             }