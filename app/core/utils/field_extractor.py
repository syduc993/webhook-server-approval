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

    def extract_field_from_fieldlist(self, form_data: List[Dict], fieldlist_name: str, 
                                target_field_name: str, debug: bool = False) -> Optional[Any]:
        """
        Trích xuất giá trị đầu tiên của một field từ bên trong một fieldList cụ thể.
        
        Hàm này chỉ trả về giá trị đầu tiên tìm thấy. Để lấy tất cả giá trị,
        sử dụng `extract_all_values_from_fieldlist`.
        
        Args:
            form_data: Form data từ API
            fieldlist_name: Tên fieldList container (vd: "Kế toán - Thông tin tạm ứng")  
            target_field_name: Tên field cần tìm (vd: "Số tiền chi")
            debug: In debug info
            
        Returns:
            Giá trị field hoặc None nếu không tìm thấy
        """
        try:
            if debug:
                print(f"🔍 Searching for first '{target_field_name}' in fieldList '{fieldlist_name}'")
                
            if not fieldlist_name or not target_field_name:
                if debug: print("❌ Invalid parameters: fieldlist_name and target_field_name required")
                return None
                
            for field in form_data:
                if field.get('name') == fieldlist_name and field.get('type') == 'fieldList':
                    field_list_values = field.get('value', [])
                    if debug: print(f"📋 Found fieldList '{fieldlist_name}' with {len(field_list_values)} items")
                    
                    for field_group in field_list_values:
                        if isinstance(field_group, list):
                            for sub_field in field_group:
                                if isinstance(sub_field, dict) and sub_field.get('name') == target_field_name:
                                    value = sub_field.get('value')
                                    if debug: print(f"✅ Found first '{target_field_name}' = {value}")
                                    return value
                    
                    if debug: print(f"❌ Field '{target_field_name}' not found in fieldList")
                    return None
            
            if debug:
                print(f"❌ fieldList '{fieldlist_name}' not found")
                available = [f.get('name') for f in form_data if f.get('type') == 'fieldList']
                print(f"Available fieldLists: {available}")
            return None
            
        except Exception as e:
            print(f"❌ Error extracting field from fieldList: {e}")
            return None
            
    def extract_all_values_from_fieldlist(self, form_data: List[Dict], fieldlist_name: str, 
                                          target_field_name: str, debug: bool = False) -> List[Any]:
        """
        ✅ MỚI: Trích xuất TẤT CẢ các giá trị của một field từ TẤT CẢ các dòng trong một fieldList.
        
        Hữu ích khi cần tính tổng các giá trị trong một danh sách, ví dụ như tổng "Số tiền chi"
        từ nhiều lần tạm ứng của kế toán.
        
        Args:
            form_data: Form data từ API.
            fieldlist_name: Tên của fieldList container (ví dụ: "Kế toán - Thông tin tạm ứng").
            target_field_name: Tên của field cần trích xuất giá trị (ví dụ: "Số tiền chi").
            debug: Bật/tắt in thông tin gỡ lỗi.
            
        Returns:
            List[Any]: Một danh sách chứa tất cả các giá trị tìm thấy. Trả về list rỗng nếu không tìm thấy gì.
        """
        extracted_values = []
        try:
            if debug:
                print(f"🔍 Searching for ALL '{target_field_name}' values in fieldList '{fieldlist_name}'")

            for field in form_data:
                if field.get('name') == fieldlist_name and field.get('type') == 'fieldList':
                    field_list_values = field.get('value', [])
                    if debug:
                        print(f"📋 Found fieldList '{fieldlist_name}' with {len(field_list_values)} rows.")
                    
                    # Duyệt qua từng dòng (field_group) trong fieldList
                    for i, field_group in enumerate(field_list_values):
                        if isinstance(field_group, list):
                            # Duyệt qua từng trường (sub_field) trong dòng
                            for sub_field in field_group:
                                if isinstance(sub_field, dict) and sub_field.get('name') == target_field_name:
                                    value = sub_field.get('value')
                                    extracted_values.append(value)
                                    if debug:
                                        print(f"   ✅ Row {i+1}: Found value '{value}'")
                    
                    # Sau khi duyệt xong, không cần tìm nữa
                    if debug:
                        print(f"📊 Total values found: {len(extracted_values)}")
                    return extracted_values
            
            if debug:
                print(f"❌ FieldList '{fieldlist_name}' not found in form data.")
            return extracted_values

        except Exception as e:
            print(f"❌ Error extracting all values from fieldList: {e}")
            return extracted_values

    def extract_fields_by_prefix(self, form_data: List[Dict], prefix: str, debug: bool = False) -> Dict[str, Any]:
        """
        ✅ MỚI: Trích xuất tất cả các trường có tên bắt đầu bằng một tiền tố (prefix) cho trước.
        
        Hữu ích để tìm các trường động như "Số tiền tạm ứng lần 1:", "Số tiền tạm ứng lần 2:",...
        
        Args:
            form_data: Form data từ API.
            prefix: Tiền tố dùng để tìm kiếm (ví dụ: "Số tiền tạm ứng lần").
            debug: Bật/tắt in thông tin gỡ lỗi.
            
        Returns:
            Dict[str, Any]: Một dictionary với key là tên đầy đủ của trường và value là giá trị của nó.
        """
        extracted_fields = {}
        try:
            if debug:
                print(f"🔍 Searching for all fields with prefix: '{prefix}'")
            
            # Duyệt qua tất cả các trường ở mọi cấp độ
            for field in form_data:
                field_name = field.get('name')
                
                # Kiểm tra trường ở cấp cao nhất
                if field_name and field_name.startswith(prefix):
                    value = field.get('value')
                    extracted_fields[field_name] = value
                    if debug:
                        print(f"   ✅ Found top-level field: '{field_name}' = {value}")
                
                # Kiểm tra các trường lồng trong fieldList
                if field.get('type') == 'fieldList' and 'value' in field:
                    field_list_values = field.get('value', [])
                    if isinstance(field_list_values, list):
                        for field_group in field_list_values:
                            if isinstance(field_group, list):
                                for sub_field in field_group:
                                    sub_field_name = sub_field.get('name')
                                    if sub_field_name and sub_field_name.startswith(prefix):
                                        value = sub_field.get('value')
                                        extracted_fields[sub_field_name] = value
                                        if debug:
                                            print(f"   ✅ Found nested field: '{sub_field_name}' = {value}")
            
            if debug:
                print(f"📊 Total fields found with prefix: {len(extracted_fields)}")
            return extracted_fields

        except Exception as e:
            print(f"❌ Error extracting fields by prefix '{prefix}': {e}")
            return extracted_fields