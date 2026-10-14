from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ConversationEventType(str, Enum):
    MEETING_CREATED = "meeting.created"
    AUDIO_UPLOADED = "audio.uploaded"
    TRANSCRIPT_AVAILABLE = "transcript.available"
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"
    DECISION_EXTRACTED = "decision.extracted"
    ACTION_EXTRACTED = "action.extracted"
    MOM_GENERATED = "mom.generated"
    MOM_APPROVED = "mom.approved"
    EMAIL_SENT = "email.sent"
    ACTION_COMPLETED = "action.completed"
    ACTION_OVERDUE = "action.overdue"

class EventEnvelope(BaseModel):
    event_id: str
    event_type: ConversationEventType
    aggregate_id: str  # conversation_id
    idempotency_key: str  # conversation_id + processing_version
    tenant_id: str = "default_tenant"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
