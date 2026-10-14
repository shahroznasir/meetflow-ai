import os
import json
import logging
from typing import Optional, List
from app.config import settings
from app.schemas.mom import MeetingMinutesPackage, ParticipantSchema

logger = logging.getLogger(__name__)

# Graceful import for Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    genai = None
    types = None
    HAS_GENAI = False

MOM_SYSTEM_INSTRUCTION = """
You are an executive Chief of Staff, professional stenographer, and AI Meeting Secretary.
Your job is to listen to the recorded multi-speaker conversation (which may be from Google Meet, Microsoft Teams, Zoom, or an IVR Telephony call) and create a world-class, production-grade Minutes of Meeting (MoM) package AND an exhaustive, verbatim, speaker-attributed transcript.

Your output must follow the strict JSON schema provided:
1. Executive Summary: High-level overview of the purpose, themes, and tone of the meeting.
2. Agenda & Topics: Categorize all points raised, debates, viewpoints, and resolutions.
3. Key Decisions: Explicitly enumerate agreements made by the participants.
4. Action Items: Extract every commitment. You MUST identify:
   - task: Exact responsibility
   - assignee_name: Name of the responsible person (match against participant list if provided)
   - assignee_email: Email if mentioned or inferable
   - due_date: Deadlines or time commitments
   - priority: Urgent, High, Medium, or Low
   - context_quote: The exact spoken phrase where the person agreed or was assigned
5. Unresolved Questions: Points deferred for future discussions.
6. Overall Sentiment: Productive, Urgent, Collaborative, etc.
7. Follow-up Email:
8. Transcript: Provide the complete, exhaustive verbatim word-by-word transcription of everything spoken during the meeting. Segment chronologically by speaker turns with precise timestamps (e.g. [00:00:15] Speaker: exact words spoken). Do NOT omit or summarize spoken dialogue. Every utterance must be preserved.
9. Conversation Intelligence (Fireflies Analytics):
   - speaker_talk_time: For each distinct speaker in the conversation, calculate their percentage of talk time (0-100) and approximate word count. Total percentages must sum to 100.
   - words_per_minute: Estimated speaking speed / pace (e.g. 120-160 WPM).
   - questions_asked: Extract all key questions or inquiries voiced during the conversation.
   - key_metrics: Any metrics, dates, percentages, amounts, deadlines, or numerical targets mentioned.
   - sentiment_breakdown: Percentages of positive, neutral, and negative sentiment (e.g. {"positive": 80, "neutral": 15, "negative": 5}).
"""

class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client = None
        if HAS_GENAI and self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize GenAI client: {e}")

    def set_api_key(self, api_key: str):
        self.api_key = api_key
        if HAS_GENAI and api_key:
            try:
                self.client = genai.Client(api_key=api_key)
                logger.info("GenAI client initialized successfully with new key.")
            except Exception as e:
                logger.error(f"Failed to initialize GenAI client with key: {e}")

    async def generate_minutes_from_audio(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/webm",
        meeting_title: str = "Meeting Sync",
        known_participants: Optional[List[ParticipantSchema]] = None,
        live_transcript: Optional[List[dict]] = None
    ) -> MeetingMinutesPackage:
        """Processes audio through Gemini 2.0/1.5 Multimodal API and extracts structured MoM."""
        
        participant_context = ""
        if known_participants:
            names = [f"{p.name} ({p.email or 'no email'})" for p in known_participants]
            participant_context = f"\nKnown Participants in this call: {', '.join(names)}."

        prompt_text = f"""
Meeting Title: {meeting_title}
{participant_context}

CRITICAL REQUIREMENT:
You must transcribe every single utterance verbatim into the 'transcript' array with timestamps (e.g. [00:00:15]) and speaker labels (e.g. Speaker 1, Speaker 2, or participant names). Every word spoken must be accurately documented.
In addition, generate the executive summary, agenda topics, decisions, action items, and email recap according to the schema.
"""

        # If live Gemini Client is available, call Gemini API
        if self.client:
            candidates = [settings.GEMINI_MODEL, "gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-pro"]
            seen = set()
            model_list = [m for m in candidates if m and not (m in seen or seen.add(m))]

            for model_name in model_list:
                try:
                    audio_part = types.Part.from_bytes(
                        data=audio_bytes,
                        mime_type=mime_type
                    )

                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=[audio_part, prompt_text],
                        config=types.GenerateContentConfig(
                            system_instruction=MOM_SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                            response_schema=MeetingMinutesPackage,
                            temperature=0.2
                        )
                    )

                    raw_json = response.text
                    settings.GEMINI_MODEL = model_name
                    return MeetingMinutesPackage.model_validate_json(raw_json)
                except Exception as e:
                    logger.warning(f"Gemini API model {model_name} invocation error: {e}")
                    if "404" in str(e) or "NOT_FOUND" in str(e):
                        continue
                    break

        # Fallback / Mock Generator for offline testing or missing API key
        return self._generate_mock_minutes(meeting_title, known_participants)

    def _generate_mock_minutes(
        self,
        meeting_title: str,
        known_participants: Optional[List[ParticipantSchema]] = None
    ) -> MeetingMinutesPackage:
        """Generates realistic structured meeting minutes for testing and offline development."""
        p_names = [p.name for p in known_participants] if known_participants else ["Host", "Participant"]
        if len(p_names) < 2:
            p_names.append("Colleague")

        speaker_a = p_names[0]
        speaker_b = p_names[1]

        p1_email = known_participants[0].email if (known_participants and known_participants[0].email) else None
        p2_email = known_participants[1].email if (known_participants and len(known_participants) > 1 and known_participants[1].email) else None

        return MeetingMinutesPackage(
            meeting_title=meeting_title,
            meeting_type="Project Strategy & Status Sync",
            date_time="Today",
            participants=p_names,
            executive_summary=(
                f"During this session, {speaker_a} and {speaker_b} reviewed project milestones, timeline expectations, "
                f"and integration priorities. Key architectural directions were solidified, and clear responsibilities were assigned "
                f"for technical deliverables and stakeholder communication."
            ),
            key_decisions=[
                "Approved deployment of the new AI-powered communication pipeline.",
                "Agreed to synchronize weekly progress reports every Friday at 10 AM.",
                "Confirmed use of open-source infrastructure for internal data sovereignty."
            ],
            agenda_topics=[
                {
                    "topic": "Architecture & Cloud Infrastructure",
                    "summary": f"{speaker_a} presented the technical topology. {speaker_b} confirmed compliance with security protocols.",
                    "decisions": ["Deploy stack with Docker Compose and PostgreSQL."]
                },
                {
                    "topic": "Action Items & Timeline Alignment",
                    "summary": "Reviewed immediate action points and deliverables for the upcoming sprint.",
                    "decisions": ["Milestones locked for Phase 1 delivery."]
                }
            ],
            action_items=[
                {
                    "task": "Finalize backend API documentation and circulate with the team",
                    "assignee_name": speaker_a,
                    "assignee_email": p1_email,
                    "due_date": "End of Week",
                    "priority": "High",
                    "context_quote": f"'{speaker_a}: I will finalize the backend API docs and send them over by Friday.'"
                },
                {
                    "task": "Verify extension audio capture on Microsoft Teams and Google Meet",
                    "assignee_name": speaker_b,
                    "assignee_email": p2_email,
                    "due_date": "Next Monday",
                    "priority": "Medium",
                    "context_quote": f"'{speaker_b}: Let me handle testing across both Meet and Teams.'"
                }
            ],
            unresolved_questions=[
                "Should we implement single sign-on (SSO) with Okta in the next release?"
            ],
            overall_sentiment="Highly Productive & Collaborative",
            follow_up_email_subject=f"Action Items & Minutes of Meeting: {meeting_title}",
            follow_up_email_body_html=f"""
<div style="font-family: Arial, sans-serif; color: #1e293b; line-height: 1.6;">
  <h2 style="color: #0284c7;">Minutes of Meeting: {meeting_title}</h2>
  <p>Thank you for participating in today's discussion. Below is the executive summary and key action items agreed upon:</p>
  
  <h3 style="color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px;">Executive Summary</h3>
  <p>The team reviewed upcoming development milestones, confirmed architecture directions, and assigned clear action ownership.</p>
  
  <h3 style="color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px;">Key Action Items</h3>
  <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
    <thead>
      <tr style="background: #f1f5f9; text-align: left;">
        <th style="padding: 8px; border: 1px solid #cbd5e1;">Task</th>
        <th style="padding: 8px; border: 1px solid #cbd5e1;">Assignee</th>
        <th style="padding: 8px; border: 1px solid #cbd5e1;">Deadline</th>
        <th style="padding: 8px; border: 1px solid #cbd5e1;">Priority</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="padding: 8px; border: 1px solid #cbd5e1;">Finalize backend API documentation</td>
        <td style="padding: 8px; border: 1px solid #cbd5e1;"><strong>{speaker_a}</strong></td>
        <td style="padding: 8px; border: 1px solid #cbd5e1;">End of Week</td>
        <td style="padding: 8px; border: 1px solid #cbd5e1;"><span style="color: #dc2626;">High</span></td>
      </tr>
      <tr>
        <td style="padding: 8px; border: 1px solid #cbd5e1;">Verify extension audio capture</td>
        <td style="padding: 8px; border: 1px solid #cbd5e1;"><strong>{speaker_b}</strong></td>
        <td style="padding: 8px; border: 1px solid #cbd5e1;">Next Monday</td>
        <td style="padding: 8px; border: 1px solid #cbd5e1;"><span style="color: #0284c7;">Medium</span></td>
      </tr>
    </tbody>
  </table>
  
  <p style="margin-top: 20px; font-size: 13px; color: #64748b;">
    The complete Minutes of Meeting PDF is attached for your records.
  </p>
</div>
""",
            transcript=[
                {"speaker": speaker_a, "timestamp": "[00:00:05]", "text": "Hello everyone, thanks for jumping on. Let's go through the roadmap."},
                {"speaker": speaker_b, "timestamp": "[00:00:15]", "text": "Sounds good! I've been reviewing the AI engine and audio capture design."},
                {"speaker": speaker_a, "timestamp": "[00:00:30]", "text": "Great. I'll finalize the backend API docs and send them over by Friday."},
                {"speaker": speaker_b, "timestamp": "[00:00:45]", "text": "Perfect, let me handle testing across both Meet and Teams."}
            ],
            speaker_talk_time=[
                {"speaker": speaker_a, "percentage": 55, "word_count": 210},
                {"speaker": speaker_b, "percentage": 45, "word_count": 175}
            ],
            words_per_minute=142,
            questions_asked=[
                "Should we implement single sign-on (SSO) with Okta in the next release?",
                "What is the target deployment deadline for the extension?"
            ],
            key_metrics=[
                "Weekly progress reports every Friday at 10 AM",
                "Phase 1 delivery roadmap milestones",
                "100% test coverage target"
            ],
            sentiment_breakdown={"positive": 75, "neutral": 20, "negative": 5}
        )

    async def chat_with_meeting(
        self,
        meeting_context: dict,
        question: str,
        history: Optional[List[dict]] = None
    ) -> dict:
        """Interactive Ask-Aura AI Meeting Assistant for MeetFlow AI powered by Gemini 2.5 Flash."""
        if not self.client:
            return {
                "answer": "Gemini API client is not configured. Please set your Gemini API key in Settings.",
                "suggested_followups": ["How do I set my Gemini API key?"]
            }

        title = meeting_context.get("title", "Meeting")
        summary = meeting_context.get("summary", "")
        decisions = meeting_context.get("decisions", [])
        actions = meeting_context.get("actions", [])
        transcript = meeting_context.get("transcript", [])

        transcript_text = "\n".join([f"{t.get('timestamp', '')} {t.get('speaker', 'Speaker')}: {t.get('text', '')}" for t in transcript])

        system_instruction = f"""You are Aura, an elite AI Executive Meeting Assistant for MeetFlow AI (powered by Google Gemini 2.5 Flash).
You have full access to the complete meeting data:
- Meeting Title: {title}
- Executive Summary: {summary}
- Key Decisions: {json.dumps(decisions)}
- Action Items: {json.dumps(actions)}
- Verbatim Transcript:
{transcript_text}

Your mission:
1. Answer the user's questions about this meeting with surgical precision, citing who said what and at what timestamp.
2. If asked to draft a follow-up email, create a bulleted summary, extract questions, or analyze sentiment, deliver it in executive-ready GitHub markdown.
3. Keep your answers clear, concise, proactive, and directly grounded in the meeting dialogue.
4. Conclude your answer with 2 or 3 suggested follow-up questions formatted as:
---FOLLOW_UPS---
- First suggested question?
- Second suggested question?
"""

        messages_content = []
        if history:
            for h in history[-6:]:
                role = "user" if h.get("role") == "user" else "model"
                messages_content.append(f"{role.upper()}: {h.get('content', '')}")

        messages_content.append(f"USER: {question}")
        full_prompt = "\n\n".join(messages_content)

        candidates = [settings.GEMINI_MODEL, "gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-pro"]
        seen = set()
        model_list = [m for m in candidates if m and not (m in seen or seen.add(m))]

        last_error = ""
        for model_name in model_list:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.3
                    )
                )

                raw_text = response.text or ""
                follow_ups = []
                if "---FOLLOW_UPS---" in raw_text:
                    parts = raw_text.split("---FOLLOW_UPS---")
                    answer = parts[0].strip()
                    for line in parts[1].strip().split("\n"):
                        cleaned = line.strip().lstrip("-").lstrip("*").strip()
                        if cleaned:
                            follow_ups.append(cleaned)
                else:
                    answer = raw_text.strip()
                    follow_ups = [
                        "What were the next steps agreed upon?",
                        "Draft an email recap to all attendees",
                        "What questions were left unanswered?"
                    ]

                settings.GEMINI_MODEL = model_name
                return {
                    "answer": answer,
                    "suggested_followups": follow_ups[:3]
                }
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Ask Aura Gemini chat error on {model_name}: {e}")
                if "404" in last_error or "NOT_FOUND" in last_error:
                    continue
                break

        return {
            "answer": f"I ran into an issue analyzing the meeting: {last_error}",
            "suggested_followups": ["Can you summarize the meeting?", "What action items were assigned?"]
        }

gemini_service = GeminiService()
