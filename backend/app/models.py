from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime, timezone
from .db import Base


class MeetingStatus:
    """Lifecycle of a meeting as it moves through the processing pipeline."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    PENDING = (QUEUED, PROCESSING)


class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    transcript = Column(Text)
    summary = Column(Text)
    language = Column(String(8))
    duration_seconds = Column(Float)
    keywords = Column(Text)
    status = Column(String(20), nullable=False,
                    default=MeetingStatus.QUEUED)
    error_message = Column(Text)
    # Path of the stored upload; filenames are not unique, so this is what
    # the worker reads and what gets removed when the meeting is deleted.
    file_path = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
