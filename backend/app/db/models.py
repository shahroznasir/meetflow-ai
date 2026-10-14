from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    source = Column(String(50), default="web_extension")  # web_extension, telephony_ivr, manual_upload
    status = Column(String(50), default="processing")  # recording, processing, completed, failed
    duration_seconds = Column(Integer, nullable=True, default=0)
    audio_path = Column(String(500), nullable=True)
    pdf_path = Column(String(500), nullable=True)
    email_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    participants = relationship("Participant", back_populates="meeting", cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")
    summary = relationship("MeetingSummary", uselist=False, back_populates="meeting", cascade="all, delete-orphan")

class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    role = Column(String(50), default="attendee")  # host, attendee, caller, agent

    meeting = relationship("Meeting", back_populates="participants")

class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    task = Column(Text, nullable=False)
    assignee_name = Column(String(255), nullable=False)
    assignee_email = Column(String(255), nullable=True)
    due_date = Column(String(100), nullable=True)
    priority = Column(String(50), default="Medium")  # Low, Medium, High, Urgent
    status = Column(String(50), default="Pending")  # Pending, In Progress, Completed
    context_quote = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="action_items")

class MeetingSummary(Base):
    __tablename__ = "meeting_summaries"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True)
    executive_summary = Column(Text, nullable=False)
    sentiment = Column(String(50), default="Productive")
    topics_json = Column(Text, nullable=True)
    key_decisions_json = Column(Text, nullable=True)
    unresolved_questions_json = Column(Text, nullable=True)
    transcript_json = Column(Text, nullable=True)
    raw_mom_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="summary")
