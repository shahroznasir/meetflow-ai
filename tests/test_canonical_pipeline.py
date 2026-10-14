import pytest
from app.schemas.canonical import (
    CanonicalConversation, ConversationSourceType, Participant,
    TranscriptEntry, ApprovalMode, ActionStatus, ActionPriority
)
from app.ai.pipeline import intelligence_pipeline
from app.services.validation_engine import validation_engine
from app.services.mcp_server import mcp_server

@pytest.mark.asyncio
async def test_canonical_pipeline_and_validation():
    participants = [
        Participant(id="p1", name="Sarah Connor", email="sarah@example.com", role="host"),
        Participant(id="p2", name="John Reese", email="john@example.com", role="attendee")
    ]

    transcript = [
        TranscriptEntry(
            entry_id="e1",
            speaker_id="p1",
            speaker_name="Sarah Connor",
            start_time_seconds=0.0,
            end_time_seconds=15.0,
            raw_text="Let's align on the canonical data model and API architecture.",
            normalized_text="Let's align on the canonical data model and API architecture."
        ),
        TranscriptEntry(
            entry_id="e2",
            speaker_id="p2",
            speaker_name="John Reese",
            start_time_seconds=16.0,
            end_time_seconds=35.0,
            raw_text="Agreed. I will finalize the canonical models and schemas.",
            normalized_text="Agreed. I will finalize the canonical models and schemas."
        )
    ]

    # Execute 6-stage deterministic pipeline
    mom = await intelligence_pipeline.execute_pipeline(
        transcript=transcript,
        participants=participants,
        meeting_title="Platform Architecture Sync"
    )

    assert mom.executive_summary is not None
    assert len(mom.decisions) > 0
    assert len(mom.action_items) > 0
    assert mom.model_version is not None
    assert mom.prompt_version is not None

    # Apply validation engine
    full_transcript = "Let's align on the canonical data model. I will finalize the canonical models and schemas."
    validated_mom = validation_engine.validate_mom(
        mom=mom,
        participants=participants,
        transcript_text=full_transcript,
        approval_mode=ApprovalMode.MANUAL_APPROVAL
    )

    # In manual approval mode, action items must be held in PROPOSED status
    for action in validated_mom.action_items:
        assert action.status == ActionStatus.PROPOSED
        assert action.validation_status in ["VERIFIED", "EVIDENCE_UNVERIFIED"]

def test_mcp_server_tool_definitions():
    tools = mcp_server.get_tool_definitions()
    tool_names = [t["name"] for t in tools]
    assert "search_meetings" in tool_names
    assert "get_meeting" in tool_names
    assert "get_decisions" in tool_names
    assert "get_action_items" in tool_names
    assert "complete_action" in tool_names
