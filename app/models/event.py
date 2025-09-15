from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class EventHeader(BaseModel):
    event_id: Optional[str] = None
    event_type: Optional[str] = None
    create_time: Optional[str] = None
    token: Optional[str] = None
    tenant_key: Optional[str] = None
    app_id: Optional[str] = None

class EventBody(BaseModel):
    instance_code: Optional[str] = None
    type: Optional[str] = None
    object: Optional[Dict[str, Any]] = None

class LarkEvent(BaseModel):
    schema: Optional[str] = None
    header: Optional[EventHeader] = None
    event: Optional[EventBody] = None
    type: Optional[str] = None  # For URL verification
    challenge: Optional[str] = None  # For URL verification

class EventRecord(BaseModel):
    timestamp: datetime
    event_type: str
    instance_code: Optional[str]
    raw_event: str
