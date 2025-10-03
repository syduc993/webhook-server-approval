import json
from app.core.config.settings import settings
# NODE_CONFIG và AmountDetector không còn cần thiết cho logic chính, nhưng giữ lại import để không ảnh hưởng các hàm phụ
from app.core.config.node_config import NODE_CONFIG
from app.core.config.field_constants import FFN
from app.core.infrastructure.lark_service import lark_service
from app.core.infrastructure.cache_service import cache_service
from app.core.utils.field_extractor import FieldExtractor
from app.domains.qr_generation.services.vietqr_service import vietqr_service
# AmountDetector không còn được sử dụng trong hàm chính nữa
# from app.domains.qr_generation.services.amount_detector import AmountDetector
from app.domains.qr_generation.models import QRType, BankInfo

class QRProcessor:
    """
    Bộ xử lý QR chính - Quản lý logic nghiệp vụ tạo và xử lý mã QR cho hệ thống phê duyệt.
    
    Class này xử lý toàn bộ quy trình từ việc kiểm tra node phê duyệt, trích xuất dữ liệu,
    validate thông tin, tạo mã VietQR và upload lên hệ thống Lark.
    
    Attributes:
        field_extractor (FieldExtractor): Bộ trích xuất trường dữ liệu từ form
    """

    def __init__(self):
        """Khởi tạo QRProcessor với các service cần thiết."""
        self.field_extractor = FieldExtractor()
        # self.amount_detector không còn cần thiết nữa
        # self.amount_detector = AmountDetector()

    # --- HÀM CŨ NÀY VẪN GIỮ LẠI NHƯNG KHÔNG ĐƯỢC GỌI TRONG HÀM CHÍNH ---
    def check_pending_allowed_node_in_task_list(self, api_response: dict, node_config: dict = None) -> dict:
        """
        Kiểm tra node có trạng thái phù hợp và đáp ứng các điều kiện bổ sung.
        (Hàm này không còn được sử dụng trong luồng chính tạo QR động)
        """
        if node_config is None:
            node_config = NODE_CONFIG
        # ... logic của hàm cũ giữ nguyên ...
        try:
            # Trích xuất dữ liệu từ API response
            data = api_response.get('data', {})
            task_list = data.get('task_list', [])
            configured_node_ids = list(node_config.keys())
            
            # Tạo map để tra cứu nhanh trạng thái của các node
            node_status_map = {}
            for task in task_list:
                node_id = task.get('node_id')
                status = task.get('status', 'UNKNOWN')
                if node_id:
                    node_status_map[node_id] = status
            
            print(f"🔍 Đang kiểm tra các node với điều kiện bổ sung:")
            for node_id, config in node_config.items():
                required_status = config.get('required_status', 'PENDING')
                additional_conditions = config.get('additional_conditions', [])
                print(f"   • {node_id[:8]}... - {config['name']} (yêu cầu: {required_status})")
                if additional_conditions:
                    for condition in additional_conditions:
                        print(f"     + Điều kiện thêm: {condition['node_id'][:8]}... phải ở trạng thái {condition['required_status']}")
            
            print(f"📋 Danh sách task chứa {len(task_list)} nhiệm vụ")
            
            matching_configured_nodes = []
            
            # Duyệt qua từng node đã cấu hình
            for node_id in configured_node_ids:
                config = node_config[node_id]
                required_status = config.get('required_status', 'PENDING')
                current_status = node_status_map.get(node_id, 'NOT_FOUND')
                
                # Kiểm tra điều kiện chính
                if current_status != required_status:
                    continue
                    
                # Kiểm tra các điều kiện bổ sung
                additional_conditions = config.get('additional_conditions', [])
                all_conditions_met = True
                
                for condition in additional_conditions:
                    condition_node_id = condition['node_id']
                    condition_required_status = condition['required_status']
                    condition_current_status = node_status_map.get(condition_node_id, 'NOT_FOUND')
                    
                    print(f"🔍 Kiểm tra điều kiện bổ sung: {condition_node_id[:8]}... ")
                    print(f"   Yêu cầu: {condition_required_status}, Hiện tại: {condition_current_status}")
                    
                    if condition_current_status != condition_required_status:
                        all_conditions_met = False
                        print(f"❌ Điều kiện bổ sung không đáp ứng cho {node_id[:8]}...")
                        break
                    else:
                        print(f"✅ Điều kiện bổ sung đã đáp ứng")
                
                # Nếu tất cả điều kiện đều thỏa mãn
                if all_conditions_met:
                    matching_configured_nodes.append({
                        'node_id': node_id,
                        'config': config,
                        'strategy': config['strategy'],
                        'matched_status': current_status,
                        'required_status': required_status,
                        'additional_conditions_met': True
                    })
                    print(f"✅ Tìm thấy node phù hợp: {node_id[:8]}... ({config['name']}) - Trạng thái: {current_status}")
            
            # Trả về node phù hợp đầu tiên
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
                print(f"❌ Không tìm thấy node nào đáp ứng tất cả điều kiện")
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
            print(f"❌ Lỗi khi kiểm tra node: {e}")
            return {
                'found': False,
                'error': str(e),
                'all_tasks': [],
                'all_matching_configured': []
            }


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

    async def process_approval_with_qr_comment(self, instance_code: str, access_token: str) -> bool:
        """
        Xử lý phê duyệt với tạo QR code và comment (phiên bản nâng cấp hỗ trợ nhiều lần tạm ứng).
        """
        try:
            # Bước 1: Lấy thông tin chi tiết của instance
            api_response = await lark_service.get_approval_instance(instance_code, access_token)
            if not api_response or 'data' not in api_response:
                print(f"❌ Không thể lấy thông tin instance {instance_code}")
                return False
            
            task_list = api_response['data'].get('task_list', [])
            form_str = api_response['data'].get('form', '[]')
            form_data = json.loads(form_str)

            # --- [LOGIC MỚI] Bắt đầu phần tìm kiếm lần tạm ứng hoạt động ---
            
            # 2.1: Tìm tất cả các node "Thủ quỹ chi tiền tạm ứng" trong quy trình
            cashier_nodes = [task for task in task_list if "Thủ quỹ chi tiền tạm ứng" in task.get('node_name', '')]
            print(f"🔍 Tìm thấy {len(cashier_nodes)} node 'Thủ quỹ chi tiền tạm ứng' trong quy trình.")

            active_advance_info = None
            
            # 2.2: Lặp qua các node thủ quỹ để tìm node đang PENDING
            for i, node in enumerate(cashier_nodes, 1):
                node_id = node.get('node_id')
                node_status = node.get('status')
                print(f"   - Kiểm tra lần tạm ứng {i} (Node ID: {node_id[:8]}..., Trạng thái: {node_status})...")

                # Điều kiện 1: Node phải ở trạng thái PENDING
                if node_status == 'PENDING':
                    # Điều kiện 2: Người dùng phải chọn "Yes" cho lần tạm ứng tương ứng
                    yes_no_field_name = f"Thanh toán tạm ứng lần {i}: Y/N"
                    amount_field_name = f"Số tiền tạm ứng lần {i}:"

                    yes_no_value = self.field_extractor.extract_field_value(form_data, yes_no_field_name)
                    
                    if yes_no_value == "Yes":
                        print(f"     ✅ Điều kiện thỏa mãn: Node PENDING và người dùng chọn 'Yes'.")
                        amount_value = self.field_extractor.extract_field_value(form_data, amount_field_name)
                        
                        active_advance_info = {
                            "amount": amount_value,
                            "node_id": node_id,
                            "node_name": node.get('node_name'),
                            "qr_type": "advance",
                            "field_used": amount_field_name,
                            "advance_round": i
                        }
                        print(f"     ➡️ Lần tạm ứng {i} được kích hoạt với số tiền: {amount_value}")
                        break # Tìm thấy rồi thì dừng lại
                    else:
                        print(f"     - Bỏ qua: Người dùng không chọn 'Yes' cho lần {i} (Giá trị: {yes_no_value}).")
                else:
                    print(f"     - Bỏ qua: Trạng thái node không phải PENDING.")

            # 2.3: Xử lý kết quả tìm kiếm
            if not active_advance_info:
                print(f"⏭️  Không có lần tạm ứng nào đang hoạt động (PENDING và được chọn 'Yes'). Bỏ qua tạo QR.")
                return True # Coi như thành công vì đã xử lý đúng (bỏ qua)

            # --- [LOGIC MỚI] Kết thúc phần tìm kiếm ---


            # --- [PHẦN GIỮ NGUYÊN] Tiếp tục xử lý với thông tin đã tìm được ---

            # Lấy các biến từ kết quả tìm kiếm
            matching_node_id = active_advance_info['node_id']
            qr_type = active_advance_info['qr_type']
            amount_value = active_advance_info['amount']
            field_used = active_advance_info['field_used']
            node_name = active_advance_info['node_name']
            
            # Bước 5: Kiểm tra duplicate TRƯỚC KHI tạo QR
            if cache_service.is_qr_recently_generated(
                instance_code, matching_node_id, qr_type, 
                settings.QR_CACHE_DURATION_MINUTES
            ):
                print(f"⚠️ PHÁT HIỆN TRÙNG LẶP: QR {qr_type.upper()} cho node {node_name} đã được tạo gần đây.")
                print(f"   → BỎ QUA tạo QR để tránh trùng lặp.")
                return True
            
            print(f"💰 Chi tiết tạo QR cho lần tạm ứng {active_advance_info['advance_round']}:")
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

            # Bước 7: Trích xuất thông tin ngân hàng
            bank_id = self.field_extractor.extract_field_value(form_data, FFN.BANK_NAME)
            account_no = self.field_extractor.extract_field_value(form_data, FFN.BANK_ACCOUNT_NUMBER)
            account_name = self.field_extractor.extract_field_value(form_data, FFN.BENEFICIARY_NAME)

            if not all([bank_id, account_no, account_name]):
                missing = [f for f, v in {FFN.BANK_NAME: bank_id, FFN.BANK_ACCOUNT_NUMBER: account_no, FFN.BENEFICIARY_NAME: account_name}.items() if not v]
                print(f"❌ Thiếu thông tin ngân hàng: {', '.join(missing)}")
                return False
            
            # Bước 8: Tạo mô tả QR theo loại
            description = vietqr_service.generate_qr_description(f"{qr_type}{active_advance_info['advance_round']}", instance_code)
            
            print(f"🏦 Tạo VietQR với thông tin:")
            print(f"   - Ngân hàng: {bank_id}")
            print(f"   - Số tài khoản: {account_no}")
            print(f"   - Tên người nhận: {account_name}")
            print(f"   - Số tiền: {amount_int:,} VND")
            print(f"   - Mô tả: {description}")
            
            # Bước 9: Tạo VietQR code trong bộ nhớ
            qr_image_buffer = vietqr_service.create_qr_in_memory(
                bank_id=bank_id,
                account_no=account_no,
                amount=amount_int,
                description=description,
                account_name=account_name
            )
            
            if not qr_image_buffer:
                print("❌ Không thể tạo mã VietQR")
                return False
            
            # Bước 10: Upload ảnh lên Lark Approval
            filename = f"{instance_code}_{qr_type}{active_advance_info['advance_round']}_qr.png"
            upload_result = await lark_service.upload_image_to_approval(qr_image_buffer, filename, access_token)
            
            if not upload_result['success']:
                print(f"❌ Upload thất bại: {upload_result['error']}")
                return False
            
            # Bước 11: Đánh dấu đã tạo QR SAU KHI upload thành công
            cache_service.mark_qr_as_generated(instance_code, matching_node_id, qr_type)
            
            # Bước 12: Tạo comment nâng cao với thông tin chi tiết
            comment_result = await lark_service.create_enhanced_comment_with_image(
                instance_code=instance_code,
                file_url=upload_result['file_url'],
                file_code=upload_result['file_code'],
                filename=filename,
                qr_type=f"{qr_type} Lần {active_advance_info['advance_round']}", # Làm rõ hơn trong comment
                amount=amount_int,
                node_name=node_name,
                access_token=access_token
            )
            
            if comment_result['success']:
                print(f"✅ Hoàn thành xử lý phê duyệt {instance_code}")
                print(f"💰 Loại: {qr_type.upper()} LẦN {active_advance_info['advance_round']} | Số tiền: {amount_int:,} VND")
                print(f"🏷️ Node: {node_name}")
                print(f"📋 Trường: {field_used}")
                print(f"💬 ID Comment: {comment_result['comment_id']}")
                return True
            else:
                print(f"❌ Tạo comment thất bại: {comment_result['error']}")
                return False
                
        except Exception as e:
            print(f"❌ Lỗi xử lý phê duyệt: {e}")
            import traceback
            traceback.print_exc()
            return False

qr_processor = QRProcessor()