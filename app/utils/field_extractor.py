from typing import List, Dict, Any, Optional

class FieldExtractor:
    def extract_field_value(self, form_data: List[Dict], field_name: str, debug: bool = False) -> Optional[Any]:
        """
        Enhanced version: Trích xuất giá trị của một field từ form data với better error handling
        
        Args:
            form_data (list): Form data từ API
            field_name (str): Tên field cần tìm
            debug (bool): In debug info
            
        Returns:
            Giá trị field hoặc None nếu không tìm thấy
        """
        try:
            if debug:
                print(f"🔍 Searching for field: '{field_name}'")
                
            # Search in top-level fields
            for field in form_data:
                if field.get('name') == field_name:
                    value = field.get('value')
                    if debug:
                        print(f"✅ Found '{field_name}' in top-level: {value}")
                    return value
                
                # Search in nested fieldList
                if field.get('type') == 'fieldList' and 'value' in field:
                    field_list_values = field['value']
                    if isinstance(field_list_values, list):
                        for field_group in field_list_values:
                            if isinstance(field_group, list):
                                for sub_field in field_group:
                                    if isinstance(sub_field, dict) and sub_field.get('name') == field_name:
                                        value = sub_field.get('value')
                                        if debug:
                                            print(f"✅ Found '{field_name}' in fieldList: {value}")
                                        return value
            
            if debug:
                print(f"❌ Field '{field_name}' not found")
                print("Available fields:", [f.get('name') for f in form_data if f.get('name')])
                
            return None
            
        except Exception as e:
            print(f"❌ Error extracting field '{field_name}': {e}")
            return None

    def get_all_field_names(self, form_data: List[Dict]) -> List[str]:
        """
        Lấy tất cả field names từ form data
        
        Args:
            form_data: Form data từ API
            
        Returns:
            List[str]: Danh sách tên fields
        """
        field_names = []
        
        try:
            for field in form_data:
                field_name = field.get('name')
                if field_name:
                    field_names.append(field_name)
                
                # Check nested fieldList
                if field.get('type') == 'fieldList' and 'value' in field:
                    field_list_values = field['value']
                    if isinstance(field_list_values, list):
                        for field_group in field_list_values:
                            if isinstance(field_group, list):
                                for sub_field in field_group:
                                    if isinstance(sub_field, dict):
                                        sub_field_name = sub_field.get('name')
                                        if sub_field_name:
                                            field_names.append(sub_field_name)
        except Exception as e:
            print(f"❌ Error getting field names: {e}")
        
        return list(set(field_names))  # Remove duplicates

    def get_amount_fields(self, form_data: List[Dict]) -> Dict[str, Any]:
        """
        Tìm tất cả fields có chứa "tiền" hoặc "amount"
        
        Args:
            form_data: Form data từ API
            
        Returns:
            Dict[str, Any]: Dict với field name là key, value là giá trị
        """
        amount_fields = {}
        
        try:
            for field in form_data:
                field_name = field.get('name', '').lower()
                if 'tiền' in field_name or 'amount' in field_name:
                    amount_fields[field.get('name')] = field.get('value')
        except Exception as e:
            print(f"❌ Error getting amount fields: {e}")
        
        return amount_fields
