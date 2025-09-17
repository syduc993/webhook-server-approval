"""
Validation Service - Dịch vụ domain cho các quy tắc validation
"""
from typing import Dict, List, Any, Optional
from app.domains.validation.models import ValidationResult, ValidationType, ValidationStatus
from app.core.utils.field_extractor import FieldExtractor
from app.core.config.field_constants import FFN

class ValidationService:
    """
    Dịch vụ validation cho hệ thống phê duyệt.
    
    Class này cung cấp các quy tắc validation khác nhau để kiểm tra
    tính nhất quán và hợp lệ của dữ liệu trong quy trình phê duyệt:
    
    - ADVANCE_AMOUNT_MISMATCH: So sánh số tiền tạm ứng
    - PAYMENT_AMOUNT_MISMATCH: So sánh số tiền thanh toán
    - TOTAL_AMOUNT_MISMATCH: Kiểm tra tổng số tiền thanh toán
    - WORKFLOW_STATUS: Kiểm tra trạng thái node
    - FIELD_CONSISTENCY: Kiểm tra logic giữa các trường
    
    Mỗi validation sẽ trả về ValidationResult với một trong các trạng thái:
    - VALID: Validation pass
    - INVALID: Validation fail  
    - SKIPPED: Bỏ qua do thiếu dữ liệu
    - ERROR: Có lỗi trong quá trình validation
    
    Attributes:
        field_extractor (FieldExtractor): Công cụ trích xuất dữ liệu từ form
        validation_rules (Dict): Map từ validation type đến method tương ứng
    """
    
    def __init__(self):
        """Khởi tạo ValidationService với field extractor và mapping rules."""
        self.field_extractor = FieldExtractor()
        
        # Mapping đã được cập nhật với các enum và tên hàm mới, cụ thể hơn
        self.validation_rules = {
            ValidationType.ADVANCE_AMOUNT_MISMATCH: self.validate_advance_amount_mismatch,
            ValidationType.PAYMENT_AMOUNT_MISMATCH: self.validate_payment_amount_mismatch,
            ValidationType.TOTAL_AMOUNT_MISMATCH: self.validate_total_amount_mismatch,
            ValidationType.WORKFLOW_STATUS: self.validate_workflow_status,
            ValidationType.FIELD_CONSISTENCY: self.validate_field_consistency,
        }
    
    def validate_advance_amount_mismatch(self, form_data: List[Dict], **kwargs) -> ValidationResult:
        """
        Validation số tiền tạm ứng giữa fieldList và top-level field.
        
        So sánh giá trị "Số tiền chi" trong fieldList "Kế toán - Thông tin tạm ứng" 
        với "Số tiền tạm ứng" ở top-level để đảm bảo tính nhất quán.
        """
        try:
            advance_amount_from_fieldlist = self.field_extractor.extract_field_from_fieldlist(
                form_data, FFN.ACCOUNTING_ADVANCE_INFO, FFN.EXPENDITURE_AMOUNT 
            )
            advance_amount_toplevel = self.field_extractor.extract_field_value(
                form_data, FFN.ADVANCE_AMOUNT
            )
            
            if advance_amount_from_fieldlist is None or advance_amount_toplevel is None:
                return ValidationResult.create_skipped(
                    ValidationType.ADVANCE_AMOUNT_MISMATCH,
                    "ℹ️ Bỏ qua: Không tìm thấy đủ các trường về số tiền tạm ứng để so sánh."
                )
            
            fieldlist_amount = float(advance_amount_from_fieldlist)
            toplevel_amount = float(advance_amount_toplevel)
            
            if abs(fieldlist_amount - toplevel_amount) < 0.01:
                return ValidationResult.create_valid(
                    ValidationType.ADVANCE_AMOUNT_MISMATCH,
                    f"✅ Số tiền tạm ứng nhất quán: {fieldlist_amount:,} VND"
                )
            else:
                return ValidationResult.create_invalid(
                    ValidationType.ADVANCE_AMOUNT_MISMATCH,
                    f"❌ Lỗi tạm ứng: '{FFN.EXPENDITURE_AMOUNT}' ({fieldlist_amount:,}) ≠ '{FFN.ADVANCE_AMOUNT}' ({toplevel_amount:,}). Chênh lệch: {abs(fieldlist_amount - toplevel_amount):,} VND",
                    {"fieldlist_amount": fieldlist_amount, "toplevel_amount": toplevel_amount}
                )
        except (ValueError, TypeError) as e:
            return ValidationResult.create_error(
                ValidationType.ADVANCE_AMOUNT_MISMATCH,
                f"❌ Lỗi định dạng số tiền tạm ứng: {e}",
            )
        except Exception as e:
            return ValidationResult.create_error(
                ValidationType.ADVANCE_AMOUNT_MISMATCH,
                f"❌ Lỗi không xác định khi validation tiền tạm ứng: {e}",
            )

    def validate_payment_amount_mismatch(self, form_data: List[Dict], **kwargs) -> ValidationResult:
        """
        Validation tính nhất quán số tiền thanh toán.
        
        So sánh "Kế toán - Thông tin thanh toán" với "Số tiền còn phải thanh toán" 
        hoặc "Số tiền thanh toán".
        """
        try:
            payment_info_amount = self.field_extractor.extract_field_from_fieldlist(
                form_data,  FFN.ACCOUNTING_PAYMENT_INFO, FFN.EXPENDITURE_AMOUNT
            )
            amount_due = self.field_extractor.extract_field_value(
                form_data,  FFN.REMAINING_PAYMENT_AMOUNT
            )
            amount_paid = self.field_extractor.extract_field_value(
                form_data, FFN.PAYMENT_AMOUNT
            )
            
            compare_amount = amount_due if amount_due is not None else amount_paid
            compare_field_name = FFN.REMAINING_PAYMENT_AMOUNT if amount_due is not None else FFN.PAYMENT_AMOUNT

            if payment_info_amount is None or compare_amount is None:
                return ValidationResult.create_skipped(
                    ValidationType.PAYMENT_AMOUNT_MISMATCH,
                    "ℹ️ Bỏ qua: Không tìm thấy đủ các trường về số tiền thanh toán để so sánh."
                )

            payment_info_float = float(payment_info_amount)
            compare_amount_float = float(compare_amount)

            if abs(payment_info_float - compare_amount_float) < 0.01:
                return ValidationResult.create_valid(
                    ValidationType.PAYMENT_AMOUNT_MISMATCH,
                    f"✅ Số tiền thanh toán nhất quán: {payment_info_float:,} VND"
                )
            else:
                return ValidationResult.create_invalid(
                    ValidationType.PAYMENT_AMOUNT_MISMATCH,
                    f"❌ Lỗi thanh toán: 'Kế toán' ({payment_info_float:,}) ≠ '{compare_field_name}' ({compare_amount_float:,}). Chênh lệch: {abs(payment_info_float - compare_amount_float):,} VND",
                    {"payment_info_amount": payment_info_float, "compare_amount": compare_amount_float}
                )
        except (ValueError, TypeError) as e:
            return ValidationResult.create_error(
                ValidationType.PAYMENT_AMOUNT_MISMATCH,
                f"❌ Lỗi định dạng số tiền thanh toán: {e}",
            )
        except Exception as e:
            return ValidationResult.create_error(
                ValidationType.PAYMENT_AMOUNT_MISMATCH,
                f"❌ Lỗi không xác định khi validation tiền thanh toán: {e}",
            )

    def validate_total_amount_mismatch(self, form_data: List[Dict], **kwargs) -> ValidationResult:
        """
        Validation tổng số tiền thanh toán.
        
        Kiểm tra công thức: Total = Tạm ứng + Còn phải thanh toán (hoặc các biến thể khác).
        """
        try:
            advance_amount = self.field_extractor.extract_field_value(form_data, FFN.ADVANCE_AMOUNT)
            amount_due = self.field_extractor.extract_field_value(form_data, FFN.REMAINING_PAYMENT_AMOUNT)
            total_payment_actual = self.field_extractor.extract_field_value(form_data, FFN.TOTAL_PAYMENT_AMOUNT)

            if advance_amount is None or total_payment_actual is None or amount_due is None:
                return ValidationResult.create_skipped(
                    ValidationType.TOTAL_AMOUNT_MISMATCH,
                    f"ℹ️ Bỏ qua: Không tìm thấy đủ các trường '{FFN.ADVANCE_AMOUNT}', '{FFN.REMAINING_PAYMENT_AMOUNT}', '{FFN.TOTAL_PAYMENT_AMOUNT}' để tính tổng."
                )

            advance_float = float(advance_amount)
            amount_due_float = float(amount_due)
            total_actual_float = float(total_payment_actual)
            
            total_expected = advance_float + amount_due_float

            if abs(total_expected - total_actual_float) < 0.01:
                return ValidationResult.create_valid(
                    ValidationType.TOTAL_AMOUNT_MISMATCH,
                    f"✅ Tổng số tiền hợp lệ: {total_actual_float:,} VND"
                )
            else:
                case_description = f"{FFN.ADVANCE_AMOUNT} ({advance_float:,}) + {FFN.REMAINING_PAYMENT_AMOUNT} ({amount_due_float:,})"
                return ValidationResult.create_invalid(
                    ValidationType.TOTAL_AMOUNT_MISMATCH,
                    f"❌ Lỗi tổng tiền: ({total_actual_float:,}) ≠ ({total_expected:,} từ {case_description}). Chênh lệch: {abs(total_expected - total_actual_float):,} VND",
                    {"total_expected": total_expected, "total_actual": total_actual_float}
                )
        except (ValueError, TypeError) as e:
            return ValidationResult.create_error(
                ValidationType.TOTAL_AMOUNT_MISMATCH,
                f"❌ Lỗi định dạng số khi tính tổng tiền: {e}",
            )
        except Exception as e:
            return ValidationResult.create_error(
                ValidationType.TOTAL_AMOUNT_MISMATCH,
                f"❌ Lỗi không xác định khi validation tổng tiền: {e}",
            )
    
    def validate_workflow_status(self, task_list: List[Dict], node_id: str, **kwargs) -> ValidationResult:
        """
        Validation trạng thái workflow để phát hiện node bị thu hồi.
        """
        try:
            target_node = next((task for task in task_list if task.get('node_id') == node_id), None)
            
            if not target_node:
                return ValidationResult.create_skipped(
                    ValidationType.WORKFLOW_STATUS,
                    f"ℹ️ Bỏ qua: Node {node_id[:8]}... không tìm thấy trong danh sách task"
                )
            
            current_status = target_node.get('status', 'UNKNOWN')
            problematic_statuses = ['REJECTED', 'CANCELED', 'WITHDRAWN']
            if current_status in problematic_statuses:
                return ValidationResult.create_invalid(
                    ValidationType.WORKFLOW_STATUS,
                    f"⚠️ CẢNH BÁO: Node {node_id[:8]}... có trạng thái {current_status} - có thể đã bị thu hồi hoặc từ chối"
                )
            
            return ValidationResult.create_valid(
                ValidationType.WORKFLOW_STATUS,
                f"✅ Node {node_id[:8]}... có trạng thái bình thường: {current_status}"
            )
        except Exception as e:
            return ValidationResult.create_error(
                ValidationType.WORKFLOW_STATUS,
                f"❌ Lỗi kiểm tra trạng thái workflow: {str(e)}"
            )
    
    def validate_field_consistency(self, form_data: List[Dict], **kwargs) -> ValidationResult:
        """
        Placeholder cho các logic validation về tính nhất quán của các trường khác.
        """
        return ValidationResult.create_valid(
            ValidationType.FIELD_CONSISTENCY,
            "✅ Kiểm tra tính nhất quán các trường thành công (placeholder)"
        )
    
    def run_validation(self, validation_type: ValidationType, **kwargs) -> ValidationResult:
        """
        Chạy một quy tắc validation cụ thể.
        """
        if validation_type in self.validation_rules:
            return self.validation_rules[validation_type](**kwargs)
        else:
            return ValidationResult.create_error(
                validation_type,
                f"❌ Loại validation không xác định: {validation_type}"
            )
    
    def run_all_validations(self, form_data: List[Dict], task_list: List[Dict], 
                           node_id: str) -> List[ValidationResult]:
        """
        Chạy tất cả các validation rules đã được đăng ký.
        """
        print(f"🚀 Bắt đầu chạy tất cả validation cho node {node_id[:8]}...")
        results = []
        
        # Vòng lặp này giúp tự động chạy tất cả các rule đã định nghĩa trong __init__
        # Giúp code dễ mở rộng và bảo trì hơn
        for validation_type in self.validation_rules.keys():
            print(f"▶️ Đang chạy: {validation_type.value}...")
            result = self.run_validation(
                validation_type, 
                form_data=form_data,
                task_list=task_list,
                node_id=node_id
            )
            results.append(result)

        # Tổng kết kết quả
        invalid_count = sum(1 for r in results if r.status == ValidationStatus.INVALID)
        print(f"📈 Hoàn thành validation: Tìm thấy {invalid_count} vấn đề.")
        
        return results

validation_service = ValidationService()