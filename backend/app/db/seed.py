import os
import json
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import Meeting, Participant, ActionItem, MeetingSummary
from app.config import settings

def seed_demo_meeting_if_empty(db: Session = None):
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        if db.query(Meeting).count() > 0:
            return

        json_path = os.path.join(os.path.dirname(__file__), "seed_data.json")
        if not os.path.exists(json_path):
            return

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        m_data = data["meeting"]

        # Dynamically locate demo audio
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        demo_audio = os.path.join(base_dir, "storage", "audio_raw", "demo_meeting_audio.wav")
        if not os.path.exists(demo_audio):
            demo_audio = os.path.join(settings.STORAGE_DIR, settings.RAW_AUDIO_SUBDIR, "demo_meeting_audio.wav")

        meeting = Meeting(
            id=1,
            title=m_data.get("title", "Product Strategy & AI Architecture Sync"),
            source=m_data.get("source", "web_extension"),
            status=m_data.get("status", "completed"),
            duration_seconds=m_data.get("duration_seconds", 22),
            audio_path=demo_audio if os.path.exists(demo_audio) else None,
            pdf_path=None,
            email_sent=0
        )
        db.add(meeting)
        db.flush()

        for p in data.get("participants", []):
            db.add(Participant(
                meeting_id=meeting.id,
                name=p["name"],
                email=p.get("email"),
                role=p.get("role", "attendee")
            ))

        for a in data.get("action_items", []):
            db.add(ActionItem(
                meeting_id=meeting.id,
                task=a["task"],
                assignee_name=a.get("assignee_name", "Team"),
                assignee_email=a.get("assignee_email"),
                due_date=a.get("due_date", "TBD"),
                priority=a.get("priority", "Medium"),
                status=a.get("status", "Pending"),
                context_quote=a.get("context_quote")
            ))

        summ = data.get("summary", {})
        db.add(MeetingSummary(
            meeting_id=meeting.id,
            executive_summary=summ.get("executive_summary", ""),
            sentiment=summ.get("sentiment", "Positive"),
            topics_json=summ.get("topics_json", "[]"),
            key_decisions_json=summ.get("key_decisions_json", "[]"),
            unresolved_questions_json=summ.get("unresolved_questions_json", "[]"),
            transcript_json=summ.get("transcript_json", "[]"),
            raw_mom_json=summ.get("raw_mom_json", "{}")
        ))

        db.commit()
    except Exception as e:
        db.rollback()
        print("Seed warning:", e)
    finally:
        if should_close:
            db.close()
