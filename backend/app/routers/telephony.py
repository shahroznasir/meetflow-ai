import base64
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db, SessionLocal
from app.db.models import Meeting, Participant, ActionItem, MeetingSummary
from app.services.audio_processor import AudioProcessor
from app.services.gemini_service import gemini_service
from app.services.pdf_service import pdf_service
from app.services.email_service import email_service
from app.schemas.mom import ParticipantSchema
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/telephony", tags=["Universal Telephony & IVR"])

@router.websocket("/ws/{call_sid}")
async def telephony_audio_stream(websocket: WebSocket, call_sid: str):
    """
    Universal WebSocket endpoint for Telephony & IVR systems (Twilio, Asterisk, FreeSWITCH).
    Streams live 8kHz mu-law audio packets, decodes to 16kHz PCM, and processes with Gemini on hangup.
    """
    await websocket.accept()
    logger.info(f"Telephony stream opened for Call SID: {call_sid}")

    audio_chunks_pcm = []
    metadata = {
        "call_sid": call_sid,
        "caller": "Customer",
        "agent": "Agent/IVR",
        "email": None
    }

    try:
        while True:
            raw_text = await websocket.receive_text()
            data = json.loads(raw_text)
            event = data.get("event")

            if event == "start":
                start_data = data.get("start", {})
                custom_params = start_data.get("customParameters", {})
                metadata["caller"] = custom_params.get("caller", "Caller")
                metadata["agent"] = custom_params.get("agent", "Representative")
                metadata["email"] = custom_params.get("email", None)
                logger.info(f"Telephony session started: {metadata}")

            elif event == "media":
                media_data = data.get("media", {})
                payload_b64 = media_data.get("payload", "")
                if payload_b64:
                    mulaw_bytes = base64.b64decode(payload_b64)
                    pcm_bytes = AudioProcessor.decode_mulaw_to_pcm(mulaw_bytes)
                    resampled = AudioProcessor.resample_pcm(pcm_bytes, orig_sr=8000, target_sr=16000)
                    audio_chunks_pcm.append(resampled)

            elif event == "stop":
                logger.info(f"Telephony call completed for SID: {call_sid}")
                break

    except WebSocketDisconnect:
        logger.info(f"Telephony WebSocket disconnected for SID: {call_sid}")
    except Exception as e:
        logger.error(f"Error handling telephony stream: {e}")

    # Process call on completion
    if audio_chunks_pcm:
        await _finalize_telephony_call(call_sid, audio_chunks_pcm, metadata)

async def _finalize_telephony_call(call_sid: str, audio_chunks: list, metadata: dict):
    """Synthesizes buffered telephony audio and processes with Gemini."""
    all_pcm = b"".join(audio_chunks)
    wav_bytes = AudioProcessor.pcm_to_wav(all_pcm, sample_rate=16000, num_channels=1)
    duration = AudioProcessor.get_wav_duration_seconds(wav_bytes)

    filename = f"ivr_{call_sid}.wav"
    saved_path = f"{settings.STORAGE_DIR}/{settings.RAW_AUDIO_SUBDIR}/{filename}"
    with open(saved_path, "wb") as f:
        f.write(wav_bytes)

    db = SessionLocal()
    try:
        meeting = Meeting(
            title=f"Telephony Call: {metadata['caller']} <-> {metadata['agent']}",
            source="telephony_ivr",
            status="processing",
            duration_seconds=int(duration),
            audio_path=saved_path
        )
        db.add(meeting)
        db.flush()

        participants_data = [
            ParticipantSchema(name=metadata['caller'], role="caller"),
            ParticipantSchema(name=metadata['agent'], role="agent")
        ]
        if metadata.get('email'):
            participants_data[0].email = metadata['email']

        for p in participants_data:
            db.add(Participant(meeting_id=meeting.id, name=p.name, email=p.email, role=p.role))
        db.commit()

        # Run Gemini Analysis
        mom_package = await gemini_service.generate_minutes_from_audio(
            audio_bytes=wav_bytes,
            mime_type="audio/wav",
            meeting_title=meeting.title,
            known_participants=participants_data
        )

        pdf_path = pdf_service.generate_mom_pdf(meeting.id, mom_package)
        meeting.pdf_path = pdf_path

        for item in mom_package.action_items:
            db.add(ActionItem(
                meeting_id=meeting.id,
                task=item.task,
                assignee_name=item.assignee_name,
                assignee_email=item.assignee_email,
                due_date=item.due_date,
                priority=item.priority,
                context_quote=item.context_quote
            ))

        db.add(MeetingSummary(
            meeting_id=meeting.id,
            executive_summary=mom_package.executive_summary,
            sentiment=mom_package.overall_sentiment,
            topics_json=json.dumps([t.model_dump() for t in mom_package.agenda_topics]),
            key_decisions_json=json.dumps(mom_package.key_decisions),
            unresolved_questions_json=json.dumps(mom_package.unresolved_questions),
            raw_mom_json=mom_package.model_dump_json()
        ))

        meeting.status = "completed"
        db.commit()

        # Optional Email Dispatch
        if metadata.get('email'):
            await email_service.dispatch_meeting_recap([metadata['email']], mom_package, pdf_path)
            meeting.email_sent = True
            db.commit()

        logger.info(f"Telephony processing finished for Meeting #{meeting.id}")
    finally:
        db.close()
