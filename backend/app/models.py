from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime, timezone
from .db import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    transcript = Column(Text)
    summary = Column(Text)
    insights_json = Column(Text)
    insight_provider = Column(String(64))
    processing_status = Column(String(32), nullable=False, default="queued")
    language = Column(String(16))
    duration_seconds = Column(Float)
    keywords = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
