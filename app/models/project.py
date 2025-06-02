# models/project.py
from pydantic import BaseModel
from typing import Optional, List

class ProjectLogBase(BaseModel):
    date: str
    content: str
    mood: Optional[str] = None

class ProjectLogCreate(ProjectLogBase):
    pass

class ProjectLog(ProjectLogBase):
    id: str
    project_id: str
    created_at: str

class ProjectBase(BaseModel):
    route_name: str
    grade: str
    crag: str
    description: Optional[str] = ""
    route_angle: str  # 'slab', 'vertical', 'overhanging', 'roof'
    route_length: str  # 'long', 'medium', 'short', 'bouldery'
    hold_type: str     # 'crack', 'crimpy', 'slopers', 'jugs', 'pinches', 'pockets'

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    route_name: Optional[str] = None
    grade: Optional[str] = None
    crag: Optional[str] = None
    description: Optional[str] = None
    route_angle: Optional[str] = None
    route_length: Optional[str] = None
    hold_type: Optional[str] = None
    is_completed: Optional[bool] = None
    completion_date: Optional[str] = None

class Project(ProjectBase):
    id: str
    user_id: int
    is_completed: bool
    completion_date: Optional[str] = None
    created_at: str
    updated_at: str
    logs: List[ProjectLog] = []