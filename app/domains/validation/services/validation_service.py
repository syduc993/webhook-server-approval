"""
Validation Service - Dịch vụ domain cho các quy tắc validation
"""
from typing import Dict, List, Any
from app.domains.validation.models import ValidationResult, ValidationType
from app.core.utils.field_extractor import FieldExtractor
# [THAY ĐỔI] Import các hàm helper mới
from app.core.config.node_config import get_field_mapping

class ValidationService:
    """
    Dịch vụ validation cho hệ thống phê duyệt.
    
    [NÂNG CẤP] Class này giờ đây đọc cấu hình field_mappings động dựa trên
    approval_code để hỗ trợ các quy tắc validation cho nhiều quy trình.
    """
    
    def __init__(self):
        """Khởi tạo ValidationService với field extractor và mapping rules."""
        self.field_extractor = FieldExtractor()
        
        self.validation_rules = {
            ValidationType.ADVANCE_AMOUNT_MISMATCH: self.validate_advance_amount_mismatch,
            ValidationType.PAYMENT_AMOUNT_MISMATCH: self.validate_payment_amount_mismatch,
            # Các quy tắc khác có thể được thêm vào đây
        }
    
    # [THAY ĐỔI] Signature nhận thêm approval_code
    def validate_advance_amount_mismatch(self, approval_code: str, form_data: List[Dict], **kwargs) -> List[ValidationResult]:
        """
        So sánh số tiền tạm ứng giữa yêu cầu của người dùng và số tiền chi của kế toán.
        Sử dụng tên trường động từ cấu hình.
        """
        try:
            # [LOGIC MỚI] Lấy tên trường từ cấu hình động
            accounting_advance_field = get_field_mapping(approval_code, "accounting_advance_info")
            expenditure_field = get_field_mapping(approval_code, "expenditure_amount")

            if not accounting_advance_field or not expenditure_field:
                return [ValidationResult.create_skipped(
                    ValidationType.ADVANCE_AMOUNT_MISMATCH,
                    "ℹ️ Bỏ qua: Cấu hình 'accounting_advance_info' hoặc 'expenditure_amount' bị thiếu."
                )]

            accountant_expenditures = self.field_extractor.extract_all_values_from_fieldlist(
                form_data, accounting_advance_field, expenditure_field
            )
            
            results = []
            found_data = False

            for i in range(1, 5): # Giữ nguyên logic kiểm tra 4 lần
                user_advance_field = f"Số tiền tạm ứng lần {i}:" # Giả định tên trường này là cố định
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
                        results.append(ValidationResult.create_invalid(ValidationType.ADVANCE_AMOUNT_MISMATCH, message))
                except (ValueError, TypeError):
                    message = f"❌ Lỗi định dạng số Tạm ứng Lần {i}."
                    results.append(ValidationResult.create_invalid(ValidationType.ADVANCE_AMOUNT_MISMATCH, message))

            if not results and found_data:
                results.append(ValidationResult.create_valid(
                    ValidationType.ADVANCE_AMOUNT_MISMATCH, "✅ Tất cả các lần tạm ứng đã khớp."
                ))
            
            if not found_data:
                results.append(ValidationResult.create_skipped(
                    ValidationType.ADVANCE_AMOUNT_MISMATCH, "ℹ️ Bỏ qua: Không tìm thấy dữ liệu tạm ứng để so sánh."
                ))
            
            return results
                
        except Exception as e:
            return [ValidationResult.create_error(
                ValidationType.ADVANCE_AMOUNT_MISMATCH, f"❌ Lỗi hệ thống khi validation tiền tạm ứng: {e}"
            )]

    # [THAY ĐỔI] Signature nhận thêm approval_code
    def validate_payment_amount_mismatch(self, approval_code: str, form_data: List[Dict], **kwargs) -> ValidationResult:
        """
        Validation tính nhất quán số tiền thanh toán, sử dụng tên trường động.
        """
        try:
            # [LOGIC MỚI] Lấy tên trường từ cấu hình động
            accounting_payment_field = get_field_mapping(approval_code, "accounting_payment_info")
            expenditure_field = get_field_mapping(approval_code, "expenditure_amount")
            # [LOGIC MỚI] Lấy các trường thanh toán khác từ cấu hình (ví dụ)
            # Giả sử chúng ta thêm các key này vào field_mappings
            remaining_payment_field = get_field_mapping(approval_code, "remaining_payment_amount") or "Số tiền còn phải thanh toán"
            payment_field = get_field_mapping(approval_code, "payment_amount") or "Số tiền thanh toán"

            if not accounting_payment_field or not expenditure_field:
                 return ValidationResult.create_skipped(
                    ValidationType.PAYMENT_AMOUNT_MISMATCH,
                    "ℹ️ Bỏ qua: Cấu hình 'accounting_payment_info' hoặc 'expenditure_amount' bị thiếu."
                )

            payment_info_amount = self.field_extractor.extract_field_from_fieldlist(
                form_data,  accounting_payment_field, expenditure_field
            )
            amount_due = self.field_extractor.extract_field_value(form_data,  remaining_payment_field)
            amount_paid = self.field_extractor.extract_field_value(form_data, payment_field)
            
            compare_amount = amount_due if amount_due is not None else amount_paid
            compare_field_name = remaining_payment_field if amount_due is not None else payment_field

            if payment_info_amount is None or compare_amount is None:
                return ValidationResult.create_skipped(
                    ValidationType.PAYMENT_AMOUNT_MISMATCH,
                    "ℹ️ Bỏ qua: Không tìm thấy đủ các trường về số tiền thanh toán để so sánh."
                )

            payment_info_float = float(payment_info_amount)
            compare_amount_float = float(compare_amount)

            if abs(payment_info_float - compare_amount_float) < 0.01:
                return ValidationResult.create_valid(
                    ValidationType.PAYMENT_AMOUNT_MISMATCH, f"✅ Số tiền thanh toán nhất quán: {payment_info_float:,.0f} VND"
                )
            else:
                message = (f"❌ Lỗi thanh toán: 'Kế toán' ({payment_info_float:,.0f}) ≠ "
                           f"'{compare_field_name}' ({compare_amount_float:,.0f}). "
                           f"Chênh lệch: {abs(payment_info_float - compare_amount_float):,.0f} VND")
                details = {"payment_info_amount": payment_info_float, "compare_amount": compare_amount_float}
                return ValidationResult.create_invalid(ValidationType.PAYMENT_AMOUNT_MISMATCH, message, details)
        except (ValueError, TypeError) as e:
            return ValidationResult.create_error(
                ValidationType.PAYMENT_AMOUNT_MISMATCH, f"❌ Lỗi định dạng số tiền thanh toán: {e}"
            )
        except Exception as e:
            return ValidationResult.create_error(
                ValidationType.PAYMENT_AMOUNT_MISMATCH, f"❌ Lỗi không xác định khi validation tiền thanh toán: {e}"
            )
    
    # [THAY ĐỔI] Signature của hàm chính đã thay đổi
    def run_all_validations(self, approval_code: str, form_data: List[Dict], task_list: List[Dict], 
                           node_id: str) -> List[ValidationResult]:
        """
        Chạy tất cả các validation rules đã được đăng ký cho quy trình được chỉ định.
        """
        print(f"🚀 Bắt đầu chạy tất cả validation cho quy trình '{approval_code}'...")
        results = []
        
        for validation_type, validation_func in self.validation_rules.items():
            print(f"▶️ Đang chạy: {validation_type.value}...")
            
            # [THAY ĐỔI] Truyền approval_code vào mỗi hàm validation
            result_or_list = validation_func(
                approval_code=approval_code,
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