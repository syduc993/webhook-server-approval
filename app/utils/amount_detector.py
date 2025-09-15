from typing import Dict, List, Optional
from app.config.node_config import get_node_config
from app.utils.field_extractor import FieldExtractor

class AmountDetector:
    def __init__(self):
        self.field_extractor = FieldExtractor()
    
    def detect_available_amount_fields(self, form_data: List[Dict], node_config: Dict = None) -> Dict:
        """
        Scan form data để tìm amount fields theo config của node
        
        Args:
            form_data (list): Form data từ API response
            node_config (dict): Node configuration (optional)
            
        Returns:
            dict: Detection results với các fields và values
        """
        try:
            # Sử dụng config từ node thay vì hardcode
            if node_config:
                advance_field = node_config.get('advance_field')
                payment_field = node_config.get('payment_field')
            else:
                # Fallback cho backward compatibility
                advance_field = "Số tiền tạm ứng"
                payment_field = "Số tiền thanh toán"
            
            # Extract cả 2 fields (chỉ khi field name không phải None)
            advance_value = self.field_extractor.extract_field_value(form_data, advance_field) if advance_field else None
            payment_value = self.field_extractor.extract_field_value(form_data, payment_field) if payment_field else None
            
            # Debug: tìm tất cả fields có chứa "tiền" hoặc "amount" 
            all_amount_fields = self.field_extractor.get_amount_fields(form_data)
            
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
            
            print(f"💰 Field detection results:")
            if advance_field:
                print(f"   - {advance_field}: {'✅ ' + str(advance_value) if advance_value else '❌ Not found'}")
            else:
                print(f"   - Advance field: ❌ Not configured")
                
            if payment_field:
                print(f"   - {payment_field}: {'✅ ' + str(payment_value) if payment_value else '❌ Not found'}")
            else:
                print(f"   - Payment field: ❌ Not configured")
                
            print(f"   - All amount fields: {list(all_amount_fields.keys())}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error detecting amount fields: {e}")
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
        Quyết định QR type dựa trên fields có giá trị
        
        Args:
            field_detection_result (dict): Kết quả từ detect_available_amount_fields()
            
        Returns:
            dict: QR type decision result
        """
        try:
            advance_found = field_detection_result.get('advance_field_found', False)
            payment_found = field_detection_result.get('payment_field_found', False)
            advance_amount = field_detection_result.get('advance_amount')
            payment_amount = field_detection_result.get('payment_amount')

            fields_used = field_detection_result.get('fields_used', {})
            advance_field_name = fields_used.get('advance_field', 'Số tiền tạm ứng')
            payment_field_name = fields_used.get('payment_field', 'Số tiền thanh toán')

            print(f"🎯 Determining QR type: advance={advance_found}, payment={payment_found}")
            
            # Logic priority: advance trước, sau đó payment
            if advance_found and advance_amount:
                try:
                    amount_value = float(advance_amount)
                    if amount_value > 0:
                        return {
                            'qr_type': 'advance',
                            'amount': amount_value,
                            'field_used': advance_field_name,
                            'reason': 'Found valid advance amount'
                        }
                except (ValueError, TypeError):
                    print(f"⚠️ Invalid advance amount: {advance_amount}")
            
            if payment_found and payment_amount:
                try:
                    amount_value = float(payment_amount)
                    if amount_value > 0:
                        return {
                            'qr_type': 'payment', 
                            'amount': amount_value,
                            'field_used': payment_field_name,
                            'reason': 'Found valid payment amount'
                        }
                except (ValueError, TypeError):
                    print(f"⚠️ Invalid payment amount: {payment_amount}")
            
            # Không tìm thấy field hợp lệ
            return {
                'qr_type': 'none',
                'amount': None,
                'field_used': None,
                'reason': f'No valid amount found (advance_found={advance_found}, payment_found={payment_found})'
            }
            
        except Exception as e:
            print(f"❌ Error determining QR type: {e}")
            return {
                'qr_type': 'none',
                'amount': None,
                'field_used': None,
                'reason': f'Error: {str(e)}'
            }
    
    def get_amount_and_type_for_node(self, node_id: str, form_data: List[Dict]) -> Dict:
        """
        Lấy amount và QR type cho một node cụ thể dựa trên strategy của node đó
        
        Args:
            node_id (str): Node ID
            form_data (list): Form data từ API
            
        Returns:
            dict: Processing result với success, qr_type, amount, etc.
        """
        try:
            node_config = get_node_config(node_id)
            if not node_config:
                return {
                    'success': False,
                    'qr_type': 'none',
                    'error': f'Node {node_id} not found in configuration'
                }
            
            strategy = node_config['strategy']
            node_name = node_config['name']
            
            print(f"🔍 Processing node: {node_name} (strategy: {strategy})")
            
            # Detect available fields
            field_detection = self.detect_available_amount_fields(form_data, node_config)
            
            if strategy == "detect_both_fields":
                # Dual detection: có thể là advance hoặc payment
                qr_decision = self.determine_qr_type_by_fields(field_detection)
                
                return {
                    'success': qr_decision['qr_type'] != 'none',
                    'qr_type': qr_decision['qr_type'],
                    'amount': qr_decision['amount'],
                    'field_used': qr_decision['field_used'],
                    'node_strategy': strategy,
                    'reason': f"Dual detection result: {qr_decision['reason']}",
                    'field_detection': field_detection
                }
                
            elif strategy == "payment_field_only":
                # Payment only: chỉ check payment field
                payment_amount = field_detection.get('payment_amount')
                payment_found = field_detection.get('payment_field_found', False)
                payment_field_name = node_config.get('payment_field')

                if payment_found and payment_amount:
                    try:
                        amount_value = float(payment_amount)
                        if amount_value > 0:
                            return {
                                'success': True,
                                'qr_type': 'payment',
                                'amount': amount_value,
                                'field_used': payment_field_name,
                                'node_strategy': strategy,
                                'reason': 'Payment-only strategy: found valid payment amount',
                                'field_detection': field_detection
                            }
                    except (ValueError, TypeError):
                        pass
                
                return {
                    'success': False,
                    'qr_type': 'none',
                    'amount': None,
                    'field_used': None,
                    'node_strategy': strategy,
                    'reason': f'Payment-only strategy: no valid payment amount (found={payment_found}, value={payment_amount})',
                    'field_detection': field_detection
                }
            
            else:
                return {
                    'success': False,
                    'qr_type': 'none',
                    'error': f'Unknown strategy: {strategy}'
                }
                
        except Exception as e:
            print(f"❌ Error processing node {node_id}: {e}")
            return {
                'success': False,
                'qr_type': 'none',
                'error': str(e)
            }
