from typing import Dict, List, Optional
from app.core.config.node_config import get_node_config
from app.core.config.field_constants import FFN
from app.core.utils.field_extractor import FieldExtractor
from app.domains.qr_generation.models import AmountDetectionResult, QRTypeResult, QRType


class AmountDetector:
    """
    Bộ phát hiện và xác định số tiền cho việc tạo mã QR.

    Class này chịu trách nhiệm phân tích dữ liệu form để:
    - Tìm kiếm các trường chứa thông tin số tiền
    - Xác định loại QR (tạm ứng hoặc thanh toán) dựa trên node strategy
    - Validate và trả về số tiền phù hợp cho từng node

    Hỗ trợ nhiều chiến lược xử lý khác nhau:
    - detect_both_fields: Phát hiện cả tạm ứng và thanh toán
    - payment_field_only: Chỉ xử lý trường thanh toán

    Attributes:
        field_extractor (FieldExtractor): Công cụ trích xuất dữ liệu từ form
    """

    def __init__(self):
        """Khởi tạo AmountDetector với FieldExtractor."""
        self.field_extractor = FieldExtractor()

    def detect_available_amount_fields(self, form_data: List[Dict], node_config: Dict = None) -> Dict:
        """
        Quét dữ liệu form để tìm các trường số tiền theo cấu hình node.
        
        Phương thức này sẽ tìm kiếm các trường tạm ứng và thanh toán dựa trên
        cấu hình của node. Nếu không có cấu hình, sẽ sử dụng tên trường mặc định.
        
        Args:
            form_data (List[Dict]): Dữ liệu form từ API response của Lark
            node_config (Dict, optional): Cấu hình node chứa tên các trường cần tìm
            
        Returns:
            Dict: Kết quả phát hiện bao gồm:
                - advance_amount: Giá trị số tiền tạm ứng
                - payment_amount: Giá trị số tiền thanh toán  
                - advance_field_found: Có tìm thấy trường tạm ứng không
                - payment_field_found: Có tìm thấy trường thanh toán không
                - all_amount_fields: Tất cả trường chứa từ khóa tiền
                - fields_used: Tên các trường đã sử dụng để tìm kiếm
        """
        try:
            # Lấy tên trường từ cấu hình node hoặc sử dụng giá trị mặc định
            if node_config:
                advance_field = node_config.get('advance_field')
                payment_field = node_config.get('payment_field')
            else:
                # Giá trị mặc định để tương thích ngược
                advance_field = FFN.ADVANCE_AMOUNT
                payment_field = FFN.PAYMENT_AMOUNT
            
            # Trích xuất giá trị từ cả 2 trường (chỉ khi tên trường không phải None)
            advance_value = None
            payment_value = None
            
            if advance_field:
                advance_value = self.field_extractor.extract_field_value(form_data, advance_field)
            
            if payment_field:
                payment_value = self.field_extractor.extract_field_value(form_data, payment_field)
            
            # Debug: Tìm tất cả trường có chứa từ khóa "tiền" hoặc "amount"
            all_amount_fields = self.field_extractor.get_amount_fields(form_data)
            
            # Tạo kết quả chi tiết
            result = {
                'advance_amount': advance_value,
                'payment_amount': payment_value,
                'advance_field_found': advance_value is not None,
                'payment_field_found': payment_value is not None,
                'all_amount_fields': all_amount_fields,
                'fields_used': {
                    'advance_field': advance_field,
                    'payment_field': payment_field
                }
            }
            
            # Hiển thị kết quả phát hiện trường
            print(f"💰 Kết quả phát hiện trường số tiền:")
            if advance_field:
                status = f"✅ {advance_value}" if advance_value else "❌ Không tìm thấy"
                print(f"   - {advance_field}: {status}")
            else:
                print(f"   - Trường tạm ứng: ❌ Chưa được cấu hình")
                
            if payment_field:
                status = f"✅ {payment_value}" if payment_value else "❌ Không tìm thấy"
                print(f"   - {payment_field}: {status}")
            else:
                print(f"   - Trường thanh toán: ❌ Chưa được cấu hình")
                
            print(f"   - Tất cả trường số tiền: {list(all_amount_fields.keys())}")
            
            return result
            
        except Exception as e:
            print(f"❌ Lỗi khi phát hiện trường số tiền: {e}")
            return {
                'advance_amount': None,
                'payment_amount': None,
                'advance_field_found': False,
                'payment_field_found': False,
                'all_amount_fields': {},
                'fields_used': {'advance_field': None, 'payment_field': None},
                'error': str(e)
            }

    def determine_qr_type_by_fields(self, field_detection_result: Dict) -> Dict:
        """
        Xác định loại QR dựa trên các trường có giá trị hợp lệ.
        
        Logic ưu tiên: Tạm ứng được ưu tiên trước, sau đó đến thanh toán.
        Chỉ chọn trường có giá trị số hợp lệ và lớn hơn 0.
        
        Args:
            field_detection_result (Dict): Kết quả từ detect_available_amount_fields()
            
        Returns:
            Dict: Kết quả quyết định loại QR bao gồm:
                - qr_type: Loại QR ('advance', 'payment', hoặc 'none')
                - amount: Số tiền đã chọn
                - field_used: Tên trường đã sử dụng
                - reason: Lý do quyết định
        """
        try:
            # Trích xuất thông tin từ kết quả phát hiện trường
            advance_found = field_detection_result.get('advance_field_found', False)
            payment_found = field_detection_result.get('payment_field_found', False)
            advance_amount = field_detection_result.get('advance_amount')
            payment_amount = field_detection_result.get('payment_amount')

            # Lấy tên trường để hiển thị trong kết quả
            fields_used = field_detection_result.get('fields_used', {})
            advance_field_name = fields_used.get('advance_field', FFN.ADVANCE_AMOUNT)
            payment_field_name = fields_used.get('payment_field', FFN.PAYMENT_AMOUNT)

            print(f"🎯 Đang xác định loại QR: tạm_ứng={advance_found}, thanh_toán={payment_found}")
            
            # Logic ưu tiên: Kiểm tra tạm ứng trước
            if advance_found and advance_amount:
                try:
                    amount_value = float(advance_amount)
                    if amount_value > 0:
                        print(f"✅ Chọn tạm ứng: {amount_value:,} VND")
                        return {
                            'qr_type': 'advance',
                            'amount': amount_value,
                            'field_used': advance_field_name,
                            'reason': 'Tìm thấy số tiền tạm ứng hợp lệ'
                        }
                except (ValueError, TypeError):
                    print(f"⚠️ Số tiền tạm ứng không hợp lệ: {advance_amount}")
            
            # Nếu không có tạm ứng, kiểm tra thanh toán
            if payment_found and payment_amount:
                try:
                    amount_value = float(payment_amount)
                    if amount_value > 0:
                        print(f"✅ Chọn thanh toán: {amount_value:,} VND")
                        return {
                            'qr_type': 'payment', 
                            'amount': amount_value,
                            'field_used': payment_field_name,
                            'reason': 'Tìm thấy số tiền thanh toán hợp lệ'
                        }
                except (ValueError, TypeError):
                    print(f"⚠️ Số tiền thanh toán không hợp lệ: {payment_amount}")
            
            # Không tìm thấy trường hợp lệ nào
            print(f"❌ Không tìm thấy số tiền hợp lệ")
            return {
                'qr_type': 'none',
                'amount': None,
                'field_used': None,
                'reason': f'Không tìm thấy số tiền hợp lệ (tạm_ứng={advance_found}, thanh_toán={payment_found})'
            }
            
        except Exception as e:
            print(f"❌ Lỗi khi xác định loại QR: {e}")
            return {
                'qr_type': 'none',
                'amount': None,
                'field_used': None,
                'reason': f'Lỗi: {str(e)}'
            }

    def get_amount_and_type_for_node(self, node_id: str, form_data: List[Dict]) -> Dict:
        """
        Lấy số tiền và loại QR cho một node cụ thể dựa trên chiến lược của node.
        
        Đây là phương thức chính để xử lý node, sẽ:
        1. Lấy cấu hình node từ node_id
        2. Áp dụng chiến lược phù hợp (detect_both_fields hoặc payment_field_only)
        3. Phân tích form data và trả về kết quả
        
        Args:
            node_id (str): ID của node cần xử lý
            form_data (List[Dict]): Dữ liệu form từ Lark API
            
        Returns:
            Dict: Kết quả xử lý bao gồm:
                - success (bool): Xử lý thành công hay không
                - qr_type (str): Loại QR đã xác định
                - amount (float): Số tiền cho QR
                - field_used (str): Trường đã sử dụng
                - node_strategy (str): Chiến lược của node
                - reason (str): Lý do kết quả
                - field_detection (Dict): Chi tiết phát hiện trường
        """
        try:
            # Lấy cấu hình node từ hệ thống
            node_config = get_node_config(node_id)
            if not node_config:
                print(f"❌ Không tìm thấy cấu hình cho node {node_id}")
                return {
                    'success': False,
                    'qr_type': 'none',
                    'error': f'Không tìm thấy node {node_id} trong cấu hình'
                }
            
            # Trích xuất thông tin node
            strategy = node_config['strategy']
            node_name = node_config['name']
            
            print(f"🔍 Đang xử lý node: {node_name} (chiến lược: {strategy})")
            
            # Phát hiện các trường có sẵn trong form
            field_detection = self.detect_available_amount_fields(form_data, node_config)
            
            # Áp dụng chiến lược xử lý theo cấu hình
            if strategy == "detect_both_fields":
                # Chiến lược phát hiện kép: có thể là tạm ứng hoặc thanh toán
                print(f"📋 Áp dụng chiến lược phát hiện kép")
                qr_decision = self.determine_qr_type_by_fields(field_detection)
                
                return {
                    'success': qr_decision['qr_type'] != 'none',
                    'qr_type': qr_decision['qr_type'],
                    'amount': qr_decision['amount'],
                    'field_used': qr_decision['field_used'],
                    'node_strategy': strategy,
                    'reason': f"Kết quả phát hiện kép: {qr_decision['reason']}",
                    'field_detection': field_detection
                }
                
            elif strategy == "payment_field_only":
                # Chiến lược chỉ thanh toán: chỉ kiểm tra trường thanh toán
                print(f"💳 Áp dụng chiến lược chỉ thanh toán")
                payment_amount = field_detection.get('payment_amount')
                payment_found = field_detection.get('payment_field_found', False)
                payment_field_name = node_config.get('payment_field')

                if payment_found and payment_amount:
                    try:
                        amount_value = float(payment_amount)
                        if amount_value > 0:
                            print(f"✅ Tìm thấy số tiền thanh toán hợp lệ: {amount_value:,} VND")
                            return {
                                'success': True,
                                'qr_type': 'payment',
                                'amount': amount_value,
                                'field_used': payment_field_name,
                                'node_strategy': strategy,
                                'reason': 'Chiến lược chỉ thanh toán: tìm thấy số tiền hợp lệ',
                                'field_detection': field_detection
                            }
                    except (ValueError, TypeError):
                        print(f"⚠️ Số tiền thanh toán không hợp lệ: {payment_amount}")
                
                print(f"❌ Không tìm thấy số tiền thanh toán hợp lệ")
                return {
                    'success': False,
                    'qr_type': 'none',
                    'amount': None,
                    'field_used': None,
                    'node_strategy': strategy,
                    'reason': f'Chiến lược chỉ thanh toán: không có số tiền hợp lệ (tìm_thấy={payment_found}, giá_trị={payment_amount})',
                    'field_detection': field_detection
                }
            
            else:
                print(f"❌ Chiến lược không xác định: {strategy}")
                return {
                    'success': False,
                    'qr_type': 'none',
                    'error': f'Chiến lược không xác định: {strategy}'
                }
                
        except Exception as e:
            print(f"❌ Lỗi khi xử lý node {node_id}: {e}")
            return {
                'success': False,
                'qr_type': 'none',
                'error': str(e)
            }