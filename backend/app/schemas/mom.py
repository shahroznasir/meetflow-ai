from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ParticipantSchema(BaseModel):
    name: str = Field(description="Name or identifier of the participant")
    email: Optional[str] = Field(None, description="Email address of the participant")
    role: Optional[str] = Field("attendee", description="Role: host, attendee, caller, agent")

class ActionItemSchema(BaseModel):
    task: str = Field(description="Clear, actionable task description")
    assignee_name: str = Field(description="Name of the person accountable")
    assignee_email: Optional[str] = Field(None, description="Email of assignee if identified")
    due_date: Optional[str] = Field(None, description="Estimated or agreed due date (e.g. YYYY-MM-DD or 'Next Friday')")
    priority: str = Field("Medium", description="Low, Medium, High, or Urgent")
    context_quote: Optional[str] = Field(None, description="Exact spoken sentence where this was agreed")

class TopicDiscussion(BaseModel):
    topic: str = Field(description="Agenda item or discussion subject")
    summary: str = Field(description="Concise summary of what was debated and agreed upon")
    decisions: List[str] = Field(default_factory=list, description="Specific decisions reached regarding this topic")

class TranscriptSegment(BaseModel):
    speaker: str = Field(description="Speaker label (e.g. Speaker 1, John, Host, Caller)")
    timestamp: Optional[str] = Field(None, description="Time marker (e.g. [01:24])")
    text: str = Field(description="Transcribed spoken dialogue")

class SpeakerTalkTime(BaseModel):
    speaker: str = Field(description="Speaker name or label")
    percentage: int = Field(default=0, description="Percentage of total talk time (0-100)")
    word_count: int = Field(default=0, description="Estimated words spoken by this speaker")

class SentimentBreakdown(BaseModel):
    positive: int = Field(default=70, description="Positive sentiment percentage (0-100)")
    neutral: int = Field(default=25, description="Neutral sentiment percentage (0-100)")
    negative: int = Field(default=5, description="Negative or challenging sentiment percentage (0-100)")

class MeetingMinutesPackage(BaseModel):
    meeting_title: str = Field(description="Descriptive meeting headline")
    meeting_type: str = Field(default="Strategy & Sync", description="Type of conversation")
    date_time: Optional[str] = Field(None, description="Date and time of the conversation")
    participants: List[str] = Field(default_factory=list, description="List of participant names identified")
    executive_summary: str = Field(description="Thorough 2-3 paragraph executive overview of the conversation")
    key_decisions: List[str] = Field(default_factory=list, description="List of agreed-upon conclusions")
    agenda_topics: List[TopicDiscussion] = Field(default_factory=list, description="Categorized discussion points")
    action_items: List[ActionItemSchema] = Field(default_factory=list, description="Extracted actionable commitments")
    unresolved_questions: List[str] = Field(default_factory=list, description="Pending or unaddressed questions")
    overall_sentiment: str = Field(default="Productive", description="Tone: Productive, Urgent, Collaborative, etc.")
    follow_up_email_subject: str = Field(description="Polished subject line for post-meeting email recap")
    follow_up_email_body_html: str = Field(description="Clean HTML email recap ready to send to participants")
    transcript: Optional[List[TranscriptSegment]] = Field(default_factory=list, description="Diarized transcript")
    speaker_talk_time: Optional[List[SpeakerTalkTime]] = Field(default_factory=list, description="Talk-time breakdown by speaker")
    words_per_minute: Optional[int] = Field(default=130, description="Average pace of speech (words per minute)")
    questions_asked: Optional[List[str]] = Field(default_factory=list, description="Key questions asked during the meeting")
    key_metrics: Optional[List[str]] = Field(default_factory=list, description="Key metrics, numbers, or figures mentioned")
    sentiment_breakdown: Optional[SentimentBreakdown] = Field(default_factory=SentimentBreakdown, description="Distribution of sentiment in conversation")

class MeetingChatRequest(BaseModel):
    question: str = Field(description="Question to Ask Fred about the meeting")
    history: Optional[List[dict]] = Field(default_factory=list, description="Previous messages in chat session")

class MeetingChatResponse(BaseModel):
    answer: str
    suggested_followups: Optional[List[str]] = Field(default_factory=list)

class MeetingCreateRequest(BaseModel):
    meeting_title: str
    participants: List[ParticipantSchema] = []
    source: str = "web_extension"  # web_extension, telephony_ivr, upload
    auto_email: bool = True

class MeetingResponse(BaseModel):
    id: int
    title: str
    source: str
    status: str
    duration_seconds: Optional[int]
    created_at: datetime
    participants: List[ParticipantSchema]
    minutes: Optional[MeetingMinutesPackage] = None
    audio_path: Optional[str] = None
    pdf_path: Optional[str] = None
    email_sent: bool = False

    class Config:
        from_attributes = True
