import os
import json
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.db.models import Meeting, Participant, ActionItem, MeetingSummary
from app.schemas.mom import MeetingMinutesPackage, ParticipantSchema, MeetingChatRequest, MeetingChatResponse
from app.services.gemini_service import gemini_service
from app.services.pdf_service import pdf_service
from app.services.email_service import email_service
from app.services.audio_processor import AudioProcessor
from app.config import settings

router = APIRouter(prefix="/api/v1/meetings", tags=["Meetings"])

def _to_utc_iso(dt):
    if not dt:
        return None
    iso = dt.isoformat()
    return iso if iso.endswith("Z") else f"{iso}Z"

@router.post("/recordings")
async def upload_and_process_recording(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    meeting_title: str = Form("Meeting Sync"),
    participants_json: str = Form("[]"),
    source: str = Form("web_extension"),
    auto_email: bool = Form(True),
    duration_seconds: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """Receives recorded audio from Chrome Extension or app, processes with Gemini, and dispatches MoM."""
    # 1. Parse participants
    try:
        raw_participants = json.loads(participants_json)
        participants_data = [ParticipantSchema(**p) for p in raw_participants]
    except Exception:
        participants_data = []

    # 2. Read audio content & store
    audio_bytes = await audio_file.read()
    filename = f"rec_{os.urandom(8).hex()}_{audio_file.filename}"
    saved_audio_path = os.path.join(settings.STORAGE_DIR, settings.RAW_AUDIO_SUBDIR, filename)

    with open(saved_audio_path, "wb") as f:
        f.write(audio_bytes)

    if duration_seconds is not None and duration_seconds > 0:
        duration = float(duration_seconds)
    else:
        duration = AudioProcessor.get_wav_duration_seconds(audio_bytes)
        if duration == 0.0 and len(audio_bytes) > 0:
            duration = max(1.0, round(len(audio_bytes) / 8000.0, 1))

    # 3. Create Meeting record in DB
    meeting = Meeting(
        title=meeting_title,
        source=source,
        status="processing",
        duration_seconds=int(duration),
        audio_path=saved_audio_path
    )
    db.add(meeting)
    db.flush()

    for p in participants_data:
        db.add(Participant(meeting_id=meeting.id, name=p.name, email=p.email, role=p.role))
    db.commit()

    # 4. Generate Minutes with Gemini
    mime_type = audio_file.content_type or "audio/webm"
    mom_package = await gemini_service.generate_minutes_from_audio(
        audio_bytes=audio_bytes,
        mime_type=mime_type,
        meeting_title=meeting_title,
        known_participants=participants_data
    )

    # 5. Generate PDF
    pdf_path = pdf_service.generate_mom_pdf(meeting.id, mom_package)
    meeting.pdf_path = pdf_path

    # 6. Save Action Items & Summary
    for item in mom_package.action_items:
        db.add(ActionItem(
            meeting_id=meeting.id,
            task=item.task,
            assignee_name=item.assignee_name,
            assignee_email=item.assignee_email,
            due_date=item.due_date,
            priority=item.priority,
            context_quote=item.context_quote,
            status="Pending"
        ))

    db.add(MeetingSummary(
        meeting_id=meeting.id,
        executive_summary=mom_package.executive_summary,
        sentiment=mom_package.overall_sentiment,
        topics_json=json.dumps([t.model_dump() for t in mom_package.agenda_topics]),
        key_decisions_json=json.dumps(mom_package.key_decisions),
        unresolved_questions_json=json.dumps(mom_package.unresolved_questions),
        transcript_json=json.dumps([t.model_dump() for t in (mom_package.transcript or [])]),
        raw_mom_json=mom_package.model_dump_json()
    ))

    # 7. Email Dispatching
    email_recipients = [p.email for p in participants_data if p.email]
    if auto_email and email_recipients:
        email_sent = await email_service.dispatch_meeting_recap(
            recipients=email_recipients,
            mom=mom_package,
            pdf_path=pdf_path
        )
        meeting.email_sent = email_sent

    meeting.status = "completed"
    db.commit()
    db.refresh(meeting)

    return {
        "status": "success",
        "meeting_id": meeting.id,
        "title": meeting.title,
        "email_sent": meeting.email_sent,
        "minutes": mom_package.model_dump(),
        "pdf_url": f"/api/v1/meetings/{meeting.id}/pdf"
    }

@router.get("")
def list_meetings(db: Session = Depends(get_db)):
    """Lists all stored meetings."""
    meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).all()
    results = []
    for m in meetings:
        results.append({
            "id": m.id,
            "title": m.title,
            "source": m.source,
            "status": m.status,
            "duration_seconds": m.duration_seconds,
            "email_sent": m.email_sent,
            "created_at": _to_utc_iso(m.created_at),
            "participants_count": len(m.participants),
            "action_items_count": len(m.action_items)
        })
    return results

@router.get("/{meeting_id}")
def get_meeting_details(meeting_id: int, db: Session = Depends(get_db)):
    """Retrieves full meeting details, summary, and action items."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    mom_data = json.loads(meeting.summary.raw_mom_json) if meeting.summary else None

    return {
        "id": meeting.id,
        "title": meeting.title,
        "source": meeting.source,
        "status": meeting.status,
        "duration_seconds": meeting.duration_seconds,
        "email_sent": meeting.email_sent,
        "created_at": _to_utc_iso(meeting.created_at),
        "participants": [{"name": p.name, "email": p.email, "role": p.role} for p in meeting.participants],
        "action_items": [
            {
                "id": a.id,
                "task": a.task,
                "assignee_name": a.assignee_name,
                "assignee_email": a.assignee_email,
                "due_date": a.due_date,
                "priority": a.priority,
                "status": a.status,
                "context_quote": a.context_quote
            } for a in meeting.action_items
        ],
        "minutes": mom_data,
        "has_pdf": bool(meeting.pdf_path and os.path.exists(meeting.pdf_path)),
        "has_audio": bool(meeting.audio_path and os.path.exists(meeting.audio_path)),
        "audio_url": f"/api/v1/meetings/{meeting.id}/audio" if meeting.audio_path and os.path.exists(meeting.audio_path) else None
    }

@router.get("/{meeting_id}/audio")
def stream_meeting_audio(meeting_id: int, db: Session = Depends(get_db)):
    """Streams the raw audio recording for in-browser playback."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting or not meeting.audio_path or not os.path.exists(meeting.audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    media_type = "audio/webm"
    if meeting.audio_path.endswith(".wav"):
        media_type = "audio/wav"
    elif meeting.audio_path.endswith(".mp3"):
        media_type = "audio/mpeg"
    elif meeting.audio_path.endswith(".ogg"):
        media_type = "audio/ogg"
    return FileResponse(meeting.audio_path, media_type=media_type)

@router.post("/{meeting_id}/reprocess")
async def reprocess_meeting_recording(meeting_id: int, db: Session = Depends(get_db)):
    """Re-analyzes and transcribes an existing meeting recording using Gemini."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if not meeting.audio_path or not os.path.exists(meeting.audio_path):
        raise HTTPException(status_code=400, detail="Original audio file is no longer available on disk")

    with open(meeting.audio_path, "rb") as f:
        audio_bytes = f.read()

    mime_type = "audio/webm"
    if meeting.audio_path.endswith(".wav"):
        mime_type = "audio/wav"
    elif meeting.audio_path.endswith(".mp3"):
        mime_type = "audio/mpeg"
    elif meeting.audio_path.endswith(".ogg"):
        mime_type = "audio/ogg"

    participants_data = [ParticipantSchema(name=p.name, email=p.email, role=p.role) for p in meeting.participants]

    # Re-run Gemini
    mom_package = await gemini_service.generate_minutes_from_audio(
        audio_bytes=audio_bytes,
        mime_type=mime_type,
        meeting_title=meeting.title,
        known_participants=participants_data
    )

    # Re-generate PDF
    pdf_path = pdf_service.generate_mom_pdf(meeting.id, mom_package)
    meeting.pdf_path = pdf_path

    # Replace Action Items
    db.query(ActionItem).filter(ActionItem.meeting_id == meeting.id).delete()
    for item in mom_package.action_items:
        db.add(ActionItem(
            meeting_id=meeting.id,
            task=item.task,
            assignee_name=item.assignee_name,
            assignee_email=item.assignee_email,
            due_date=item.due_date,
            priority=item.priority,
            context_quote=item.context_quote,
            status="Pending"
        ))

    # Replace Summary
    if meeting.summary:
        meeting.summary.executive_summary = mom_package.executive_summary
        meeting.summary.sentiment = mom_package.overall_sentiment
        meeting.summary.topics_json = json.dumps([t.model_dump() for t in mom_package.agenda_topics])
        meeting.summary.key_decisions_json = json.dumps(mom_package.key_decisions)
        meeting.summary.unresolved_questions_json = json.dumps(mom_package.unresolved_questions)
        meeting.summary.transcript_json = json.dumps([t.model_dump() for t in (mom_package.transcript or [])])
        meeting.summary.raw_mom_json = mom_package.model_dump_json()
    else:
        db.add(MeetingSummary(
            meeting_id=meeting.id,
            executive_summary=mom_package.executive_summary,
            sentiment=mom_package.overall_sentiment,
            topics_json=json.dumps([t.model_dump() for t in mom_package.agenda_topics]),
            key_decisions_json=json.dumps(mom_package.key_decisions),
            unresolved_questions_json=json.dumps(mom_package.unresolved_questions),
            transcript_json=json.dumps([t.model_dump() for t in (mom_package.transcript or [])]),
            raw_mom_json=mom_package.model_dump_json()
        ))

    meeting.status = "completed"
    db.commit()
    db.refresh(meeting)

    return {
        "status": "success",
        "message": "Meeting successfully re-processed with Gemini",
        "meeting_id": meeting.id,
        "minutes": mom_package.model_dump()
    }

@router.get("/{meeting_id}/transcript")
def get_meeting_transcript(meeting_id: int, db: Session = Depends(get_db)):
    """Retrieves full verbatim speaker-diarized transcript with timestamps."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting or not meeting.summary:
        raise HTTPException(status_code=404, detail="Meeting or transcript not found")

    mom_data = json.loads(meeting.summary.raw_mom_json) if meeting.summary else {}
    transcript_segments = mom_data.get("transcript", [])

    plain_lines = []
    for seg in transcript_segments:
        plain_lines.append(f"{seg.get('timestamp', '')} {seg.get('speaker', 'Speaker')}: {seg.get('text', '')}")

    return {
        "meeting_id": meeting.id,
        "title": meeting.title,
        "segments": transcript_segments,
        "plain_text": "\n".join(plain_lines)
    }

@router.get("/{meeting_id}/pdf")
def download_meeting_pdf(meeting_id: int, db: Session = Depends(get_db)):
    """Serves the generated PDF Minutes document."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting or not meeting.pdf_path or not os.path.exists(meeting.pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found for this meeting")
    return FileResponse(meeting.pdf_path, media_type="application/pdf", filename=f"MoM_Meeting_{meeting.id}.pdf")

@router.post("/{meeting_id}/email")
async def trigger_email_recap(
    meeting_id: int,
    custom_recipients: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """Manually re-triggers email dispatch for a meeting to specified or stored recipients."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting or not meeting.summary:
        raise HTTPException(status_code=404, detail="Meeting summary not found")

    recipients = custom_recipients or [p.email for p in meeting.participants if p.email]
    if not recipients:
        raise HTTPException(status_code=400, detail="No email addresses available for this meeting")

    mom_package = MeetingMinutesPackage.model_validate_json(meeting.summary.raw_mom_json)
    success = await email_service.dispatch_meeting_recap(recipients, mom_package, meeting.pdf_path)

    meeting.email_sent = success
    db.commit()
    return {"status": "success", "recipients": recipients, "sent": success}

@router.delete("/{meeting_id}")
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """Permanently deletes a meeting record, its audio file, and its generated PDF."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Safely remove audio file from disk
    if meeting.audio_path and os.path.exists(meeting.audio_path):
        try:
            os.remove(meeting.audio_path)
        except Exception:
            pass

    # Safely remove PDF file from disk
    if meeting.pdf_path and os.path.exists(meeting.pdf_path):
        try:
            os.remove(meeting.pdf_path)
        except Exception:
            pass

    db.delete(meeting)
    db.commit()

    return {
        "status": "success",
        "message": f"Meeting #{meeting_id} deleted successfully",
        "deleted_id": meeting_id
    }

@router.delete("")
def delete_all_meetings(db: Session = Depends(get_db)):
    """Permanently deletes all meeting records and their associated files."""
    meetings = db.query(Meeting).all()
    count = len(meetings)
    for m in meetings:
        if m.audio_path and os.path.exists(m.audio_path):
            try:
                os.remove(m.audio_path)
            except Exception:
                pass
        if m.pdf_path and os.path.exists(m.pdf_path):
            try:
                os.remove(m.pdf_path)
            except Exception:
                pass
        db.delete(m)
    db.commit()
    return {"status": "success", "message": f"Deleted {count} meetings", "deleted_count": count}

@router.post("/{meeting_id}/chat", response_model=MeetingChatResponse)
async def chat_with_meeting_ai(
    meeting_id: int,
    payload: MeetingChatRequest,
    db: Session = Depends(get_db)
):
    """Ask Fred: Interactive AI meeting chatbot grounded on the meeting's transcript and minutes."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    mom_data = json.loads(meeting.summary.raw_mom_json) if meeting.summary else {}

    meeting_context = {
        "title": meeting.title,
        "summary": mom_data.get("executive_summary", ""),
        "decisions": mom_data.get("key_decisions", []),
        "actions": [
            {
                "task": a.task,
                "assignee": a.assignee_name,
                "due_date": a.due_date,
                "priority": a.priority,
                "quote": a.context_quote
            } for a in meeting.action_items
        ],
        "transcript": mom_data.get("transcript", [])
    }

    result = await gemini_service.chat_with_meeting(
        meeting_context=meeting_context,
        question=payload.question,
        history=payload.history
    )

    return result
