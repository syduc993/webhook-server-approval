from .field_constants import FFN

# Cấu hình chi tiết cho từng node trong approval workflow
NODE_CONFIG = {
    # Node trưởng phòng duyệt - Có thể detect cả advance và payment (Không bắt được node submit, node này luôn là node tiếp theo)
    "30e5338b60587c64c7cef5f6a7211ccb": {
        "name": "truong_phong_duyet",
        "type": "dual_detection",                   # Loại node hỗ trợ cả advance và payment
        "advance_field": FFN.ADVANCE_AMOUNT,        # Tên field chứa số tiền tạm ứng
        "payment_field": FFN.PAYMENT_AMOUNT,        # Tên field chứa số tiền thanh toán
        "strategy": "detect_both_fields",           # Strategy tự động detect loại QR dựa trên fields
        "required_status": "PENDING",               # Status cần thiết để trigger QR generation
        "description": "Trưởng phòng duyệt - Auto detect advance/payment"
    },
    
    # Node thanh toán
    "f23535375a26847ef71c1cbf0755f246": {
        "name": "thanh_toan_sau_tam_ung", 
        "type": "payment_only",                          # Loại node chỉ xử lý payment
        "advance_field": None,                           # Không có field advance
        "payment_field": FFN.REMAINING_PAYMENT_AMOUNT,   # Field chứa số tiền cần thanh toán
        "strategy": "payment_field_only",                # Strategy chỉ xử lý payment field
        "required_status": "APPROVED",                   # Node này cần status APPROVED
        
        # Điều kiện bổ sung để trigger QR generation
        "additional_conditions": [
            {
                "node_id": "ef83b231885a1a77658f32808a199764",  # Node tiếp theo
                "required_status": "PENDING",                   # Node tiếp theo phải PENDING
                "description": "Node tiếp theo phải PENDING"    # Mô tả điều kiện
            }
        ],
        "description": "Thanh toán sau tạm ứng - Payment only (trigger on APPROVED + next node PENDING)"
    }
}


def get_node_config(node_id: str) -> dict:
    """
    Lấy configuration chi tiết cho một node_id cụ thể.
    
    Args:
        node_id (str): Node ID cần lấy configuration
        
    Returns:
        dict: Dictionary chứa cấu hình node bao gồm:
            - name: Tên node
            - type: Loại node (dual_detection, payment_only, etc.)
            - advance_field: Tên field chứa số tiền tạm ứng
            - payment_field: Tên field chứa số tiền thanh toán
            - strategy: Chiến lược xử lý (detect_both_fields, payment_field_only, etc.)
            - required_status: Status cần thiết để trigger
            - additional_conditions: Các điều kiện bổ sung (optional)
            - description: Mô tả node
        Trả về None nếu không tìm thấy node_id
    """
    return NODE_CONFIG.get(node_id)


def get_node_strategy(node_id: str) -> str:
    """
    Lấy strategy xử lý của một node cụ thể.
    
    Args:
        node_id (str): Node ID cần lấy strategy
        
    Returns:
        str: Tên strategy của node như:
            - "detect_both_fields": Tự động detect advance/payment
            - "payment_field_only": Chỉ xử lý payment
            - "unknown": Nếu không tìm thấy node hoặc strategy
    """
    config = get_node_config(node_id)
    return config.get("strategy", "unknown") if config else "unknown"


def print_node_config_summary():
    """
    In ra tóm tắt chi tiết của NODE_CONFIG bao gồm additional conditions.
    
    Function này hiển thị thông tin tổng quan về tất cả nodes được cấu hình,
    bao gồm strategy, fields, required status và các điều kiện bổ sung.
    """
    print("📋 Tóm tắt cấu hình NODE_CONFIG:")
    
    # Duyệt qua từng node trong configuration
    for node_id, config in NODE_CONFIG.items():
        required_status = config.get('required_status', 'PENDING')
        additional_conditions = config.get('additional_conditions', [])
        
        # Hiển thị thông tin cơ bản của node
        print(f"   • {node_id[:8]}... - {config['name']} ({config['strategy']})")
        print(f"     Các trường: advance='{config['advance_field']}', payment='{config['payment_field']}'")
        print(f"     Status yêu cầu: {required_status}")
        
        # Hiển thị các điều kiện bổ sung nếu có
        if additional_conditions:
            print(f"     Điều kiện bổ sung:")
            for condition in additional_conditions:
                condition_node_short = condition['node_id'][:8]
                condition_status = condition['required_status']
                print(f"       - {condition_node_short}... phải có status {condition_status}")


def get_configured_node_ids():
    """
    Lấy danh sách tất cả node IDs đã được cấu hình.
    
    Returns:
        List[str]: Danh sách tất cả node IDs có trong NODE_CONFIG
    """
    return list(NODE_CONFIG.keys())


# Backward compatibility - Giữ lại tên cũ để không break existing code
ALLOWED_NODE_IDS = get_configured_node_ids()
