import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import Meeting, ActionItem, MeetingSummary

logger = logging.getLogger(__name__)

class MeetingMCPServer:
    """
    Model Context Protocol (MCP) Server for Enterprise AI Agents.
    Enables conversational query, decision lookup, and action execution across all recorded meetings.
    """

    @staticmethod
    def get_tool_definitions() -> List[Dict[str, Any]]:
        """Returns standard MCP tool signatures for tool-calling agents."""
        return [
            {
                "name": "search_meetings",
                "description": "Searches stored meetings, executive summaries, and transcripts by query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search term, topic, or attendee name"},
                        "limit": {"type": "integer", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_meeting",
                "description": "Retrieves comprehensive details, summary, and decisions for a specific meeting.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "integer", "description": "The unique meeting identifier"}
                    },
                    "required": ["meeting_id"]
                }
            },
            {
                "name": "get_decisions",
                "description": "Retrieves all verified, evidence-backed decisions agreed during a meeting.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "integer", "description": "The meeting ID"}
                    },
                    "required": ["meeting_id"]
                }
            },
            {
                "name": "get_action_items",
                "description": "Retrieves action items filtered by status (Pending, Completed) or assignee.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "integer", "description": "Optional meeting ID filter"},
                        "status": {"type": "string", "enum": ["Pending", "Completed"], "description": "Action status"},
                        "assignee": {"type": "string", "description": "Name of the person accountable"}
                    }
                }
            },
            {
                "name": "complete_action",
                "description": "Marks a tracked action item as completed in the system of record.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action_id": {"type": "integer", "description": "The action item ID"}
                    },
                    "required": ["action_id"]
                }
            }
        ]

    @classmethod
    def execute_tool(cls, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches tool execution against the database."""
        db: Session = SessionLocal()
        try:
            if tool_name == "search_meetings":
                query = arguments.get("query", "")
                limit = arguments.get("limit", 10)
                meetings = db.query(Meeting).filter(Meeting.title.ilike(f"%{query}%")).limit(limit).all()
                return {
                    "results": [
                        {"id": m.id, "title": m.title, "source": m.source, "created_at": str(m.created_at)}
                        for m in meetings
                    ]
                }

            elif tool_name == "get_meeting":
                m_id = arguments.get("meeting_id")
                meeting = db.query(Meeting).filter(Meeting.id == m_id).first()
                if not meeting:
                    return {"error": "Meeting not found"}
                return {
                    "id": meeting.id,
                    "title": meeting.title,
                    "source": meeting.source,
                    "summary": meeting.summary.executive_summary if meeting.summary else None,
                    "action_items_count": len(meeting.action_items)
                }

            elif tool_name == "get_decisions":
                m_id = arguments.get("meeting_id")
                summary = db.query(MeetingSummary).filter(MeetingSummary.meeting_id == m_id).first()
                if not summary or not summary.key_decisions_json:
                    return {"decisions": []}
                return {"decisions": json.loads(summary.key_decisions_json)}

            elif tool_name == "get_action_items":
                q = db.query(ActionItem)
                if arguments.get("meeting_id"):
                    q = q.filter(ActionItem.meeting_id == arguments["meeting_id"])
                if arguments.get("status"):
                    q = q.filter(ActionItem.status == arguments["status"])
                if arguments.get("assignee"):
                    q = q.filter(ActionItem.assignee_name.ilike(f"%{arguments['assignee']}%"))
                items = q.all()
                return {
                    "action_items": [
                        {"id": a.id, "task": a.task, "owner": a.assignee_name, "status": a.status, "due": a.due_date}
                        for a in items
                    ]
                }

            elif tool_name == "complete_action":
                act_id = arguments.get("action_id")
                item = db.query(ActionItem).filter(ActionItem.id == act_id).first()
                if not item:
                    return {"error": "Action item not found"}
                item.status = "Completed"
                db.commit()
                return {"success": True, "action_id": act_id, "status": "Completed"}

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        finally:
            db.close()

mcp_server = MeetingMCPServer()
