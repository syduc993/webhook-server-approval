from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class FormField(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    value: Optional[Any] = None

class TaskInfo(BaseModel):
    node_id: Optional[str] = None
    status: Optional[str] = None
    task_id: Optional[str] = None
    node_name: Optional[str] = None

class ApprovalInstance(BaseModel):
    instance_code: str
    status: Optional[str] = None
    form: Optional[str] = None
    task_list: Optional[List[TaskInfo]] = None
