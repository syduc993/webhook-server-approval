from .field_constants import FFN

APPROVAL_WORKFLOWS = {
    "FCF7110C-FA4B-42AA-93D2-209910F8A0B0": {
        "name": "Quy trình thanh toán tổng hợp mới",
        "nodes": {
            "30e5338b60587c64c7cef5f6a7211ccb": {
                "name": "truong_phong_duyet",
                "type": "dual_detection",
                "advance_field": FFN.ADVANCE_AMOUNT,
                "payment_field": FFN.PAYMENT_AMOUNT,
                "strategy": "detect_both_fields",
                "required_status": "PENDING",
                "description": "Trưởng phòng duyệt - Auto detect advance/payment"
            },
            "f23535375a26847ef71c1cbf0755f246": {
                "name": "thanh_toan_sau_tam_ung",
                "type": "payment_only",
                "advance_field": None,
                "payment_field": FFN.REMAINING_PAYMENT_AMOUNT,
                "strategy": "payment_field_only",
                "required_status": "APPROVED",
                "additional_conditions": [
                    {
                        "node_id": "ef83b231885a1a77658f32808a199764",
                        "required_status": "PENDING",
                        "description": "Node tiếp theo phải PENDING"
                    }
                ],
                "description": "Thanh toán sau tạm ứng - Payment only"
            }
        },
        "field_mappings": {
            "bank_name": FFN.BANK_NAME,
            "account_number": FFN.BANK_ACCOUNT_NUMBER,
            "beneficiary_name": FFN.BENEFICIARY_NAME,
            "accounting_advance_info": FFN.ACCOUNTING_ADVANCE_INFO,
            "accounting_payment_info": FFN.ACCOUNTING_PAYMENT_INFO,
            "expenditure_amount": FFN.EXPENDITURE_AMOUNT
        },
        "qr_trigger_nodes": [
            {
                "node_name_contains": "Thủ quỹ chi tiền tạm ứng",
                "status": "PENDING",
                "yes_no_field_template": "Thanh toán tạm ứng lần {i}: Y/N",
                "amount_field_template": "Số tiền tạm ứng lần {i}:",
                "qr_type": "advance"
            }
        ]
    },
    "3B92E61C-6C60-484C-B8E4-38683B1101EE": {
        "name": "TC4 - Mua sắm Tài sản trong nước",
        "field_mappings": {
            "bank_name": FFN.BANK_NAME,
            "account_number": FFN.BANK_ACCOUNT_NUMBER,
            "beneficiary_name": FFN.BENEFICIARY_NAME,
            "accounting_advance_info": FFN.ACCOUNTING_ADVANCE_INFO,
            "accounting_payment_info": FFN.ACCOUNTING_PAYMENT_INFO,
            "expenditure_amount": FFN.EXPENDITURE_AMOUNT
        },
        "qr_trigger_nodes": [
            {
                "node_name_contains": "Thủ quỹ chi tiền tạm ứng",
                "status": "PENDING",
                "yes_no_field_template": "Thanh toán tạm ứng lần {i}: Y/N",
                "amount_field_template": "Số tiền tạm ứng lần {i}:",
                "qr_type": "advance"
            }
        ]
    }
}


def get_workflow_config(approval_code: str) -> dict:
    """
    Lấy toàn bộ cấu hình cho một quy trình phê duyệt dựa trên approval_code.
    """
    return APPROVAL_WORKFLOWS.get(approval_code)

def get_node_config(approval_code: str, node_id: str) -> dict:
    """
    Lấy cấu hình chi tiết cho một node_id cụ thể trong một quy trình.
    """
    workflow = get_workflow_config(approval_code)
    if workflow and 'nodes' in workflow:
        return workflow['nodes'].get(node_id)
    return None

def get_field_mapping(approval_code: str, field_key: str) -> str:
    """
    Lấy tên trường thực tế từ key logic cho một quy trình.
    Ví dụ: get_field_mapping(code, "bank_name") -> "Ngân hàng"
    """
    workflow = get_workflow_config(approval_code)
    if workflow and 'field_mappings' in workflow:
        return workflow['field_mappings'].get(field_key)
    return None

def get_qr_trigger_config(approval_code: str) -> list:
    """
    Lấy danh sách các cấu hình kích hoạt tạo QR cho một quy trình.
    """
    workflow = get_workflow_config(approval_code)
    if workflow:
        return workflow.get('qr_trigger_nodes', [])
    return []

def print_workflow_summary():
    """
    In ra tóm tắt cấu hình của tất cả các quy trình phê duyệt.
    """
    print("📋 Tóm tắt cấu hình APPROVAL_WORKFLOWS:")
    for code, config in APPROVAL_WORKFLOWS.items():
        print(f"\n Workflow: {config.get('name', 'N/A')} ({code})")
        print(f"   - {len(config.get('nodes', {}))} nodes được cấu hình.")
        print(f"   - {len(config.get('field_mappings', {}))} field mappings.")
        print(f"   - {len(config.get('qr_trigger_nodes', []))} QR triggers.")