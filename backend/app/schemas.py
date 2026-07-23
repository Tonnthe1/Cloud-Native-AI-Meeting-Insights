from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional
from datetime import datetime


class ActionItem(BaseModel):
    task: str
    owner: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high"]] = None
    status: Literal["open", "in_progress", "done"] = "open"


class StructuredInsights(BaseModel):
    overview: str
    key_points: list[str] = []
    decisions: list[str] = []
    action_items: list[ActionItem] = []
    risks: list[str] = []
    open_questions: list[str] = []
    provider: Optional[str] = None


class MeetingListItem(BaseModel):
    id: int
    filename: str
    created_at: datetime
    summary: Optional[str] = None
    language: Optional[str] = None
    duration_seconds: Optional[float] = None
    keywords: Optional[list[str]] = None
    status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MeetingDetail(BaseModel):
    id: int
    filename: str
    created_at: datetime
    language: Optional[str] = None
    duration_seconds: Optional[float] = None
    keywords: Optional[list[str]] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    insights: Optional[StructuredInsights] = None
    status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
