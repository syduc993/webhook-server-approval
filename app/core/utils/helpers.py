from typing import Optional, Dict, Any
from datetime import datetime
import pandas as pd
import json
import os

def extract_instance_code(event_data: Dict) -> Optional[str]:
    """Trích xuất instance_code từ event"""
    try:
        event_body = event_data.get("event", {})
        if "instance_code" in event_body:
            return event_body["instance_code"]
            
        if "object" in event_body and "instance_code" in event_body["object"]:
            return event_body["object"]["instance_code"]
            
        return None
    except:
        return None

def get_event_type(event_data: Dict) -> str:
    """Lấy event type"""
    try:
        if "header" in event_data:
            return event_data["header"].get("event_type", "unknown")
        
        if "event" in event_data and "type" in event_data["event"]:
            return event_data["event"]["type"]
            
        return event_data.get("type", "unknown")
    except:
        return "unknown"

async def save_event_to_csv(event_data: Dict, events_file: str = "lark_events.csv"):
    """Lưu event vào CSV"""
    try:
        row_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": get_event_type(event_data),
            "instance_code": extract_instance_code(event_data),
            "raw_event": json.dumps(event_data, ensure_ascii=False)
        }
        
        df = pd.DataFrame([row_data])
        
        if os.path.exists(events_file):
            df.to_csv(events_file, mode='a', header=False, index=False, encoding='utf-8')
        else:
            df.to_csv(events_file, mode='w', header=True, index=False, encoding='utf-8')
            
        print(f"✅ Event saved to {events_file}")
        
    except Exception as e:
        print(f"❌ Error saving event: {e}")

def format_currency(amount: float) -> str:
    """Format số tiền theo định dạng VND"""
    return f"{amount:,} VND"

def get_short_node_id(node_id: str, length: int = 8) -> str:
    """Get short version of node ID for display"""
    return node_id[:length] + "..." if len(node_id) > length else node_id
