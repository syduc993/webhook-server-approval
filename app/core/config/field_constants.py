# app/core/config/field_constants.py

class FormFieldNames:
    """
    Single Source of Truth for all Lark Approval form field names.
    Tập trung tất cả tên trường của form phê duyệt Lark tại một nơi duy nhất.
    """
    
    # === Trường Tiền Tệ Cấp Cao (Top-level Amount Fields) ===
    ADVANCE_AMOUNT = "Số tiền tạm ứng"
    PAYMENT_AMOUNT = "Số tiền thanh toán"
    REMAINING_PAYMENT_AMOUNT = "Số tiền còn phải thanh toán"
    TOTAL_PAYMENT_AMOUNT = "Total số tiền thanh toán"

    # === Trường Trong FieldList Kế Toán (Accounting FieldList Fields) ===
    ACCOUNTING_ADVANCE_INFO = "Kế toán - Thông tin tạm ứng"
    ACCOUNTING_PAYMENT_INFO = "Kế toán - Thông tin thanh toán"
    EXPENDITURE_AMOUNT = "Số tiền chi" # Dùng chung cho cả tạm ứng và thanh toán

    # === Trường Thông Tin Ngân Hàng (Bank Information Fields) ===
    BANK_NAME = "Ngân hàng"
    BANK_ACCOUNT_NUMBER = "Số tài khoản ngân hàng"
    BENEFICIARY_NAME = "Tên người thụ hưởng"

# Tạo một instance để dễ dàng import và sử dụng
# from app.core.config.field_constants import FFN
FFN = FormFieldNames()