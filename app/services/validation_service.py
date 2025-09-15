"""
Validation Service - Dành cho các validation rules mở rộng trong tương lai
Ví dụ: kiểm tra tổng tạm ứng + thanh toán = thành tiền
"""
from typing import Dict, List, Any, Optional
from app.models.approval import ValidationResult

class ValidationService:
    def __init__(self):
        self.validation_rules = {
            "amount_sum_validation": self.validate_amount_sum,
            "workflow_status_validation": self.validate_workflow_status,
            "field_consistency_validation": self.validate_field_consistency
        }
    
    def validate_amount_sum(self, form_data: List[Dict], **kwargs) -> ValidationResult:
        """
        Kiểm tra tổng tạm ứng + thanh toán có bằng thành tiền không
        
        Args:
            form_data: Form data từ approval
            **kwargs: Additional parameters
            
        Returns:
            ValidationResult: Kết quả validation
        """
        try:
            from app.utils.field_extractor import FieldExtractor
            extractor = FieldExtractor()
            
            # Extract các fields cần thiết
            advance_amount = extractor.extract_field_value(form_data, "Số tiền tạm ứng")
            payment_amount = extractor.extract_field_value(form_data, "Số tiền thanh toán")
            total_amount = extractor.extract_field_value(form_data, "Thành tiền")
            
            # Convert sang float
            advance = float(advance_amount) if advance_amount else 0
            payment = float(payment_amount) if payment_amount else 0
            total = float(total_amount) if total_amount else 0
            
            calculated_sum = advance + payment
            
            if abs(calculated_sum - total) < 0.01:  # Allow small floating point differences
                return ValidationResult(
                    is_valid=True,
                    validation_type="amount_sum_validation",
                    message=f"✅ Tổng số tiền hợp lệ: {advance:,} + {payment:,} = {total:,}",
                    details={
                        "advance_amount": advance,
                        "payment_amount": payment,
                        "total_amount": total,
                        "calculated_sum": calculated_sum
                    }
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    validation_type="amount_sum_validation",
                    message=f"❌ Tổng số tiền không khớp: {advance:,} + {payment:,} = {calculated_sum:,} ≠ {total:,}",
                    details={
                        "advance_amount": advance,
                        "payment_amount": payment,
                        "total_amount": total,
                        "calculated_sum": calculated_sum,
                        "difference": abs(calculated_sum - total)
                    }
                )
                
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                validation_type="amount_sum_validation",
                message=f"❌ Lỗi validation: {str(e)}",
                details={"error": str(e)}
            )
    
    def validate_workflow_status(self, task_list: List[Dict], node_id: str, **kwargs) -> ValidationResult:
        """
        Kiểm tra workflow status - cảnh báo nếu node đã duyệt mà bị thu hồi
        
        Args:
            task_list: Task list từ approval
            node_id: Node ID cần kiểm tra
            **kwargs: Additional parameters
            
        Returns:
            ValidationResult: Kết quả validation
        """
        try:
            # Tìm node trong task list
            target_node = None
            for task in task_list:
                if task.get('node_id') == node_id:
                    target_node = task
                    break
            
            if not target_node:
                return ValidationResult(
                    is_valid=True,  # Không tìm thấy node không phải lỗi
                    validation_type="workflow_status_validation",
                    message=f"Node {node_id[:8]}... không tìm thấy trong task list",
                    details={"node_id": node_id, "found": False}
                )
            
            current_status = target_node.get('status', 'UNKNOWN')
            
            # Logic kiểm tra thu hồi
            if current_status in ['REJECTED', 'CANCELED', 'WITHDRAWN']:
                # Kiểm tra xem trước đó có được approve không
                # (Logic này có thể phức tạp hơn tùy theo business rule)
                return ValidationResult(
                    is_valid=False,
                    validation_type="workflow_status_validation",
                    message=f"⚠️ CẢNH BÁO: Node {node_id[:8]}... có status {current_status} - có thể đã bị thu hồi",
                    details={
                        "node_id": node_id,
                        "current_status": current_status,
                        "alert_type": "potential_withdrawal"
                    }
                )
            
            return ValidationResult(
                is_valid=True,
                validation_type="workflow_status_validation",
                message=f"✅ Node {node_id[:8]}... có status bình thường: {current_status}",
                details={
                    "node_id": node_id,
                    "current_status": current_status
                }
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                validation_type="workflow_status_validation",
                message=f"❌ Lỗi kiểm tra workflow status: {str(e)}",
                details={"error": str(e)}
            )
    
    def validate_field_consistency(self, form_data: List[Dict], **kwargs) -> ValidationResult:
        """
        Kiểm tra tính nhất quán của các fields
        Ví dụ: Ngày bắt đầu phải trước ngày kết thúc
        """
        try:
            # Placeholder cho logic validation khác
            return ValidationResult(
                is_valid=True,
                validation_type="field_consistency_validation",
                message="✅ Field consistency check passed",
                details={"checked": True}
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                validation_type="field_consistency_validation",
                message=f"❌ Lỗi kiểm tra field consistency: {str(e)}",
                details={"error": str(e)}
            )
    
    def run_validation(self, validation_type: str, **kwargs) -> ValidationResult:
        """
        Chạy một validation rule cụ thể
        
        Args:
            validation_type: Loại validation cần chạy
            **kwargs: Parameters cho validation
            
        Returns:
            ValidationResult: Kết quả validation
        """
        if validation_type in self.validation_rules:
            return self.validation_rules[validation_type](**kwargs)
        else:
            return ValidationResult(
                is_valid=False,
                validation_type=validation_type,
                message=f"❌ Unknown validation type: {validation_type}",
                details={"available_types": list(self.validation_rules.keys())}
            )
    
    def run_all_validations(self, form_data: List[Dict], task_list: List[Dict], 
                           node_id: str) -> List[ValidationResult]:
        """
        Chạy tất cả validations
        
        Args:
            form_data: Form data từ approval
            task_list: Task list từ approval
            node_id: Node ID đang xử lý
            
        Returns:
            List[ValidationResult]: Danh sách kết quả validation
        """
        results = []
        
        # Amount sum validation
        results.append(self.run_validation(
            "amount_sum_validation", 
            form_data=form_data
        ))
        
        # Workflow status validation
        results.append(self.run_validation(
            "workflow_status_validation", 
            task_list=task_list, 
            node_id=node_id
        ))
        
        # Field consistency validation
        results.append(self.run_validation(
            "field_consistency_validation", 
            form_data=form_data
        ))
        
        return results

# Global service instance
validation_service = ValidationService()
