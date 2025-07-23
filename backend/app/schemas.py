from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MeetingOut(BaseModel):
    id: int
    filename: str
    transcript: Optional[str]
    summary: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
