"""Node configuration for different approval workflows"""

NODE_CONFIG = {
    "30e5338b60587c64c7cef5f6a7211ccb": {
        "name": "truong_phong_duyet",
        "type": "dual_detection",
        "advance_field": "Số tiền tạm ứng",
        "payment_field": "Số tiền thanh toán",
        "strategy": "detect_both_fields",
        "required_status": "PENDING",
        "description": "Trưởng phòng duyệt - Auto detect advance/payment"
    },
    "f23535375a26847ef71c1cbf0755f246": {
        "name": "thanh_toan_sau_tam_ung", 
        "type": "payment_only",
        "advance_field": None,
        "payment_field": "Số tiền còn phải thanh toán",
        "strategy": "payment_field_only",
        "required_status": "APPROVED",
        "additional_conditions": [
            {
                "node_id": "ef83b231885a1a77658f32808a199764",
                "required_status": "PENDING",
                "description": "Node tiếp theo phải PENDING"
            }
        ],
        "description": "Thanh toán sau tạm ứng - Payment only (trigger on APPROVED + next node PENDING)"
    }
}

def get_node_config(node_id: str) -> dict:
    """
    Lấy configuration cho một node_id cụ thể
    
    Args:
        node_id (str): Node ID cần lấy config
        
    Returns:
        dict: Node config hoặc None nếu không tìm thấy
    """
    return NODE_CONFIG.get(node_id)

def get_node_strategy(node_id: str) -> str:
    """
    Lấy strategy của một node
    
    Args:
        node_id (str): Node ID
        
    Returns:
        str: Strategy name hoặc "unknown" nếu không tìm thấy
    """
    config = get_node_config(node_id)
    return config.get("strategy", "unknown") if config else "unknown"

def print_node_config_summary():
    """Print summary của NODE_CONFIG với additional conditions"""
    print("📋 NODE_CONFIG Summary:")
    for node_id, config in NODE_CONFIG.items():
        required_status = config.get('required_status', 'PENDING')
        additional_conditions = config.get('additional_conditions', [])
        
        print(f"   • {node_id[:8]}... - {config['name']} ({config['strategy']})")
        print(f"     Fields: advance='{config['advance_field']}', payment='{config['payment_field']}'")
        print(f"     Required Status: {required_status}")
        
        if additional_conditions:
            print(f"     Additional Conditions:")
            for condition in additional_conditions:
                print(f"       - {condition['node_id'][:8]}... must be {condition['required_status']}")

def get_configured_node_ids():
    """Trả về list tất cả node IDs được cấu hình"""
    return list(NODE_CONFIG.keys())

# Backward compatibility
ALLOWED_NODE_IDS = get_configured_node_ids()
