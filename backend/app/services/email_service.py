import os
import logging
from email.message import EmailMessage
from typing import List, Optional
import aiosmtplib
from icalendar import Calendar, Event
from datetime import datetime, timedelta
from app.config import settings
from app.schemas.mom import MeetingMinutesPackage, ParticipantSchema

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def create_action_ics(task_name: str, due_date_str: Optional[str]) -> bytes:
        """Creates an iCalendar (.ics) attachment for a tracked action item."""
        cal = Calendar()
        cal.add('prodid', '-//AI Meeting Secretary//EN')
        cal.add('version', '2.0')

        event = Event()
        event.add('summary', f"Action Item: {task_name}")
        
        # Default deadline: 3 days out if unspecified
        start_time = datetime.utcnow() + timedelta(days=3)
        event.add('dtstart', start_time)
        event.add('dtend', start_time + timedelta(hours=1))
        event.add('dtstamp', datetime.utcnow())
        event.add('description', f"Deliverable from meeting: {task_name}")

        cal.add_component(event)
        return cal.to_ical()

    @classmethod
    async def dispatch_meeting_recap(
        cls,
        recipients: List[str],
        mom: MeetingMinutesPackage,
        pdf_path: Optional[str] = None
    ) -> bool:
        """Sends rich recap email with PDF and ICS attachments to all participants."""
        if not recipients:
            logger.info("No recipient emails provided. Skipping email dispatch.")
            return False

        message = EmailMessage()
        message["Subject"] = mom.follow_up_email_subject
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = ", ".join(recipients)

        # Plain text fallback
        plain_text = f"""Minutes of Meeting: {mom.meeting_title}

Executive Summary:
{mom.executive_summary}

Action Items:
"""
        for item in mom.action_items:
            plain_text += f"- [{item.priority}] {item.task} (Assignee: {item.assignee_name}, Due: {item.due_date})\n"

        message.set_content(plain_text)
        message.add_alternative(mom.follow_up_email_body_html, subtype="html")

        # Attach PDF if available
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
            message.add_attachment(
                pdf_data,
                maintype="application",
                subtype="pdf",
                filename=os.path.basename(pdf_path)
            )

        # Attach Action ICS file
        if mom.action_items:
            primary_task = mom.action_items[0]
            ics_bytes = cls.create_action_ics(primary_task.task, primary_task.due_date)
            message.add_attachment(
                ics_bytes,
                maintype="text",
                subtype="calendar",
                filename="meeting_actions.ics"
            )

        # Send via aiosmtplib
        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_USE_TLS,
                timeout=10
            )
            logger.info(f"Successfully sent meeting recap email to: {recipients}")
            return True
        except Exception as e:
            logger.warning(f"Could not send email via SMTP ({settings.SMTP_HOST}:{settings.SMTP_PORT}): {e}")
            return False

email_service = EmailService()
