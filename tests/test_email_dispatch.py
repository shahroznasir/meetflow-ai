import pytest
from app.services.email_service import email_service
from app.schemas.mom import MeetingMinutesPackage, ActionItemSchema

def test_action_ics_generation():
    ics_bytes = email_service.create_action_ics("Ship V1 Extension to Chrome Web Store", "2026-10-15")
    assert b"BEGIN:VCALENDAR" in ics_bytes
    assert b"BEGIN:VEVENT" in ics_bytes
    assert b"Ship V1 Extension" in ics_bytes
    assert b"END:VCALENDAR" in ics_bytes

@pytest.mark.asyncio
async def test_email_dispatch_empty_recipients():
    mom = MeetingMinutesPackage(
        meeting_title="Test Meeting",
        executive_summary="Summary",
        key_decisions=[],
        agenda_topics=[],
        action_items=[],
        unresolved_questions=[],
        follow_up_email_subject="Recap",
        follow_up_email_body_html="<p>Body</p>"
    )
    # Should cleanly skip without error when no recipients provided
    result = await email_service.dispatch_meeting_recap([], mom)
    assert result is False
