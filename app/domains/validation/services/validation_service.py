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
    
    - ADVANCE_AMOUNT_MISMATCH: So sánh tổng số tiền tạm ứng
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
        
        self.validation_rules = {
            ValidationType.ADVANCE_AMOUNT_MISMATCH: self.validate_advance_amount_mismatch,
            ValidationType.PAYMENT_AMOUNT_MISMATCH: self.validate_payment_amount_mismatch,
            #ValidationType.TOTAL_AMOUNT_MISMATCH: self.validate_total_amount_mismatch,
            ValidationType.WORKFLOW_STATUS: self.validate_workflow_status,
            ValidationType.FIELD_CONSISTENCY: self.validate_field_consistency,
        }
    
    # Thay vì trả về ValidationResult, giờ đây hàm sẽ trả về List[ValidationResult]
    def validate_advance_amount_mismatch(self, form_data: List[Dict], **kwargs) -> List[ValidationResult]:
        """
        Trả về một danh sách các ValidationResult, mỗi result cho một lỗi.
        """
        try:
            accountant_expenditures = self.field_extractor.extract_all_values_from_fieldlist(
                form_data, FFN.ACCOUNTING_ADVANCE_INFO, FFN.EXPENDITURE_AMOUNT
            )
            
            results = []
            found_data = False

            for i in range(1, 5): # Chỉ kiểm tra 4 lần
                user_advance_field = f"Số tiền tạm ứng lần {i}:"
                user_advance_value = self.field_extractor.extract_field_value(form_data, user_advance_field)
                
                if user_advance_value is not None:
                    found_data = True

                if (i - 1) >= len(accountant_expenditures) or user_advance_value is None:
                    continue
                
                accountant_expenditure_value = accountant_expenditures[i-1]
                
                try:
                    user_amount = float(user_advance_value)
                    accountant_amount = float(accountant_expenditure_value)
                    
                    if abs(user_amount - accountant_amount) >= 0.01:
                        message = (f"❌ Lỗi Tạm ứng Lần {i}: Yêu cầu ({user_amount:,.0f}) ≠ Kế toán chi ({accountant_amount:,.0f}). "
                                f"Lệch: {abs(user_amount - accountant_amount):,.0f} VND")
                        # Tạo một result riêng cho lỗi này
                        results.append(ValidationResult.create_invalid(ValidationType.ADVANCE_AMOUNT_MISMATCH, message))
                except (ValueError, TypeError):
                    message = f"❌ Lỗi định dạng số Tạm ứng Lần {i}."
                    results.append(ValidationResult.create_invalid(ValidationType.ADVANCE_AMOUNT_MISMATCH, message))

            # Nếu không có lỗi nào được tìm thấy và có dữ liệu để kiểm tra
            if not results and found_data:
                results.append(ValidationResult.create_valid(
                    ValidationType.ADVANCE_AMOUNT_MISMATCH,
                    "✅ Tất cả các lần tạm ứng đã khớp."
                ))
            
            # Nếu không có dữ liệu để kiểm tra
            if not found_data:
                results.append(ValidationResult.create_skipped(
                    ValidationType.ADVANCE_AMOUNT_MISMATCH,
                    "ℹ️ Bỏ qua: Không tìm thấy dữ liệu tạm ứng để so sánh."
                ))
            
            return results
                
        except Exception as e:
            return [ValidationResult.create_error(
                ValidationType.ADVANCE_AMOUNT_MISMATCH,
                f"❌ Lỗi hệ thống khi validation tiền tạm ứng: {e}",
            )]

    def validate_payment_amount_mismatch(self, form_data: List[Dict], **kwargs) -> ValidationResult:
        """
        Validation tính nhất quán số tiền thanh toán (giữ nguyên logic cũ).
        
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
                    f"✅ Số tiền thanh toán nhất quán: {payment_info_float:,.0f} VND"
                )
            else:
                message = (f"❌ Lỗi thanh toán: 'Kế toán' ({payment_info_float:,.0f}) ≠ "
                           f"'{compare_field_name}' ({compare_amount_float:,.0f}). "
                           f"Chênh lệch: {abs(payment_info_float - compare_amount_float):,.0f} VND")
                details = {"payment_info_amount": payment_info_float, "compare_amount": compare_amount_float}
                return ValidationResult.create_invalid(ValidationType.PAYMENT_AMOUNT_MISMATCH, message, details)
        except (ValueError, TypeError) as e:
            return ValidationResult.create_error(
                ValidationType.PAYMENT_AMOUNT_MISMATCH, f"❌ Lỗi định dạng số tiền thanh toán: {e}",
            )
        except Exception as e:
            return ValidationResult.create_error(
                ValidationType.PAYMENT_AMOUNT_MISMATCH, f"❌ Lỗi không xác định khi validation tiền thanh toán: {e}",
            )

    def validate_total_amount_mismatch(self, form_data: List[Dict], **kwargs) -> ValidationResult:
        """
        Validation tổng số tiền thanh toán dựa trên các khoản chi đã được kế toán xác nhận.
        
        Công thức: Total = (Tổng các khoản chi trong FieldList "Kế toán - Thông tin tạm ứng") + (Số tiền còn phải thanh toán).
        """
        try:
            # Lấy tổng các khoản chi tạm ứng THỰC TẾ từ kế toán
            accountant_expenditures = self.field_extractor.extract_all_values_from_fieldlist(
                form_data, FFN.ACCOUNTING_ADVANCE_INFO, FFN.EXPENDITURE_AMOUNT
            )
            total_accountant_advance = sum(float(v) for v in accountant_expenditures if v is not None and str(v).strip() != '')

            # Lấy các trường còn lại
            amount_due = self.field_extractor.extract_field_value(form_data, FFN.REMAINING_PAYMENT_AMOUNT)
            total_payment_actual = self.field_extractor.extract_field_value(form_data, FFN.TOTAL_PAYMENT_AMOUNT)

            if total_accountant_advance == 0 and amount_due is None:
                return ValidationResult.create_skipped(
                    ValidationType.TOTAL_AMOUNT_MISMATCH,
                    f"ℹ️ Bỏ qua: Kế toán chưa điền thông tin chi hoặc số tiền còn lại."
                )

            if total_payment_actual is None:
                return ValidationResult.create_skipped(
                    ValidationType.TOTAL_AMOUNT_MISMATCH,
                    f"ℹ️ Bỏ qua: Không tìm thấy trường '{FFN.TOTAL_PAYMENT_AMOUNT}' để tính tổng."
                )

            amount_due_float = float(amount_due) if amount_due is not None else 0.0
            total_actual_float = float(total_payment_actual)
            
            total_expected = total_accountant_advance + amount_due_float

            if abs(total_expected - total_actual_float) < 0.01:
                return ValidationResult.create_valid(
                    ValidationType.TOTAL_AMOUNT_MISMATCH,
                    f"✅ Tổng số tiền hợp lệ: {total_actual_float:,.0f} VND"
                )
            else:
                case_description = f"Tổng Kế toán chi ({total_accountant_advance:,.0f}) + Còn Lại ({amount_due_float:,.0f})"
                message = (f"❌ Lỗi tổng tiền: Thực tế ({total_actual_float:,.0f}) ≠ "
                        f"Dự kiến ({total_expected:,.0f} từ {case_description}). "
                        f"Chênh lệch: {abs(total_expected - total_actual_float):,.0f} VND")
                details = {
                    "total_expected": total_expected, 
                    "total_actual": total_actual_float,
                    "total_accountant_advance": total_accountant_advance,
                    "remaining_payment": amount_due_float
                }
                return ValidationResult.create_invalid(ValidationType.TOTAL_AMOUNT_MISMATCH, message, details)
        except (ValueError, TypeError) as e:
            return ValidationResult.create_error(
                ValidationType.TOTAL_AMOUNT_MISMATCH, f"❌ Lỗi định dạng số khi tính tổng tiền: {e}",
            )
        except Exception as e:
            return ValidationResult.create_error(
                ValidationType.TOTAL_AMOUNT_MISMATCH, f"❌ Lỗi không xác định khi validation tổng tiền: {e}",
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
        
        for validation_type in self.validation_rules.keys():
            print(f"▶️ Đang chạy: {validation_type.value}...")
            # Sử dụng extend để xử lý việc một rule có thể trả về nhiều result
            validation_func = self.validation_rules[validation_type]
            
            # Cần kiểm tra xem hàm có trả về list hay không
            # Vì các hàm khác vẫn trả về 1 result đơn lẻ
            result_or_list = validation_func(
                form_data=form_data,
                task_list=task_list,
                node_id=node_id
            )

            if isinstance(result_or_list, list):
                results.extend(result_or_list)
            else:
                results.append(result_or_list)

        invalid_count = sum(1 for r in results if not r.is_valid)
        print(f"📈 Hoàn thành validation: Tìm thấy {invalid_count} vấn đề.")
        
        return results

validation_service = ValidationService()