from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime, timezone
from .db import Base


class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    transcript = Column(Text)
    summary = Column(Text)
    language = Column(String(8))
    duration_seconds = Column(Float)
    keywords = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
