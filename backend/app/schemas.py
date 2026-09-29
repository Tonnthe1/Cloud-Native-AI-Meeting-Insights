from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import datetime, timezone


class MeetingListItem(BaseModel):
    id: int
    filename: str
    created_at: datetime
    status: str = "completed"
    error_message: Optional[str] = None
    summary: Optional[str] = None
    language: Optional[str] = None
    duration_seconds: Optional[float] = None
    keywords: Optional[list[str]] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("keywords", mode="before")
    @classmethod
    def _split_keywords(cls, value):
        # Keywords are stored as a comma-separated string.
        if isinstance(value, str):
            return [k.strip() for k in value.split(",") if k.strip()] or None
        return value

    @field_validator("created_at")
    @classmethod
    def _assume_utc(cls, value: datetime) -> datetime:
        # Timestamps are stored in UTC without tz info; mark them as UTC so
        # clients don't interpret them as local time.
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class MeetingDetail(MeetingListItem):
    transcript: Optional[str] = None
