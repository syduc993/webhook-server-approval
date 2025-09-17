import json
from app.core.config.settings import settings
from app.core.config.node_config import NODE_CONFIG
from app.core.config.field_constants import FFN
from app.core.infrastructure.lark_service import lark_service
from app.core.infrastructure.cache_service import cache_service
from app.core.utils.field_extractor import FieldExtractor
from app.domains.qr_generation.services.vietqr_service import vietqr_service
from app.domains.qr_generation.services.amount_detector import AmountDetector
from app.domains.qr_generation.models import QRType, BankInfo

class QRProcessor:
    """
    Bộ xử lý QR chính - Quản lý logic nghiệp vụ tạo và xử lý mã QR cho hệ thống phê duyệt.
    
    Class này xử lý toàn bộ quy trình từ việc kiểm tra node phê duyệt, trích xuất dữ liệu,
    validate thông tin, tạo mã VietQR và upload lên hệ thống Lark.
    
    Attributes:
        field_extractor (FieldExtractor): Bộ trích xuất trường dữ liệu từ form
        amount_detector (AmountDetector): Bộ phát hiện và xác định số tiền
    """

    def __init__(self):
        """Khởi tạo QRProcessor với các service cần thiết."""
        self.field_extractor = FieldExtractor()
        self.amount_detector = AmountDetector()

    def check_pending_allowed_node_in_task_list(self, api_response: dict, node_config: dict = None) -> dict:
        """
        Kiểm tra node có trạng thái phù hợp và đáp ứng các điều kiện bổ sung.
        
        Phương thức này sẽ duyệt qua danh sách task và tìm node đầu tiên
        thỏa mãn cả trạng thái chính và các điều kiện phụ.
        
        Args:
            api_response (dict): Phản hồi API từ Lark chứa thông tin instance
            node_config (dict, optional): Cấu hình node. Defaults to NODE_CONFIG.
            
        Returns:
            dict: Kết quả kiểm tra bao gồm:
                - found (bool): Có tìm thấy node phù hợp không
                - node_id (str): ID của node tìm thấy
                - node_config (dict): Cấu hình của node
                - strategy (str): Chiến lược xử lý
                - matched_status (str): Trạng thái hiện tại
                - required_status (str): Trạng thái yêu cầu
                - all_tasks (list): Danh sách tất cả task
                - node_status_map (dict): Map trạng thái của các node
        """
        if node_config is None:
            node_config = NODE_CONFIG
            
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
        
        Args:
            amount_value: Giá trị số tiền cần validate (có thể là string, int, float)
            
        Returns:
            dict: Kết quả validation bao gồm:
                - valid (bool): Giá trị có hợp lệ không
                - amount (int): Giá trị số tiền đã chuyển đổi
                - error (str): Thông báo lỗi nếu có
        """
        try:
            if amount_value is None:
                return {'valid': False, 'amount': None, 'error': 'Số tiền không được để trống'}
                
            # Chuyển đổi sang float trước, sau đó sang int
            amount_float = float(amount_value)
            amount_int = int(amount_float)
            
            if amount_int <= 0:
                return {'valid': False, 'amount': amount_int, 'error': 'Số tiền phải lớn hơn 0'}
                
            return {'valid': True, 'amount': amount_int, 'error': None}
            
        except (ValueError, TypeError) as e:
            return {'valid': False, 'amount': None, 'error': f'Định dạng số tiền không hợp lệ: {str(e)}'}

    async def process_approval_with_qr_comment(self, instance_code: str, access_token: str) -> bool:
        """
        Xử lý phê duyệt với tạo QR code và comment.
        
        Đây là phương thức chính xử lý toàn bộ quy trình:
        1. Lấy thông tin instance từ Lark
        2. Kiểm tra node phù hợp với cấu hình
        3. Trích xuất và validate dữ liệu form
        4. Kiểm tra duplicate để tránh tạo QR trùng lặp
        5. Tạo mã VietQR
        6. Upload và tạo comment
        
        Args:
            instance_code (str): Mã instance phê duyệt
            access_token (str): Token để truy cập Lark API
            
        Returns:
            bool: True nếu xử lý thành công, False nếu có lỗi
        """
        try:
            # Bước 1: Lấy thông tin chi tiết của instance
            api_response = await lark_service.get_approval_instance(instance_code, access_token)
            if not api_response:
                print(f"❌ Không thể lấy thông tin instance {instance_code}")
                return False
            
            # Bước 2: Kiểm tra node có trạng thái phù hợp
            node_check_result = self.check_pending_allowed_node_in_task_list(api_response)
            
            if not node_check_result['found']:
                print(f"⏭️ Bỏ qua tạo QR - không tìm thấy node phù hợp với cấu hình")
                return True  # Trả về True vì không phải lỗi, chỉ là bỏ qua
            
            # Lấy thông tin node phù hợp
            matching_node_id = node_check_result['node_id']
            node_config = node_check_result['node_config']
            node_strategy = node_check_result['strategy']
            matched_status = node_check_result.get('matched_status', 'UNKNOWN')
            required_status = node_check_result.get('required_status', 'PENDING')
            
            print(f"✅ Đang xử lý node: {node_config['name']} (chiến lược: {node_strategy})")
            print(f"   Trạng thái: {matched_status} (yêu cầu: {required_status})")
            
            # Bước 3: Trích xuất dữ liệu form
            if 'data' not in api_response or 'form' not in api_response['data']:
                print("❌ Không tìm thấy dữ liệu form")
                return False
                
            form_str = api_response['data']['form']
            form_data = json.loads(form_str)
            
            # Bước 4: Phát hiện số tiền và loại QR theo chiến lược node
            amount_result = self.amount_detector.get_amount_and_type_for_node(matching_node_id, form_data)
            
            if not amount_result['success']:
                print(f"❌ Không thể xác định số tiền/loại QR: {amount_result.get('reason', 'Lỗi không xác định')}")
                if 'error' in amount_result:
                    print(f"    Chi tiết lỗi: {amount_result['error']}")
                return False
            
            qr_type = amount_result['qr_type']
            amount_value = amount_result['amount']
            field_used = amount_result['field_used']
            
            # Bước 5: Kiểm tra duplicate TRƯỚC KHI tạo QR
            if cache_service.is_qr_recently_generated(
                instance_code, matching_node_id, qr_type, 
                settings.QR_CACHE_DURATION_MINUTES
            ):
                print(f"⚠️ PHÁT HIỆN TRÙNG LẶP: QR {qr_type.upper()} cho node {node_config['name']} đã được tạo gần đây")
                print(f"   → BỎ QUA tạo QR để tránh trùng lặp")
                return True  # Trả về thành công vì không phải lỗi, chỉ là bỏ qua duplicate
            
            print(f"💰 Chi tiết tạo QR:")
            print(f"   - Loại: {qr_type}")
            print(f"   - Số tiền: {amount_value:,} VND")
            print(f"   - Trường sử dụng: {field_used}")
            print(f"   - Chiến lược node: {node_strategy}")
            print(f"   - Trạng thái kích hoạt: {matched_status}")
            
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

            # Kiểm tra đầy đủ thông tin ngân hàng
            if not all([bank_id, account_no, account_name]):
                missing_fields = []
                if not bank_id: missing_fields.append(FFN.BANK_NAME)
                if not account_no: missing_fields.append(FFN.BANK_ACCOUNT_NUMBER)
                if not account_name: missing_fields.append(FFN.BENEFICIARY_NAME)

                print(f"❌ Thiếu thông tin ngân hàng: {', '.join(missing_fields)}")
                return False
            
            # Bước 8: Tạo mô tả QR theo loại
            description = vietqr_service.generate_qr_description(qr_type, instance_code)
            
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
            filename = f"{instance_code}_{qr_type}_qr.png"
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
                qr_type=qr_type,
                amount=amount_int,
                node_name=node_config['name'],
                access_token=access_token
            )
            
            if comment_result['success']:
                print(f"✅ Hoàn thành xử lý phê duyệt {instance_code}")
                print(f"💰 Loại: {qr_type.upper()} | Số tiền: {amount_int:,} VND")
                print(f"🏷️ Node: {node_config['name']} | Trạng thái: {matched_status}")
                print(f"📋 Trường: {field_used} | Chiến lược: {node_strategy}")
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