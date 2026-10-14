import io
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_root_dashboard():
    response = client.get("/")
    assert response.status_code == 200
    assert "Gemini Meeting Agent" in response.text

def test_create_meeting_and_get_details():
    dummy_wav = io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
    participants = [
        {"name": "Alice", "email": "alice@example.com", "role": "host"},
        {"name": "Bob", "email": "bob@example.com", "role": "attendee"}
    ]

    response = client.post(
        "/api/v1/meetings/recordings",
        data={
            "meeting_title": "Sprint Planning 42",
            "participants_json": json.dumps(participants),
            "source": "web_extension",
            "auto_email": "false"
        },
        files={
            "audio_file": ("test_recording.wav", dummy_wav, "audio/wav")
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    meeting_id = data["meeting_id"]

    # Verify meeting listing
    list_res = client.get("/api/v1/meetings")
    assert list_res.status_code == 200
    meetings = list_res.json()
    assert any(m["id"] == meeting_id for m in meetings)

    # Verify meeting detail
    detail_res = client.get(f"/api/v1/meetings/{meeting_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["title"] == "Sprint Planning 42"
    assert len(detail["participants"]) == 2
    assert len(detail["action_items"]) > 0

    # Verify action item status update
    action_id = detail["action_items"][0]["id"]
    patch_res = client.patch(f"/api/v1/actions/{action_id}", json={"status": "Completed"})
    assert patch_res.status_code == 200
    assert patch_res.json()["current_status"] == "Completed"

    # Verify transcript endpoint
    transcript_res = client.get(f"/api/v1/meetings/{meeting_id}/transcript")
    assert transcript_res.status_code == 200
    transcript_data = transcript_res.json()
    assert "segments" in transcript_data
    assert "plain_text" in transcript_data
    assert len(transcript_data["segments"]) > 0

    # Verify Ask Fred Chat endpoint
    chat_res = client.post(
        f"/api/v1/meetings/{meeting_id}/chat",
        json={"question": "What are the action items?", "history": []}
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "answer" in chat_data
    assert "suggested_followups" in chat_data
    assert len(chat_data["answer"]) > 0

    # Verify meeting deletion
    del_res = client.delete(f"/api/v1/meetings/{meeting_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # Verify meeting is no longer accessible
    get_after_del = client.get(f"/api/v1/meetings/{meeting_id}")
    assert get_after_del.status_code == 404

    # Verify deleting non-existent meeting returns 404
    del_404_res = client.delete(f"/api/v1/meetings/999999")
    assert del_404_res.status_code == 404
