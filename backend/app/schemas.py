from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MeetingListItem(BaseModel):
    id: int
    filename: str
    created_at: datetime
    summary: Optional[str] = None
    language: Optional[str] = None
    duration_seconds: Optional[float] = None
    keywords: Optional[list[str]] = None

    class Config:
        from_attributes = True
    

class MeetingDetail(BaseModel):
    id: int
    filename: str
    created_at: datetime
    language: Optional[str] = None
    duration_seconds: Optional[float] = None
    keywords: Optional[list[str]] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None

    class Config:
        from_attributes = True

