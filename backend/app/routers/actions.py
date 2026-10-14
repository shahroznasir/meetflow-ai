from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.db.database import get_db
from app.db.models import ActionItem, Meeting

router = APIRouter(prefix="/api/v1/actions", tags=["Action Items"])

class ActionItemUpdate(BaseModel):
    status: Optional[str] = None  # Pending, In Progress, Completed
    due_date: Optional[str] = None
    priority: Optional[str] = None

@router.get("")
def list_all_action_items(
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieves all tracked action items across all meetings with optional filters."""
    query = db.query(ActionItem).join(Meeting)
    if status:
        query = query.filter(ActionItem.status == status)
    if assignee:
        query = query.filter(ActionItem.assignee_name.ilike(f"%{assignee}%"))

    items = query.order_by(ActionItem.id.desc()).all()
    results = []
    for item in items:
        results.append({
            "id": item.id,
            "meeting_id": item.meeting_id,
            "meeting_title": item.meeting.title if item.meeting else None,
            "task": item.task,
            "assignee_name": item.assignee_name,
            "assignee_email": item.assignee_email,
            "due_date": item.due_date,
            "priority": item.priority,
            "status": item.status,
            "context_quote": item.context_quote,
            "created_at": item.created_at.isoformat() if item.created_at else None
        })
    return results

@router.patch("/{action_id}")
def update_action_item(
    action_id: int,
    payload: ActionItemUpdate,
    db: Session = Depends(get_db)
):
    """Updates an action item's status, due date, or priority."""
    item = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    if payload.status:
        item.status = payload.status
    if payload.due_date:
        item.due_date = payload.due_date
    if payload.priority:
        item.priority = payload.priority

    db.commit()
    db.refresh(item)
    return {"status": "success", "action_id": item.id, "current_status": item.status}
