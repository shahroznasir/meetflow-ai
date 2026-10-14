import pytest
from app.schemas.mom import MeetingMinutesPackage, ParticipantSchema
from app.services.gemini_service import gemini_service

@pytest.mark.asyncio
async def test_gemini_mock_minutes_generation():
    participants = [
        ParticipantSchema(name="Sarah Connor", email="sarah@example.com", role="host"),
        ParticipantSchema(name="John Reese", email="john@example.com", role="attendee")
    ]

    dummy_audio = bytes(1024)
    mom = await gemini_service.generate_minutes_from_audio(
        audio_bytes=dummy_audio,
        mime_type="audio/webm",
        meeting_title="Q4 Strategic Alignment",
        known_participants=participants
    )

    assert isinstance(mom, MeetingMinutesPackage)
    assert mom.meeting_title == "Q4 Strategic Alignment"
    assert len(mom.participants) >= 2
    assert len(mom.action_items) > 0
    assert len(mom.key_decisions) > 0
    assert mom.follow_up_email_subject is not None
    assert "Sarah Connor" in mom.executive_summary or "John Reese" in mom.executive_summary

def test_pydantic_schema_validation():
    valid_data = {
        "meeting_title": "Budget Review",
        "executive_summary": "Reviewed the Q1 financial projection and finalized departmental budgets.",
        "key_decisions": ["Approved $50k marketing budget."],
        "agenda_topics": [
            {
                "topic": "Marketing Allocation",
                "summary": "Discussed paid acquisition channels.",
                "decisions": ["Allocate to digital ads."]
            }
        ],
        "action_items": [
            {
                "task": "Distribute updated spreadsheet",
                "assignee_name": "Dave",
                "priority": "High"
            }
        ],
        "unresolved_questions": [],
        "overall_sentiment": "Positive",
        "follow_up_email_subject": "Recap: Budget Review",
        "follow_up_email_body_html": "<p>Meeting summary here</p>"
    }

    pkg = MeetingMinutesPackage(**valid_data)
    assert pkg.meeting_title == "Budget Review"
    assert pkg.action_items[0].assignee_name == "Dave"
