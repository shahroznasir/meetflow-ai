from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ConversationSourceType(str, Enum):
    TEAMS = "teams"
    GOOGLE_MEET = "google_meet"
    ZOOM = "zoom"
    AUDIO_UPLOAD = "audio_upload"
    BROWSER_MIC = "browser_mic"
    IVR_TELEPHONY = "ivr_telephony"
    SIP_RTP = "sip_rtp"

class ApprovalMode(str, Enum):
    MANUAL_APPROVAL = "manual_approval"
    AUTO_CONFIDENCE = "auto_confidence"
    AUTO_INTERNAL = "auto_internal"

class ActionPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"

class Participant(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    role: str = "attendee"
    is_external: bool = False
    voice_enrolled: bool = False

class TranscriptEntry(BaseModel):
    entry_id: str
    speaker_id: str
    speaker_name: Optional[str] = None
    start_time_seconds: float
    end_time_seconds: float
    raw_text: str
    normalized_text: str
    confidence: float = 1.0

class Decision(BaseModel):
    decision_id: str
    decision: str
    supporting_discussion: str
    start_timestamp: str
    end_timestamp: Optional[str] = None
    participants: List[str]
    evidence: List[str]
    confidence: float

class ActionItem(BaseModel):
    action_id: str
    description: str
    owner: str
    owner_email: Optional[str] = None
    due_date: Optional[str] = None
    priority: ActionPriority = ActionPriority.MEDIUM
    status: ActionStatus = ActionStatus.PROPOSED
    source_timestamp: str
    evidence: str
    confidence: float
    validation_status: str = "pending_validation"

class Risk(BaseModel):
    risk_id: str
    description: str
    severity: str  # low, medium, high, critical
    owner: Optional[str] = None
    evidence_timestamp: str
    evidence: str

class UnresolvedQuestion(BaseModel):
    question_id: str
    question: str
    asked_by: str
    timestamp: str
    status: str = "unresolved"

class TopicDiscussion(BaseModel):
    topic: str
    start_time_seconds: float
    end_time_seconds: float
    summary: str
    key_points: List[str]

class MinutesOfMeeting(BaseModel):
    executive_summary: str
    agenda: List[str]
    discussion_points: List[TopicDiscussion]
    decisions: List[Decision]
    action_items: List[ActionItem]
    risks: List[Risk]
    open_questions: List[UnresolvedQuestion]
    follow_up_email_subject: str
    follow_up_email_body_html: str
    model_version: str
    prompt_version: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class CanonicalConversation(BaseModel):
    conversation_id: str
    tenant_id: str = "default_tenant"
    source: ConversationSourceType
    source_meeting_id: Optional[str] = None
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    participants: List[Participant]
    audio_s3_uri: Optional[str] = None
    raw_transcript: List[TranscriptEntry] = []
    mom: Optional[MinutesOfMeeting] = None
    approval_mode: ApprovalMode = ApprovalMode.MANUAL_APPROVAL
    is_approved: bool = False
    metadata: Dict[str, Any] = {}
